"""Versioned Manager client and transparent local reference (not the internal Manager)."""
import json
import secrets
import threading
import time
import urllib.parse
from .common import Fault, Store, canonical, digest, request
from .assets import ReleaseClient

TERMINAL = {'completed','cancelled','failed','expired','interrupted'}

def serialized(method):
    def wrapped(self,*args,**kwargs):
        with self.operations:
            return method(self,*args,**kwargs)
    return wrapped


class ManagerClient:
    def __init__(self,cfg):
        self.base,self.key = cfg['manager_url'],cfg['service_keys']['manager']

    def call(self,path,method='GET',data=None):
        return request(self.base,'/v1'+path,method,data,self.key,timeout=60,service=True)

    def submit(self,data):
        return self.call('/runs','POST',data)

    def query(self,id):
        return self.call('/runs/'+id)

    def cancel(self,id,actor):
        return self.call('/runs/'+id+'/cancel','POST',{'actor':actor})

    def events(self,id):
        return self.call('/runs/'+id+'/events')

    def recovery(self):
        return self.call('/recovery','POST',{})

    def report(self,id):
        return self.call('/runs/'+id+'/report')

    def delivery(self,id):
        return self.call('/runs/'+id+'/delivery')


class ReferenceManager:
    def __init__(self,store,cfg):
        self.store,self.cfg = store,cfg
        self.assets = ReleaseClient(cfg)
        from .supervisor import WorkerSupervisor
        self.supervisor=WorkerSupervisor(cfg,store)
        self.admission = threading.Lock()
        self.operations = threading.RLock()
        for n in cfg['nodes']:
            prior=store.get('node_policy',n['id'])
            if prior:
                n['enabled']=prior['enabled']
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.reconcile,daemon=True,name='reference-reconciler')
        self.worker.start()

    def node(self,id):
        return next(n for n in self.cfg['nodes'] if n['id']==id)

    def endpoint_snapshot(self,n):
        return {'gateway_url':n['url'],'state_url':n['state_url'],
            'gateway_identity_sha256':digest(n['key']),'state_identity_sha256':digest(n['state_admin_key'])}

    def run_node(self,r):
        n=self.node(r['node'])
        if r.get('endpoint_snapshot') and r['endpoint_snapshot']!=self.endpoint_snapshot(n):
            raise Fault(409,'persisted_run_endpoint_drift')
        return n

    def verify_node(self,node):
        identity=request(node['state_url'],'/v1/identity',token=node['state_admin_key'])
        health=request(node['url'],'/health',token=node['key'])
        if identity['node']!=node['id'] or identity['engine']!=node['engine']:
            raise Fault(503,'node_identity_drift')
        if health.get('version')!='0.21.3':raise Fault(503,'gateway_version_drift')

    def eligible(self,engine):
        live=[]
        rows=self.store.all('runs')
        if self.cfg.get('owned_local_lab'):
            available=[n for n in self.cfg['nodes'] if n['engine']==engine and n['enabled'] and
                sum(r['node']==n['id'] and r['status'] not in TERMINAL for r in rows)<n['max_running']]
            if not available:raise Fault(503,'no_eligible_node')
            chosen=min(available,key=lambda n:sum(r['node']==n['id'] for r in rows))
            self.supervisor.ensure(chosen)
            self.verify_node(chosen)
            return chosen
        for n in self.cfg['nodes']:
            if n['engine']!=engine or not n['enabled']:
                continue
            count=sum(r['node']==n['id'] and r['status'] not in TERMINAL for r in rows)
            if count>=n['max_running']:
                continue
            try:
                identity=request(n['state_url'],'/v1/identity',token=n['state_admin_key'])
                request(n['url'],'/health',token=n['key'])
                if identity['node']!=n['id'] or identity['engine']!=engine:
                    continue
                live.append(n)
            except Fault:
                continue
        if not live:
            candidates=[n for n in self.cfg['nodes'] if n['engine']==engine and n['enabled']]
            if not candidates:raise Fault(503,'no_eligible_node')
            chosen=min(candidates,key=lambda n:sum(r['node']==n['id'] for r in rows))
            self.supervisor.ensure(chosen)
            request(chosen['url'],'/health',token=chosen['key'])
            live=[chosen]
        # Bounded pool policy; historical load rotates same-engine nodes.
        return min(live,key=lambda n:sum(r['node']==n['id'] for r in rows))

    def event(self,id,kind,detail):
        self.store.audit({'run':id,'event':kind,'at':time.time(),**detail})

    def submit(self,b):
        required={'owner','engine','space','conversation','input_revision','text','routing','allowed_engines'}
        if not required <= set(b) or b['engine'] not in b['allowed_engines']:
            raise Fault(400,'invalid_manager_input')
        key=digest(canonical({'owner':b['owner'],'input_revision':b['input_revision']}))
        fingerprint=digest(canonical(b))
        with self.admission:
            existing=self.store.get('idempotency',key)
            if existing:
                if existing['fingerprint']!=fingerprint:
                    raise Fault(409,'idempotency_conflict')
                return self.store.get('runs',existing['run'])
            rows=self.store.all('runs')
            if any(r['conversation']==b['conversation'] and r['status'] not in TERMINAL for r in rows):
                raise Fault(409,'conversation_busy')
            if sum(r['status'] not in TERMINAL for r in rows)>=6:
                raise Fault(429,'global_run_budget')
            pinned=next((r for r in rows if r['conversation']==b['conversation']),None)
            n=self.node(pinned['node']) if pinned else self.eligible(b['engine'])
            if pinned:
                # Existing session never silently migrates to a second node.
                if not n['enabled']:
                    raise Fault(503,'pinned_node_draining')
                if sum(r['node']==n['id'] and r['status'] not in TERMINAL for r in rows)>=n['max_running']:
                    raise Fault(429,'pinned_node_budget')
                self.supervisor.ensure(n)
                self.verify_node(n)
                request(n['url'],'/health',token=n['key'])
            release=self.assets.call(b['engine'],'/current')
            bundle=self.assets.call(b['engine'],'/releases/'+release['id'])
            id='manager-'+secrets.token_hex(12)
            context_id=secrets.token_hex(16)
            body={'model':n.get('model','webui-node-fixture'),'input':b['text']+'\nHUB_CONTEXT='+context_id,
                'session_id':b['conversation'], 'instructions':'Read-only contract validation. Use ops_evidence with context_id '+context_id+'.',
                'conversation_history':b.get('history',[])}
            row={'id':id,'owner':b['owner'],'engine':b['engine'],'space':b['space'],'conversation':b['conversation'],
                'input_revision':b['input_revision'],'routing':b['routing'],'node':n['id'],
                'attempt':1,'status':'dispatching','cancel_requested':False,'gateway_run':None,
                'endpoint_snapshot':self.endpoint_snapshot(n),
                'knowledge_release':release['id'],'skill_release':release['id'],'bundle_sha256':release['bundle_sha256'],
                'context_id':context_id,'request':body,'at':time.time(), 'shared_with':b.get('shared_with',[]),
                'reference_boundary':'LOCAL_REFERENCE_NOT_INTERNAL_MANAGER',
                'model':body['model'],
                'context':{'id':context_id,'owner':b['owner'],'conversation':b['conversation'],
                    'engine':b['engine'],'release':release['id'],'bundle_sha256':release['bundle_sha256']}}
            # Persist exact target + request before external side effects.
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                self.store.put('runs',id,row,db)
                self.store.put('idempotency',key,{'run':id,'fingerprint':fingerprint},db)
            self.event(id,'admitted',{'node':n['id'],'release':release['id']})
            return self.dispatch(row)

    @serialized
    def dispatch(self,r):
        n=self.run_node(r)
        request(n['state_url'],'/v1/contexts','POST',r['context'],n['state_admin_key'],timeout=20,service=True)
        admitted=request(n['url'],'/v1/runs','POST',r['request'],n['key'],
            headers={'Idempotency-Key':'enginehub-'+r['id'],
                'X-Hermes-Session-Id':r['conversation'],'X-Hermes-Session-Key':'hub:'+r['conversation']}, timeout=15)
        gateway=admitted.get('run_id',admitted.get('id'))
        if not gateway:
            raise Fault(502,'missing_gateway_run')
        # Preserve cancellation that arrived while admission was in flight.
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=self.store.get('runs',r['id'],db)
            current.update({'gateway_run':gateway,'status':'running'})
            self.store.put('runs',r['id'],current,db)
        self.event(r['id'],'dispatched',{'gateway_run':gateway,'node':n['id']})
        return current

    @serialized
    def refresh(self,r):
        r=self.store.get('runs',r['id'])
        if r['status'] in TERMINAL:
            return r
        if not r['gateway_run']:
            # The same persisted key/body re-admits an acknowledged or uncertain request.
            r=self.dispatch(r)
        n=self.run_node(r)
        if r['cancel_requested']:
            request(n['url'],'/v1/runs/'+r['gateway_run']+'/stop','POST',{},n['key'])
        remote=request(n['url'],'/v1/runs/'+r['gateway_run'],token=n['key'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            latest=self.store.get('runs',r['id'],db)
            if latest['status'] in TERMINAL:
                return latest
            latest['status']=remote['status']
            latest['observed_at']=time.time()
            if latest['status'] in TERMINAL:
                output=remote.get('output') or ''
                if not isinstance(output,str):
                    output=canonical(output)
                latest['report']=output
                latest['report_sha256']=digest(output)
                latest['delivery_receipt']={'id':'receipt-'+r['id'],'report_sha256':digest(output),
                    'target':'local-reference-report-store','external_delivery':'NOT_RUN'}
                if remote.get('error'):
                    # Keep failure evidence without reflecting raw provider secrets.
                    latest['failure']={'kind':'gateway_terminal_error','detail_available_in_node_record':True}
            self.store.put('runs',r['id'],latest,db)
        if latest['status'] in TERMINAL:
            self.event(r['id'],'terminal',{'status':latest['status'],'report_sha256':latest['report_sha256']})
        return latest

    @serialized
    def cancel(self,id,actor):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            r=self.store.get('runs',id,db)
            if not r:
                raise Fault(404,'not_found')
            if r['status'] in TERMINAL:
                return r
            r['cancel_requested']=True
            r['cancel_actor']=actor
            self.store.put('runs',id,r,db)
        self.event(id,'cancel_requested',{'actor':actor})
        return self.refresh(r)

    def reconcile(self):
        # One fixed worker, bounded network timeouts; no recursively-created helpers.
        while not self.stop.wait(1):
            for r in self.store.all('runs'):
                if r['status'] not in TERMINAL:
                    try:
                        self.refresh(r)
                    except Fault as e:
                        self.event(r['id'],'target_unavailable',{'error':e.code})

    def handle(self,h):
        token=h.headers.get('Authorization','').removeprefix('Bearer ')
        if not secrets.compare_digest(token,self.cfg['service_keys']['manager']):
            raise Fault(401,'service_auth_required')
        path=urllib.parse.urlsplit(h.path).path.split('/')
        if path==['','v1','runs']:
            result=self.store.all('runs') if h.command=='GET' else self.submit(h.body())
        elif len(path)==5 and path[1:3]==['v1','nodes'] and path[4]=='state-ready' and h.command=='POST':
            n=self.node(path[3]);self.supervisor.ensure_state(n)
            result={'node':n['id'],'state_service_ready':True}
        elif len(path)==4 and path[1:3]==['v1','nodes'] and h.command=='PATCH':
            n=next((n for n in self.cfg['nodes'] if n['id']==path[3]),None)
            if not n:
                raise Fault(404,'not_found')
            b=h.body()
            if not isinstance(b.get('enabled'),bool):
                raise Fault(400,'invalid_node_policy')
            n['enabled']=b['enabled']
            self.store.put('node_policy',n['id'],{'enabled':n['enabled']})
            self.store.audit({'action':'node_policy','node':n['id'],'actor':b.get('actor'),'enabled':n['enabled']})
            result={'node':n['id'],'enabled':n['enabled']}
        elif path==['','v1','recovery'] and h.command=='POST':
            rows=[]
            for r in self.store.all('runs'):
                try:
                    rows.append(self.refresh(r))
                except Fault:
                    rows.append(r)
            result={'runs':rows,'authority':'LOCAL_REFERENCE_NOT_INTERNAL_MANAGER'}
        elif len(path)>=4 and path[1:3]==['v1','runs']:
            r=self.store.get('runs',path[3])
            if not r:
                raise Fault(404,'not_found')
            if len(path)==4 and h.command=='GET':
                result=self.refresh(r)
            elif len(path)==5 and path[4]=='cancel' and h.command=='POST':
                result=self.cancel(r['id'],h.body()['actor'])
            elif len(path)==5 and h.command=='GET':
                if path[4]=='events':
                    with self.store.connect() as db:
                        result=[json.loads(x[0]) for x in db.execute('SELECT data FROM audit ORDER BY seq') if json.loads(x[0]).get('run')==r['id']]
                elif path[4]=='report':
                    r=self.refresh(r)
                    result={'report':r.get('report'),'sha256':r.get('report_sha256')}
                elif path[4]=='delivery':
                    result={'receipt':r.get('delivery_receipt'),'external_delivery':'NOT_RUN'}
                else:
                    raise Fault(404,'not_found')
            else:
                raise Fault(405,'method_not_allowed')
        else:
            raise Fault(404,'not_found')
        h.reply(200,result)
