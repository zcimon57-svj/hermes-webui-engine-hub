"""WeKnora content authority plus a thin single-owner release/CAS coordinator."""
import json
import secrets
import time
import urllib.parse
from .common import Fault, canonical, digest, request


class WeKnoraClient:
    def __init__(self, base, identities):
        self.base, self.identities = base, identities

    def call(self, engine, path, method='GET', data=None):
        identity = self.identities.get(engine)
        if not identity:
            raise Fault(404, 'not_found')
        result = request(self.base, '/api/v1'+path, method, data, identity['token'], timeout=12)
        if result.get('success') is False:
            raise Fault(502, 'weknora_rejected')
        return result.get('data', result)

    def create(self, engine, kb, title, content):
        return self.call(engine, '/knowledge-bases/'+kb+'/knowledge/manual', 'POST',
            {'title':title,'content':content,'status':'draft'})

    def read(self, engine, document):
        item = self.call(engine, '/knowledge/'+document)
        # The locked image returns metadata as a JSON object; tolerate encoded JSON.
        meta = item.get('metadata') or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        manual = meta.get('manual', meta.get('manual_metadata', meta))
        if isinstance(manual, str):
            manual = json.loads(manual)
        content = manual.get('content')
        if content is None:
            raise Fault(502, 'weknora_content_missing')
        return {'content':content,'remote_revision':manual.get('version'),'status':manual.get('status'),
            'knowledge_id':item['id'],'kb_id':item['knowledge_base_id'],
            'citation':self.base+'/api/v1/knowledge/'+item['id']}

    def publish(self, engine, document, content):
        self.call(engine, '/knowledge/manual/'+document, 'PUT', {'content':content,'status':'publish'})
        return self.read(engine, document)

    def search(self, engine, kb, query):
        return self.call(engine, '/knowledge-bases/'+kb+'/hybrid-search', 'POST',
            {'query_text':query,'vector_threshold':0,'keyword_threshold':0,'match_count':5})


def validate_package(package):
    if not isinstance(package, dict) or not {'SKILL.md','scripts/probe.py','references/method.md'} <= set(package):
        raise Fault(400, 'incomplete_skill_package')
    if len(canonical(package)) > 256000:
        raise Fault(413, 'skill_package_too_large')
    for path, content in package.items():
        parts = path.split('/')
        if path.startswith('/') or '..' in parts or not all(parts) or '\\' in path or not isinstance(content,str):
            raise Fault(400, 'unsafe_skill_path')
    if 'dependencies.json' in package:
        try:
            spec=json.loads(package['dependencies.json'])
            if set(spec)!={'python','packages'} or not isinstance(spec['python'],str) or not isinstance(spec['packages'],dict):raise ValueError()
            if not all(isinstance(k,str) and isinstance(v,str) for k,v in spec['packages'].items()):raise ValueError()
        except (ValueError,TypeError):raise Fault(400,'invalid_dependency_manifest') from None


class ReleaseAuthority:
    def __init__(self, store, cfg):
        self.store, self.cfg = store, cfg
        self.remote = WeKnoraClient(cfg['weknora']['base'], cfg['weknora']['identities'])

    def current(self, engine):
        ptr = self.store.get('pointers', engine)
        if not ptr:
            raise Fault(409, 'no_approved_release')
        return self.release(engine, ptr['release'])

    def release(self, engine, id, include_content=False):
        r = self.store.get('releases', id)
        if not r or r['engine'] != engine:
            raise Fault(404, 'not_found')
        if r['revoked']:
            raise Fault(410, 'release_revoked')
        result = dict(r)
        if include_content:
            contents = {}
            for kind, doc in r['documents'].items():
                remote = self.remote.read(engine, doc['id'])
                if digest(remote['content']) != doc['sha256'] or remote['status'] != 'publish':
                    raise Fault(409, 'remote_asset_drift')
                if 'remote_revision' in doc and remote['remote_revision']!=doc['remote_revision']:
                    raise Fault(409,'remote_revision_drift')
                contents[kind] = remote
            result['content'] = contents
        return result

    def candidate(self, body):
        engine = body['engine']
        if engine not in self.cfg['weknora']['identities']:
            raise Fault(404, 'not_found')
        if not body.get('share_consent') or not body.get('source'):
            raise Fault(400, 'source_and_share_consent_required')
        source = body['source']
        if source.get('engine') != engine or source.get('owner') != body['author']:
            raise Fault(403, 'source_scope_mismatch')
        package = body['package']
        validate_package(package)
        id = 'candidate-'+secrets.token_hex(12)
        kb = self.cfg['weknora']['identities'][engine]['kb_id']
        docs = {}
        for kind, content in {'knowledge':body['knowledge'],'skill':canonical(package)}.items():
            item = self.remote.create(engine,kb,id+'-'+kind,content)
            remote = self.remote.read(engine,item['id'])
            if remote['content'] != content:
                raise Fault(502, 'draft_readback_mismatch')
            docs[kind] = {'id':item['id'],'kb_id':kb,'sha256':digest(content)}
        row = {'id':id,'engine':engine,'author':body['author'],'source':source,
            'share_consent':True,'base':body.get('base'),'documents':docs,
            'stage':'candidate','origin':body.get('origin','MANUAL_SYNTHETIC'), 'at':time.time()}
        self.store.put('candidates',id,row)
        return row

    def evaluate(self, id, body):
        c = self.store.get('candidates',id)
        if not c:
            raise Fault(404, 'not_found')
        if c['stage'] != 'candidate':
            raise Fault(409, 'candidate_not_pending')
        c['evaluation'] = {'passed':body.get('passed') is True,'reviewer':body['reviewer'],
            'evidence':body.get('evidence',[]),'quality':'GOVERNANCE_ONLY' if c['origin']=='MANUAL_SYNTHETIC' else 'UNACCEPTED_DOMAIN_EVALUATION'}
        c['stage'] = 'evaluated' if c['evaluation']['passed'] else 'evaluation_failed'
        self.store.put('candidates',id,c)
        return c

    def approve(self, id, body):
        # One transaction owns pointer comparison and publication. Failed remote work
        # never becomes eligible; unreferenced remote documents remain evidence.
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            c = self.store.get('candidates',id,db)
            if not c or c['stage'] != 'evaluated':
                raise Fault(409, 'candidate_not_evaluated')
            if body['reviewer'] == c['author']:
                raise Fault(403, 'independent_reviewer_required')
            current = self.store.get('pointers',c['engine'],db)
            current_id = current['release'] if current else None
            if c['base'] != current_id or body.get('base') != current_id:
                raise Fault(409, 'stale_base')
            for doc in c['documents'].values():
                remote = self.remote.read(c['engine'],doc['id'])
                if digest(remote['content']) != doc['sha256']:
                    raise Fault(409, 'candidate_content_changed')
                readback = self.remote.publish(c['engine'],doc['id'],remote['content'])
                if digest(readback['content']) != doc['sha256'] or readback['status'] != 'publish':
                    raise Fault(502, 'publish_readback_mismatch')
                doc['remote_revision']=readback['remote_revision']
            release = {'id':'release-'+secrets.token_hex(12),'engine':c['engine'],'candidate':id,
                'base':current_id,'documents':c['documents'],'config':{'tool_policy':'read_only','version':'config-1'},
                'reviewer':body['reviewer'],'at':time.time(),'revoked':False,'semantic_quality':'NOT_RUN'}
            release['bundle_sha256'] = digest(canonical({'documents':release['documents'],'config':release['config']}))
            self.store.put('releases',release['id'],release,db)
            self.store.put('pointers',c['engine'],{'release':release['id']},db)
            c['stage'], c['release'] = 'published',release['id']
            self.store.put('candidates',id,c,db)
        self.store.audit({'action':'publish','release':release['id'],'reviewer':body['reviewer']})
        return release

    def withdraw(self, engine, id, body):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            r = self.store.get('releases',id,db)
            if not r or r['engine'] != engine:
                raise Fault(404,'not_found')
            r['revoked'],r['withdrawal'] = True,body
            self.store.put('releases',id,r,db)
        self.store.audit({'action':'withdraw','release':id,'reason':body.get('reason')})
        return {'withdrawn':id}

    def rollback(self, engine, body):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            ptr = self.store.get('pointers',engine,db)
            if not ptr or ptr['release'] != body['base']:
                raise Fault(409,'stale_base')
            target = self.store.get('releases',body['target'],db)
            if not target or target['engine'] != engine or target['revoked']:
                raise Fault(409,'target_ineligible')
            self.store.put('pointers',engine,{'release':target['id']},db)
        self.store.audit({'action':'rollback','engine':engine,'target':target['id']})
        return target

    def handle(self,h):
        token = h.headers.get('Authorization','').removeprefix('Bearer ')
        writer = secrets.compare_digest(token,self.cfg['service_keys']['assets'])
        node = next((n for n in self.cfg['nodes'] if secrets.compare_digest(token,n['asset_key'])),None)
        if not writer and not node:
            raise Fault(401,'service_auth_required')
        path = urllib.parse.urlsplit(h.path).path.split('/')
        if len(path) < 4 or path[1:3] != ['v1','assets']:
            raise Fault(404,'not_found')
        engine = path[3]
        if engine not in self.cfg['weknora']['identities'] or (node and node['engine']!=engine):
            raise Fault(404,'not_found')
        action = path[4] if len(path)>4 else ''
        if h.command=='GET':
            if action=='current':
                result = self.current(engine)
            elif action=='releases' and len(path)==6:
                result = self.release(engine,path[5],include_content=True)
            elif action=='history' and writer:
                result = [r for r in self.store.all('releases') if r['engine']==engine]
            elif action=='candidates' and writer:
                result = [r for r in self.store.all('candidates') if r['engine']==engine]
            else:
                raise Fault(404,'not_found')
        else:
            if not writer:
                raise Fault(403,'consumer_cannot_publish')
            b = h.body()
            if action=='candidates' and len(path)==5:
                b['engine']=engine
                result = self.candidate(b)
            elif action=='candidates' and len(path)==7:
                c = self.store.get('candidates',path[5])
                if not c or c['engine']!=engine:
                    raise Fault(404,'not_found')
                if path[6]=='evaluate':
                    result = self.evaluate(path[5],b)
                elif path[6]=='approve':
                    result = self.approve(path[5],b)
                else:
                    raise Fault(404,'not_found')
            elif action=='releases' and len(path)==7 and path[6]=='withdraw':
                result = self.withdraw(engine,path[5],b)
            elif action=='rollback':
                result = self.rollback(engine,b)
            else:
                raise Fault(404,'not_found')
        h.reply(200,result)


class ReleaseClient:
    def __init__(self, cfg):
        self.base, self.key = cfg['assets_url'],cfg['service_keys']['assets']

    def call(self,engine,path,method='GET',data=None):
        return request(self.base,'/v1/assets/'+engine+path,method,data,self.key,timeout=40,service=True)
