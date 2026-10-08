"""Create test identities and remote KBs only in the owned WeKnora instance."""
import json
import pathlib
import secrets
import subprocess
import time
from engine_hub.common import request, Fault
from engine_hub.auth import Identity
from engine_hub.common import Store

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL = ROOT/'.local'
ENGINES = ['mysql','pg','cassandra','redis']
TOPOLOGY = [('node-01','mysql'),('node-02','cassandra'),('node-03','pg'),
    ('node-04','redis'),('node-05','cassandra'),('node-06','redis')]


def main():
    base='http://127.0.0.1:15802'
    for _ in range(40):
        try:
            request(base,'/health')
            break
        except Fault:
            time.sleep(1)
    secretfile = LOCAL/'secrets.json'
    if not secretfile.exists():
        secretfile.write_text(json.dumps({'passwords':{name:secrets.token_urlsafe(18) for name in
            ['admin','viewer','chat','reviewer','restricted']},'remote':{},
            'service_keys':{name:secrets.token_hex(24) for name in ['manager','assets','node_admin']},
            'nodes':{n:{'key':secrets.token_hex(24),'asset_key':secrets.token_hex(24)} for n,e in TOPOLOGY}}))
        secretfile.chmod(0o600)
    s=json.loads(secretfile.read_text())
    def save():
        secretfile.write_text(json.dumps(s,indent=2)+'\n')
    for identity in s['nodes'].values():
        identity.setdefault('consume_key',secrets.token_hex(24))
        identity.setdefault('state_admin_key',secrets.token_hex(24))
    save()
    ip=json.loads(subprocess.check_output(['docker','inspect','eh158r-embedding'],text=True))[0]['NetworkSettings']['Networks']['eh158-net']['IPAddress']
    evidence = {}
    for e in ENGINES:
        if e not in s['remote']:
            password=secrets.token_urlsafe(24)
            request(base,'/api/v1/auth/register','POST',{'username':'eh158-'+e,'email':e+'@eh158.example.test','password':password})
            s['remote'][e]={'password':password,'email':e+'@eh158.example.test'}
            save()
        r=s['remote'][e]
        login=request(base,'/api/v1/auth/login','POST',{'email':r['email'],'password':r['password']})
        r['token']=login['token']
        if not r.get('embedding_id'):
            model=request(base,'/api/v1/models','POST',{'name':'eh158-deterministic-embedding','type':'embedding','source':'remote',
                'parameters':{'base_url':'http://'+ip+':8080/v1','api_key':'local-fixture-only',
                'embedding_parameters':{'dimension':384}}},r['token'])
            r['embedding_id']=model['data']['id']
            save()
        if not r.get('kb_id'):
            kb=request(base,'/api/v1/knowledge-bases','POST',{'name':e+'-approved-assets','type':'document',
                'embedding_model_id':r['embedding_id'],'chunking_config':{'chunk_size':512,'chunk_overlap':50,'separators':['\n']}},r['token'])
            r['kb_id']=kb['data']['id']
            save()
        try:
            skills=request(base,'/api/v1/skills',token=r['token'])
            evidence[e]={'skills_api':skills,'kb_id':r['kb_id']}
        except Fault as error:
            evidence[e]={'skills_api_error':error.code,'details':error.details,'kb_id':r['kb_id']}
    save()
    cfg={'schema':'engine-hub-config/1','owned_local_lab':True,'ui_port':15800,'manager_url':'http://127.0.0.1:15804',
        'assets_url':'http://127.0.0.1:15805','service_keys':s['service_keys'],
        'weknora':{'base':base,'identities':{e:{'token':r['token'],'kb_id':r['kb_id']} for e,r in s['remote'].items()}},
        'nodes':[{'id':n,'engine':e,'url':'http://127.0.0.1:'+str(15810+int(n[-2:])),
            'state_url':'http://127.0.0.1:'+str(15820+int(n[-2:])),**s['nodes'][n],
            'max_running':1,'enabled':True} for n,e in TOPOLOGY],
        'instances':{e+'-test':{'engine':e,'space':e+'-ops'} for e in ENGINES}}
    p=LOCAL/'config.json'
    if p.exists():
        old=json.loads(p.read_text())
        # Preserve user-maintained runtime policy and node configuration on reseed.
        cfg.update({k:old[k] for k in ['nodes','instances','classifier','model_bridge','owned_local_lab'] if k in old})
        for node in cfg['nodes']:
            node.update(s['nodes'][node['id']])
    p.write_text(json.dumps(cfg,indent=2)+'\n');p.chmod(0o600)
    store=Store(LOCAL/'ui.db');identity=Identity(store)
    for name in s['passwords']:
        if not store.get('users',name):
            role='viewer' if name=='viewer' else 'chat' if name in ['chat','restricted'] else 'admin'
            extras=['candidate'] if name=='admin' else ['evaluate','publish'] if name=='reviewer' else []
            identity.add(name,s['passwords'][name],role,['pg'] if name=='restricted' else ENGINES,extras)
    (ROOT/'evidence'/('weknora-capabilities-'+str(time.time_ns())+'.json')).write_text(json.dumps({'actual_instance':base,
        'container_image_source':'d97ad7a4','adjacent_source_head':'1edcd54b43606d9079bb36650efe3f68707a79ea',
        'source_is_not_runtime':True,'skill_adapter':'Versioned package stored as remote WeKnora manual content, read/verified through RemoteSkillProvider; not native sandbox installation',
        'identities':evidence},indent=2)+'\n')
    print('Five distinct local identities and four isolated remote WeKnora tenants prepared.')


if __name__=='__main__':
    main()
