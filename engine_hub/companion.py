"""A node-local service: narrow state allowlist, CAS writes, immutable Skill snapshots."""
import json
import pathlib
import re
import secrets
import subprocess
import threading
import tempfile
import sys
import importlib.metadata
import time
import urllib.parse
from .common import Fault, canonical, digest, request
from .assets import validate_package


class RemoteSkillProvider:
    def __init__(self,cfg,node,home):
        self.cfg,self.node,self.home=cfg,node,home

    def release(self,id):
        return request(self.cfg['assets_url'],'/v1/assets/'+self.node['engine']+'/releases/'+id,
            token=self.node['asset_key'],timeout=20,service=True)

    def snapshot(self,release):
        r=self.release(release)
        package=json.loads(r['content']['skill']['content'])
        validate_package(package)
        address=r['documents']['skill']['sha256']
        root=self.home/'approved-cache'/address
        if root.is_symlink():
            raise Fault(403,'cache_symlink_denied')
        if root.exists():
            for path,content in package.items():
                p=root/path
                if p.is_symlink() or not p.is_file() or digest(p.read_bytes())!=digest(content):
                    raise Fault(409,'cache_digest_mismatch')
        else:
            root.mkdir(parents=True,mode=0o700)
            for path,content in package.items():
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(content);p.chmod(0o444)
            for d in sorted(root.rglob('*'),reverse=True):
                if d.is_dir():
                    d.chmod(0o555)
            root.chmod(0o555)
        return r,root


class Companion:
    def __init__(self,cfg,node,home,workspace,store):
        self.cfg,self.node,self.home,self.workspace,self.store=cfg,node,pathlib.Path(home),pathlib.Path(workspace),store
        self.lock=threading.Lock()
        self.consumers=threading.BoundedSemaphore(2)
        self.assets=RemoteSkillProvider(cfg,node,self.home)

    def context(self,b):
        if b['engine']!=self.node['engine'] or not re.fullmatch(r'[a-f0-9]{32}',b['id']):
            raise Fault(403,'context_scope_mismatch')
        with self.lock:
            prior=self.store.get('contexts',b['id'])
            if prior:
                if canonical(prior)!=canonical(b):
                    raise Fault(409,'context_conflict')
                return prior
            release,root=self.assets.snapshot(b['release'])
            if release['bundle_sha256']!=b['bundle_sha256']:
                raise Fault(409,'bundle_mismatch')
            self.store.put('contexts',b['id'],b)
            private=self.home/'private-drafts'/b['owner']/b['conversation']
            private.mkdir(parents=True,exist_ok=True,mode=0o700)
            self.store.audit({'action':'adopt','release':b['release'],'context':b['id'],'at':time.time()})
            return b

    def consume(self,id):
        b=self.store.get('contexts',id)
        if not b:
            raise Fault(404,'not_found')
        # Every use revalidates remote source/auth/revocation. Cache never grants access.
        release,root=self.assets.snapshot(b['release'])
        package=json.loads(release['content']['skill']['content'])
        dependencies=json.loads(package.get('dependencies.json','{"python":"3.11","packages":{}}'))
        if not sys.version.startswith(dependencies['python']+'.'):
            raise Fault(409,'skill_python_version_unavailable')
        for name,version in dependencies['packages'].items():
            try:actual=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:raise Fault(409,'skill_dependency_unavailable') from None
            if actual!=version:raise Fault(409,'skill_dependency_version_mismatch')
        # Approved package script executes only in the node's sandbox with a deadline.
        if not self.consumers.acquire(blocking=False):
            raise Fault(429,'skill_execution_budget')
        try:
            with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
                proc=subprocess.run(['/usr/bin/prlimit','--cpu=2:2','--as=536870912:536870912',
                    '--fsize=131072:131072','--nofile=32:32',sys.executable,'-I','-B',str(root/'scripts/probe.py')],
                    cwd=root,stdout=output,stderr=errors,timeout=3,
                    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
                output.seek(0);script_output=output.read(4000).decode('utf-8','replace')
                if proc.returncode:
                    raise Fault(502,'approved_script_failed')
        except subprocess.TimeoutExpired:
            raise Fault(504,'approved_script_timeout') from None
        finally:
            self.consumers.release()
        return {'context':id,'engine':self.node['engine'],'node':self.node['id'],
            'release':b['release'],'knowledge':release['content']['knowledge'],
            'skill_sha256':release['documents']['skill']['sha256'],
            'skill_method':(root/'SKILL.md').read_text(),'reference':(root/'references/method.md').read_text(),
            'script_output':script_output,'dependencies':dependencies,'python_runtime':sys.version.split()[0],
            'bundle_sha256':release['bundle_sha256']}

    def state_path(self,kind):
        paths={'memory':self.home/'memories/MEMORY.md','workspace':self.workspace/'node-evidence.txt'}
        if kind not in paths:
            raise Fault(404,'not_found')
        p=paths[kind]
        if p.is_symlink():
            raise Fault(403,'symlink_denied')
        return p

    def draft(self,b):
        context=self.store.get('contexts',b.get('context',''))
        if not context or context['owner']!=b.get('owner') or context['conversation']!=b.get('conversation'):
            raise Fault(404,'not_found')
        id=b.get('id') or secrets.token_hex(16)
        if not re.fullmatch(r'[a-f0-9]{32}',id):
            raise Fault(400,'invalid_draft_id')
        with self.lock:
            old=self.store.get('drafts',id)
            if old and (old['owner']!=b['owner'] or old['conversation']!=b['conversation']):
                raise Fault(404,'not_found')
            if old and old['sha256']!=b.get('base_sha256'):
                raise Fault(409,'draft_conflict')
            content=b.get('content')
            if not isinstance(content,str) or len(content)>32000:
                raise Fault(400,'invalid_draft_content')
            row={'id':id,'node':self.node['id'],'engine':self.node['engine'],'owner':b['owner'],
                'conversation':b['conversation'],'context':b['context'],'content':content,
                'sha256':digest(content),'stage':'private_draft','at':time.time()}
            self.store.put('drafts',id,row)
            self.store.audit({'action':'private_draft','id':id,'owner':b['owner'],'conversation':b['conversation']})
            return row

    def state(self,kind,b=None):
        with self.lock:
            p=self.state_path(kind)
            content=p.read_text()
            if b is not None:
                if b.get('base_sha256')!=digest(content):
                    raise Fault(409,'state_conflict')
                if not isinstance(b.get('content'),str) or len(b['content'])>16000:
                    raise Fault(400,'invalid_state_content')
                p.write_text(b['content'])
                content=p.read_text()
                self.store.audit({'action':'state_write','kind':kind,'actor':b.get('actor'),'sha256':digest(content),'at':time.time()})
            return {'kind':kind,'content':content,'sha256':digest(content),'node':self.node['id']}

    def handle(self,h):
        token=h.headers.get('Authorization','').removeprefix('Bearer ')
        admin=secrets.compare_digest(token,self.node['state_admin_key'])
        reader=secrets.compare_digest(token,self.node['consume_key'])
        if not admin and not reader:
            raise Fault(401,'node_auth_required')
        path=urllib.parse.urlsplit(h.path).path.split('/')
        if reader and not (h.command=='GET' and (path==['','v1','identity'] or
            (len(path)==5 and path[1:3]==['v1','contexts'] and path[4]=='consume'))):
            raise Fault(403,'consumer_state_write_denied')
        if path==['','v1','identity'] and h.command=='GET':
            result={'node':self.node['id'],'engine':self.node['engine'],'scope':'single-node',
                'central_home_mounts':False,'approved_snapshot_writable':False}
        elif path==['','v1','contexts'] and h.command=='POST':
            result=self.context(h.body())
        elif path==['','v1','drafts'] and h.command=='POST':
            result=self.draft(h.body())
        elif len(path)==5 and path[1:3]==['v1','contexts'] and path[4]=='consume' and h.command=='GET':
            result=self.consume(path[3])
        elif len(path)==4 and path[1:3]==['v1','state']:
            if h.command not in ['GET','PUT']:
                raise Fault(405,'method_not_allowed')
            result=self.state(path[3],h.body() if h.command=='PUT' else None)
        else:
            raise Fault(404,'not_found')
        h.reply(200,result)
