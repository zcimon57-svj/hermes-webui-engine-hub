"""Actual HTTP/Gateway/MCP/WeKnora probes. Never treats fixture as semantic quality."""
import concurrent.futures
import datetime
import http.cookiejar
import json
import pathlib
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from engine_hub.common import request,canonical,digest,Fault
from engine_hub.assets import ReleaseClient,WeKnoraClient
from engine_hub.manager import ManagerClient

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:15800'
TRACE=[]
CHECKS=[]


class Client:
    def __init__(self,name,password):
        self.name=name;self.csrf=''
        self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(self.jar))
        st,obj=self.api('/login','POST',{'username':name,'password':password},record=False)
        assert st==200,(st,obj)
        self.csrf=obj['csrf'];self.user=obj['user']

    def api(self,path,method='GET',body=None,record=True,headers=None):
        h={'Content-Type':'application/json','X-CSRF-Token':self.csrf,**(headers or {})}
        req=urllib.request.Request(BASE+'/api'+path,method=method,
            data=None if body is None else json.dumps(body).encode(),headers=h)
        try:
            with self.opener.open(req,timeout=65) as r:
                st=r.status;raw=r.read().decode()
                obj=raw if r.headers.get('Content-Type','').startswith('text/event-stream') else json.loads(raw)
        except urllib.error.HTTPError as e:
            st=e.code;obj=json.load(e)
        if record:
            TRACE.append({'actor':self.name,'path':path,'method':method,'status':st,
                'result':obj if path!='/me' else {'user':obj.get('user')}})
        return st,obj

    def ok(self,path,method='GET',body=None):
        st,obj=self.api(path,method,body)
        assert st==200,(self.name,path,st,obj)
        return obj

    def denied(self,path,method='GET',body=None,status=None):
        st,obj=self.api(path,method,body)
        assert st==(status or st) and st in [400,401,403,404,405,409,410],(path,st,obj)
        return obj


def check(name,condition,detail=None):
    CHECKS.append({'name':name,'pass':bool(condition),'detail':detail})
    assert condition,(name,detail)


def terminal(client,id):
    deadline=time.monotonic()+80
    while time.monotonic()<deadline:
        result=client.ok('/runs/'+id)
        if result['status'] in ['completed','cancelled','failed','expired','interrupted']:
            return result
        time.sleep(1)
    raise AssertionError('Run timeout: '+id)


def identity(report):
    def visit(obj):
        if isinstance(obj,dict):
            if obj.get('marker')=='REAL_NODE_IDENTITY':
                return obj
            for v in obj.values():
                result=visit(v)
                if result:return result
        elif isinstance(obj,list):
            for v in obj:
                result=visit(v)
                if result:return result
        elif isinstance(obj,str):
            try:
                return visit(json.loads(obj))
            except ValueError:
                return None
        return None
    content=report.split('SYNTHETIC_PROTOCOL_REPORT\n',1)[-1]
    found=visit(content)
    if not found:
        # Hermes labels external tool content. Parse complete JSON objects inside
        # the retained wrapper; never infer the node from a text substring.
        decoder=json.JSONDecoder()
        for i,char in enumerate(content):
            if char=='{':
                try:
                    obj,_=decoder.raw_decode(content[i:])
                    found=visit(obj)
                    if found:break
                except ValueError:
                    pass
    if not found:
        raise AssertionError('No actual MCP identity: '+report[:500])
    return found


def main():
    cfg=json.loads((ROOT/'.local/config.json').read_text())
    secrets_=json.loads((ROOT/'.local/secrets.json').read_text())
    users={n:Client(n,p) for n,p in secrets_['passwords'].items()}
    admin,viewer,chat,reviewer,restricted=(users[n] for n in ['admin','viewer','chat','reviewer','restricted'])
    check('distinct_identity_roles',len({u.user['id'] for u in [admin,viewer,chat]})==3)
    for path,method,body in [('/ask','POST',{'text':'pg question'}),('/route','POST',{'text':'pg'}),
        ('/config','PATCH',{'node':'node-03','enabled':False}),('/users','POST',{}),
        ('/assets/pg/candidates','POST',{}),('/nodes/node-03/state/memory','PUT',{})]:
        viewer.denied(path,method,body,403)
    for path in ['/config','/diagnostics','/users','/nodes/node-03/state/memory']:
        chat.denied(path,status=403)
    admin.denied('/assets/pg/rollback','POST',{'base':'invalid','target':'invalid'},403)
    chat.denied('/assets/pg/candidates','POST',{},403)
    req=urllib.request.Request(BASE+'/api/summary',headers={'X-Forwarded-User':'admin','X-Auth-Request-User':'admin'})
    try:
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req)
        raise AssertionError('Spoofed identity accepted')
    except urllib.error.HTTPError as e:
        check('untrusted_headers_denied',e.code==401)
    st,_=chat.api('/ask','POST',{'text':'PG'},headers={'X-CSRF-Token':''})
    check('csrf_denied',st==403)
    route=chat.ok('/route','POST',{'text':'lock wait','instance':'pg-test'})
    check('instance_route',route['engine']=='pg' and route['reason']=='registered_instance')
    ambiguity=chat.denied('/route','POST',{'text':'锁等待'},409)
    check('ambiguity_no_default',ambiguity['error']=='clarification_required')
    chat.denied('/route','POST',{'text':'PG','profile':'mysql-node-01'},400)
    restricted.denied('/route','POST',{'text':'mysql','engine':'mysql'},404)
    check('restricted_aggregate', {n['engine'] for n in restricted.ok('/summary')['nodes']}=={'pg'})
    restricted.denied('/assets/mysql/current',status=404)
    check('admin_sanitized_config','key' not in canonical(admin.ok('/config')))
    admin.ok('/config','PATCH',{'node':'node-03','enabled':False})
    admin.ok('/config','PATCH',{'node':'node-03','enabled':True})
    check('admin_audited_config',any(x['action']=='config_write' for x in admin.ok('/diagnostics')['audit']))
    nodes=admin.ok('/summary')['nodes']
    check('six_actual_health',len(nodes)==6 and all(n['online'] for n in nodes),nodes)
    runs=[]
    # Pool rotation must reach both independent nodes of each duplicated engine.
    for engine in ['mysql','pg','cassandra','cassandra','redis','redis']:
        result=admin.ok('/ask','POST',{'text':engine+' read approved remote knowledge, Skill script and identity','engine':engine})
        run=terminal(admin,result['run']['id']);actual=identity(run['report'])
        check('actual_identity_'+run['node'],run['node']==actual['node'] and engine==actual['engine'],actual)
        check('remote_consumption_'+run['node'],actual['release']==run['knowledge_release'] and bool(actual['script_output']) and actual['other_node_paths_denied'])
        check('report_sha_'+run['node'],digest(run['report'])==run['report_sha256'])
        runs.append(run)
    check('all_six_routed',{r['node'] for r in runs}=={n['id'] for n in cfg['nodes']})
    pg=next(r for r in runs if r['engine']=='pg')
    follow=admin.ok('/ask','POST',{'text':'followup without engine','conversation':pg['conversation']})
    followed=terminal(admin,follow['run']['id'])
    check('same_session_new_run',followed['conversation']==pg['conversation'] and followed['id']!=pg['id'] and followed['node']==pg['node'])
    switched=admin.ok('/ask','POST',{'text':'redis explicit switch','conversation':pg['conversation'],'engine':'redis'})
    switched=terminal(admin,switched['run']['id'])
    check('engine_switch_new_state',switched['conversation']!=pg['conversation'] and identity(switched['report'])['engine']=='redis')
    chat.denied('/runs/'+pg['id'],status=404)
    chat.denied('/runs/'+pg['id']+'/events',status=404)
    chat.denied('/runs/'+pg['id']+'/download',status=404)
    admin.ok('/conversations/'+pg['conversation']+'/share','POST',{'users':['viewer','chat']})
    viewer.ok('/runs/'+pg['id']);viewer.ok('/runs/'+pg['id']+'/events');viewer.ok('/runs/'+pg['id']+'/download')
    chat.denied('/runs/'+pg['id']+'/cancel','POST',{},403)
    viewer.denied('/ask','POST',{'text':'followup','conversation':pg['conversation']},403)
    check('private_then_explicit_read_share',True)
    # Real cancellation rather than removing a browser spinner.
    asked=chat.ok('/ask','POST',{'text':'redis cancellation FIXTURE_DELAY=8','engine':'redis'})
    cancelled=chat.ok('/runs/'+asked['run']['id']+'/cancel','POST',{})
    cancelled=terminal(chat,cancelled['id'])
    check('actual_gateway_cancel',cancelled['status']=='cancelled',cancelled)
    # Scoped remote state write/readback and actual MCP consumption.
    state=admin.ok('/nodes/node-03/state/memory')
    changed=admin.ok('/nodes/node-03/state/memory','PUT',{'base_sha256':state['sha256'],'content':'NODE_MEMORY:pg:node-03:REMOTE_UPDATED:'+secrets.token_hex(8)})
    admin.denied('/nodes/node-03/state/memory','PUT',{'base_sha256':state['sha256'],'content':'stale'},409)
    check('remote_state_readback',admin.ok('/nodes/node-03/state/memory')['sha256']==changed['sha256'])
    readrun=admin.ok('/ask','POST',{'text':'pg remote state readback','engine':'pg'})
    readrun=terminal(admin,readrun['run']['id'])
    check('remote_state_consumed',identity(readrun['report'])['memory_marker']==changed['content'])
    for n in cfg['nodes']:
        try:
            request(n['state_url'],'/v1/identity',token='wrong-key')
            raise AssertionError('Wrong node key accepted')
        except Fault as e:
            check('wrong_key_'+n['id'],e.details.get('upstream_status')==401)
        other=next(x for x in cfg['nodes'] if x['id']!=n['id'])
        try:
            ownrun=next(r for r in runs if r['node']==n['id'])
            request(n['url'],'/v1/runs/'+ownrun['gateway_run'],token=other['key'])
            raise AssertionError('Other node key accepted')
        except Fault as e:
            check('other_node_key_'+n['id'],e.details.get('upstream_status')==401)
    admin.denied('/nodes/node-03/state/..%2Fconfig.yaml')
    # Native WeKnora wrong-tenant proof, not only central UI filtering.
    remote=WeKnoraClient(cfg['weknora']['base'],cfg['weknora']['identities'])
    approved=ReleaseClient(cfg).call('pg','/current')
    wrong_doc=approved['documents']['knowledge']['id']
    try:
        remote.read('mysql',wrong_doc)
        raise AssertionError('WeKnora cross-tenant content accepted')
    except Fault as e:
        check('real_weknora_cross_tenant_denied',e.details.get('upstream_status') in [403,404])
    # Independent users concurrently call endpoints with separate cookies.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        identities=list(pool.map(lambda c:c.ok('/me')['user']['id'],[admin,viewer,chat]))
    check('concurrent_identity_no_bleed',identities==['admin','viewer','chat'])
    check('manager_report_delivery_contract',ManagerClient(cfg).report(pg['id'])['sha256']==pg['report_sha256'] and ManagerClient(cfg).delivery(pg['id'])['external_delivery']=='NOT_RUN')
    (ROOT/'.local/verified-runs.json').write_text(json.dumps(runs,indent=2)+'\n')


if __name__=='__main__':
    name=datetime.datetime.now(datetime.timezone.utc).strftime('live-%Y%m%dT%H%M%S')
    status='PASS';error=None
    try:
        main()
    except Exception as e:
        status='FAIL';error=str(e)
        raise
    finally:
        data={'status':status,'error':error,'checks':CHECKS,'trace':TRACE,
            'boundary':'Actual UI HTTP, Hermes Gateway, MCP and WeKnora. Deterministic model and synthetic content; domain/production NOT_RUN.'}
        (ROOT/'evidence'/ (name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        print(json.dumps({'status':status,'checks':len(CHECKS),'evidence':name+'.json','error':error}))
