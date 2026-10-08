"""Own 158xx resources with PID/start_ticks; keep every state across restart."""
import argparse
import json
import os
import pathlib
import resource
import secrets
import signal
import socket
import subprocess
import sys
import time
from engine_hub.resources import check_admission,scope_command,ensure_slice,boot_id,SLICE,CPU

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parent
LOCAL=ROOT/'.local'
HISTORICAL=pathlib.Path('/home/cimon/code/business-agent-engineering/explorations/2026-09-20-four-engines-six-nodes-validation')
PY=pathlib.Path(os.environ.get('ENGINE_HUB_HERMES_PYTHON',str(HISTORICAL/'runtime/hermes-venv/bin/python')))
HERMES=pathlib.Path(os.environ.get('ENGINE_HUB_HERMES_SOURCE',str(HISTORICAL/'upstream/hermes')))


def registry():
    p=LOCAL/'resources.json'
    return json.loads(p.read_text()) if p.exists() else {}


def live(r):
    try:
        if r.get('boot_id')!=boot_id():return False
        s=pathlib.Path('/proc/'+str(r['pid'])+'/stat').read_text().split()
        return s[21]==r['start_ticks'] and s[2]!='Z'
    except OSError:
        return False


def limits():
    resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
    # Virtual mappings are not resident RAM. The shared cgroup, not RLIMIT_AS,
    # owns the 1 GiB physical budget; this allows legitimate interpreter stacks.
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    # RLIMIT_NPROC is per host UID: it would affect all sibling labs, so not used.


def start(name,cmd,env=None,port=None):
    registered=registry()
    if name in registered and live(registered[name]):
        return
    ensure_watchdog()
    check_admission(256*1024**2 if name.startswith('node-') and not name.endswith('-state') else 48*1024**2)
    if port:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0:
                raise RuntimeError('Port in use outside live registry: '+str(port))
    log=(LOCAL/(name+'.log')).open('ab')
    unit='eh158-'+name+'-'+secrets.token_hex(5)
    wrapped=scope_command(unit,cmd)
    p=subprocess.Popen(wrapped,cwd=REPO,
        env={'PATH':str(PY.parent)+':/usr/bin:/bin','LANG':'C.UTF-8','PYTHONUNBUFFERED':'1',
            'XDG_RUNTIME_DIR':'/run/user/'+str(os.getuid()),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',
            'MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1',**(env or {})},stdout=log,stderr=subprocess.STDOUT,
        start_new_session=True,preexec_fn=limits)
    registered[name]={'pid':p.pid,'start_ticks':pathlib.Path('/proc/'+str(p.pid)+'/stat').read_text().split()[21],
        'port':port,'command':list(map(str,cmd)),'boot_id':boot_id(),'unit':unit+'.scope'}
    (LOCAL/'resources.json').write_text(json.dumps(registered,indent=2)+'\n')


def ensure_watchdog():
    ensure_slice()
    p=LOCAL/'watchdog.json'
    if p.exists() and live(json.loads(p.read_text())):return
    unit='eh158-watch-'+secrets.token_hex(5)
    log=(LOCAL/'watchdog.log').open('ab')
    process=subprocess.Popen(['systemd-run','--user','--scope','--quiet','--unit='+unit,
        '-p','MemoryMax=64M','-p','TasksMax=16','taskset','-c',str(CPU),sys.executable,
        '-m','engine_hub.resources','watchdog'],cwd=REPO,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    p.write_text(json.dumps({'pid':process.pid,'start_ticks':pathlib.Path('/proc/'+str(process.pid)+'/stat').read_text().split()[21],
        'boot_id':boot_id(),'unit':unit+'.scope'}))


def stop(name):
    r=registry().get(name)
    if r and live(r):
        if r.get('unit','').startswith('eh158-') and r['unit'].endswith('.scope'):
            cg=subprocess.check_output(['systemctl','--user','show',r['unit'],'-p','ControlGroup','--value'],text=True).strip()
            if '/eh158.slice/' not in cg:raise RuntimeError('Stop containment identity mismatch')
            subprocess.run(['systemctl','--user','stop',r['unit']],check=True,capture_output=True,timeout=12)
            return
        os.killpg(r['pid'],signal.SIGTERM)
        for _ in range(50):
            if not live(r):
                break
            time.sleep(.1)
        if live(r):
            os.killpg(r['pid'],signal.SIGKILL)


def bwrap(home,workspace,companion=False):
    prefix=PY.resolve().parent.parent
    args=['/usr/bin/bwrap','--unshare-user','--unshare-pid','--unshare-ipc','--unshare-uts',
        '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib',
        '--symlink','usr/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
        '--dir','/etc','--ro-bind','/etc/resolv.conf','/etc/resolv.conf','--ro-bind','/etc/hosts','/etc/hosts']
    for path in dict.fromkeys([prefix,PY.parent.parent,HERMES]):
        args+=['--ro-bind',str(path),str(path)]
    args+=['--ro-bind',str(prefix),str(pathlib.Path(os.readlink(PY)).parent.parent)]
    args+=['--dir','/app','--dir','/app/engine_hub']
    group,_=ensure_slice()
    args+=['--ro-bind',str(group),str(group)]
    for p in ROOT.glob('*.py'):
        args+=['--ro-bind',str(p),'/app/engine_hub/'+p.name]
    args+=['--bind',str(home),'/state','--bind',str(workspace),'/workspace','--chdir','/app']
    if companion:
        args+=['--dir','/control','--ro-bind',str(LOCAL/'node-control'/ (home.parent.name+'.json')),'/control/config.json']
    return args


def initialize():
    actual=subprocess.check_output(['git','-C',str(HERMES),'rev-parse','HEAD'],text=True).strip()
    if actual!='345cd2b057a452236de401d3534b8502a7465e8d' or subprocess.run(['git','-C',str(HERMES),'diff','--quiet'],capture_output=True).returncode:
        raise RuntimeError('Hermes source version or tracked state drift; no resources started')
    cfg=json.loads((LOCAL/'config.json').read_text())
    for n in cfg['nodes']:
        home=LOCAL/'nodes'/n['id']/'home'
        workspace=home.parent/'workspace'
        for p in [home,workspace,home/'memories']:
            p.mkdir(parents=True,exist_ok=True,mode=0o700)
        contents={home/'memories/MEMORY.md':'NODE_MEMORY:'+n['engine']+':'+n['id'],
            workspace/'node-evidence.txt':'NODE_WORKSPACE:'+n['engine']+':'+n['id'],
            home/'SOUL.md':'Read-only '+n['engine']+' node; never publish private state automatically.'}
        for p,text in contents.items():
            if not p.exists():
                p.write_text(text)
        cp=home/'companion-config.json'
        reader={k:n[k] for k in ['id','engine','state_url','consume_key','asset_key']}
        cp.write_text(json.dumps({'assets_url':cfg['assets_url'],'node':reader}));cp.chmod(0o600)
        control=LOCAL/'node-control'/ (n['id']+'.json');control.parent.mkdir(exist_ok=True,mode=0o700)
        control.write_text(json.dumps({'assets_url':cfg['assets_url'],'node':n}));control.chmod(0o600)
        adoption={'node':n['id'],'engine':n['engine'],'other_host_paths':
            [str(LOCAL/'nodes'/nn['id']/'home') for nn in cfg['nodes'] if nn['id']!=n['id']]+[str(LOCAL/'secrets.json')]}
        (home/'adoption.json').write_text(json.dumps(adoption))
        config={'gateway':{'multiplex_profiles':False},'model':{'default':'webui-node-fixture','provider':'custom',
            'base_url':'http://127.0.0.1:15803/v1','api_key':'local-fixture-only','streaming':False},
            'platforms':{'api_server':{'enabled':True,'extra':{'host':'127.0.0.1','port':15810+int(n['id'][-2:]),'key':n['key']}}},
            'platform_toolsets':{'api_server':['mcp-ops']},
            'mcp_servers':{'ops':{'command':str(PY),'args':['/app/engine_hub/node_mcp.py'],'env':{'HERMES_HOME':'/state'}}},
            'memory':{'memory_enabled':False,'user_profile_enabled':False},'terminal':{'cwd':'/workspace'},'agent':{'max_turns':5}}
        p=home/'config.yaml'
        if not p.exists():
            p.write_text(json.dumps(config));p.chmod(0o600)
    return cfg


def start_state(n):
    home=LOCAL/'nodes'/n['id']/'home';workspace=home.parent/'workspace'
    number=int(n['id'][-2:])
    start(n['id']+'-state',bwrap(home,workspace,True)+[PY,'-m','engine_hub.service','companion',
        '--config','/control/config.json','--state','/state/companion.db','--port',15820+number],
        {'HOME':'/state','HERMES_HOME':'/state'},15820+number)


def start_node(n):
    home=LOCAL/'nodes'/n['id']/'home';workspace=home.parent/'workspace';number=int(n['id'][-2:])
    active=[name for name,r in registry().items() if name.startswith('node-') and not name.endswith('-state') and live(r)]
    if n['id'] not in active and len(active)>=2:
        raise RuntimeError('At most two active Gateway nodes; retire an idle owned node first')
    start_state(n)
    start(n['id'],bwrap(home,workspace)+[PY,'-m','hermes_cli.main','gateway','run'],
        {'HOME':'/state','HERMES_HOME':'/state','API_SERVER_KEY':n['key'],'API_SERVER_HOST':'127.0.0.1',
            'API_SERVER_PORT':str(15810+number),'OPENAI_API_KEY':'local-fixture-only',
            'OPENAI_BASE_URL':'http://127.0.0.1:15803/v1','HERMES_TELEMETRY_ENABLED':'false',
            **({'OPENAI_API_KEY':n['key'],'OPENAI_BASE_URL':'http://127.0.0.1:15806/v1'} if n.get('model')=='codex-luna-bridge' else {})},15810+number)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['start','status','stop','restart-ui','stop-node','start-node'])
    p.add_argument('node',nargs='?');p.add_argument('--nodes',default='node-01');a=p.parse_args()
    if a.action=='start':
        cfg=initialize()
        start('fixture',[PY,'-m','engine_hub.scripts.model_fixture'],port=15803)
        if cfg.get('model_bridge'):
            start('luna-bridge',[sys.executable,'-m','engine_hub.luna_bridge'],port=15806)
        for kind,port in [('assets',15805),('manager',15804)]:
            start(kind,[sys.executable,'-m','engine_hub.service',kind,'--config',LOCAL/'config.json',
                '--state',LOCAL/(kind+'.db'),'--port',port],port=port)
        selected=[n for n in a.nodes.split(',') if n]
        if len(set(selected))>2 or any(n not in {x['id'] for x in cfg['nodes']} for n in selected):
            raise RuntimeError('Explicit batch must contain one or two registered nodes')
        for n in [n for n in cfg['nodes'] if n['id'] in selected]:
            start_node(n)
        start('ui',[sys.executable,'-m','engine_hub.service','ui','--config',LOCAL/'config.json',
            '--state',LOCAL/'ui.db','--port',15800],port=15800)
    elif a.action=='stop':
        for name in reversed(list(registry())):
            stop(name)
    elif a.action=='stop-node':
        assert a.node in ['node-'+str(i).zfill(2) for i in range(1,7)]
        stop(a.node)
        stop(a.node+'-state')
    elif a.action=='start-node':
        cfg=initialize();start_node(next(n for n in cfg['nodes'] if n['id']==a.node))
    elif a.action=='restart-ui':
        stop('ui')
        start('ui',[sys.executable,'-m','engine_hub.service','ui','--config',LOCAL/'config.json',
            '--state',LOCAL/'ui.db','--port',15800],port=15800)
    print(json.dumps({name:{'pid':r['pid'],'start_ticks':r['start_ticks'],'port':r['port'],'running':live(r)}
        for name,r in registry().items()},indent=2))


if __name__=='__main__':
    main()
