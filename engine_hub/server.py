"""Unified browser boundary. Every route uses identity + capability + object scope."""
import json
import pathlib
import secrets
import time
import urllib.parse
from .common import Fault, canonical, request,digest
from .auth import Identity, owned, require, visible
from .routing import Router
from .manager import ManagerClient, TERMINAL
from .assets import ReleaseClient

PUBLIC_RUN_FIELDS = {'id','owner','engine','space','conversation','input_revision','node','attempt',
    'status','cancel_requested','gateway_run','knowledge_release','skill_release','bundle_sha256',
    'at','observed_at','report','report_sha256','delivery_receipt','reference_boundary','model','failure'}


class Hub:
    def __init__(self,store,cfg):
        self.store,self.cfg = store,cfg
        self.identity=Identity(store)
        self.router=Router(cfg['instances'])
        if cfg.get('classifier',{}).get('kind')=='codex-luna':
            from .codex_luna import CodexLuna
            from .routing import RuleClassifier
            model=CodexLuna(pathlib.Path(store.path).parent/'luna-ui',cfg['classifier'].get('executable'))
            class RulesThenLuna:
                def classify(self,text,allowed):
                    rule=RuleClassifier().classify(text,allowed)
                    return rule if rule['selected'] else model.classify(text,allowed)
            self.router=Router(cfg['instances'],RulesThenLuna())
        self.manager=ManagerClient(cfg)
        self.assets=ReleaseClient(cfg)
        import threading
        self.ask_lock=threading.Lock()
        for n in cfg['nodes']:
            prior=store.get('node_policy',n['id'])
            if prior:
                n['enabled']=prior['enabled']

    def static(self,h,path):
        root=pathlib.Path(__file__).parent
        files={'/':(root/'static/index.html','text/html; charset=utf-8'),
            '/hub.js':(root/'static/hub.js','application/javascript; charset=utf-8'),
            '/hub.css':(root/'static/hub.css','text/css; charset=utf-8'),
            '/upstream.css':(root.parent/'static/style.css','text/css; charset=utf-8')}
        if path not in files or h.command!='GET':
            return False
        p,mime=files[path]
        raw=p.read_bytes();h.send_response(200)
        for k,v in {'Content-Type':mime,'Content-Length':str(len(raw)),'Cache-Control':'no-store',
            'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            'X-Content-Type-Options':'nosniff'}.items():
            h.send_header(k,v)
        h.end_headers();h.wfile.write(raw)
        return True

    def nodes(self,u,extended=False):
        result=[]
        for n in self.cfg['nodes']:
            if n['engine'] not in u['engines']:
                continue
            row={'id':n['id'],'engine':n['engine'],'enabled':n['enabled'],'online':False}
            try:
                health=request(n['url'],'/health',token=n['key'],timeout=2)
                identity=request(n['state_url'],'/v1/identity',token=n['state_admin_key'],timeout=2)
                row['online']=identity['node']==n['id'] and identity['engine']==n['engine']
                row['version']=health.get('version')
            except Fault:
                pass
            if extended:
                row.update({'gateway_url':n['url'],'state_url':n['state_url'],'max_running':n['max_running']})
            result.append(row)
        return result

    def public_run(self,r):
        return {k:v for k,v in r.items() if k in PUBLIC_RUN_FIELDS}

    def conversation(self,u,id):
        row=self.store.get('conversations',id)
        owned(u,row)
        return row

    def project_conversation(self,c,manager_rows):
        # A read-only projection repairs a lost UI acknowledgement in the
        # browser without autosave or replaying an input from a Viewer GET.
        projected={**c,'turns':list(c['turns'])}
        for r in manager_rows:
            if r['conversation']!=c['id'] or r['owner']!=c['owner'] or r['engine']!=c['engine'] or r['space']!=c['space']:
                continue
            if any(t['run']==r['id'] for t in projected['turns']):continue
            key=digest(canonical({'owner':r['owner'],'revision':r['input_revision']}))
            intent=self.store.get('input_intents',key)
            if intent and intent['conversation']==c['id']:
                projected['turns'].append({'text':intent['payload']['text'],'input_revision':r['input_revision'],'run':r['id']})
        return projected

    def run(self,u,id):
        # Check local owner metadata before asking Manager; no existence oracle.
        ref=self.store.get('run_refs',id)
        if not ref:
            # Recover visibility after an acknowledgement was lost. GET never
            # submits, retries dispatch, or creates a conversation.
            found=next((r for r in self.manager.call('/runs') if r['id']==id),None)
            if found:
                c=self.store.get('conversations',found['conversation'])
                if c and visible(u,c) and found['owner']==c['owner'] and found['engine']==c['engine']:
                    ref={**found,'shared_with':c['shared_with']}
        owned(u,ref)
        return self.manager.query(id)

    def ask(self,u,b):
        with self.ask_lock:
            return self._ask(u,b)

    def _ask(self,u,b):
        require(u,'chat')
        if not isinstance(b.get('text'),str) or not 0<len(b['text'])<=8000:
            raise Fault(400,'invalid_question')
        revision=b.get('input_revision') or secrets.token_hex(16)
        if not isinstance(revision,str) or len(revision)>100:
            raise Fault(400,'invalid_input_revision')
        intent_key=digest(canonical({'owner':u['id'],'revision':revision}))
        fingerprint=digest(canonical({k:b.get(k) for k in ['text','engine','instance','conversation']}))
        prior=self.store.get('input_intents',intent_key)
        if prior:
            if prior['fingerprint']!=fingerprint:raise Fault(409,'idempotency_conflict')
            require(u,'chat',prior['engine'],prior['space'])
            conversation=self.conversation(u,prior['conversation'])
            result=self.manager.submit(prior['payload'])
            return self.settle_intent(u,conversation,result,b['text'],revision,prior,intent_key)
        old=self.conversation(u,b['conversation']) if b.get('conversation') else None
        if old and old['owner']!=u['id']:
            raise Fault(403,'shared_conversation_is_read_only')
        routing=self.router.select(u,b,old)
        require(u,'chat',routing['engine'],routing['space'])
        conversation=old
        if not old or old['engine']!=routing['engine']:
            id=secrets.token_hex(12)
            conversation={'id':id,'owner':u['id'],'engine':routing['engine'],'space':routing['space'],
                'title':b['text'][:70],'created_at':time.time(),'shared_with':[],'turns':[],
                'switched_from':old['id'] if old else None}
            self.store.put('conversations',id,conversation)
        existing=next((t for t in conversation['turns'] if t['input_revision']==revision),None)
        if existing:
            if existing['text']!=b['text']:
                raise Fault(409,'idempotency_conflict')
            return {'conversation':conversation,'run':self.public_run(self.run(u,existing['run']))}
        history=[]
        for t in conversation['turns'][-12:]:
            r=self.run(u,t['run'])
            history.append({'role':'user','content':t['text']})
            if r.get('report'):
                history.append({'role':'assistant','content':r['report']})
        payload={'owner':u['id'],'allowed_engines':u['engines'],'engine':routing['engine'],
            'space':routing['space'],'routing':routing,'conversation':conversation['id'],
            'input_revision':revision,'text':b['text'],'history':history,'shared_with':conversation['shared_with']}
        intent={'fingerprint':fingerprint,'conversation':conversation['id'],'owner':u['id'],
            'engine':routing['engine'],'space':routing['space'],'payload':payload,'run':None}
        self.store.put('input_intents',intent_key,intent)
        result=self.manager.submit(payload)
        return self.settle_intent(u,conversation,result,b['text'],revision,intent,intent_key)

    def settle_intent(self,u,conversation,result,text,revision,intent,intent_key):
        self.store.put('run_refs',result['id'],{'id':result['id'],'owner':u['id'],
            'engine':result['engine'],'space':result['space'],'shared_with':conversation['shared_with'],'conversation':conversation['id']})
        if not any(t['input_revision']==revision for t in conversation['turns']):
            conversation['turns'].append({'text':text,'input_revision':revision,'run':result['id']})
        self.store.put('conversations',conversation['id'],conversation)
        intent['run']=result['id'];self.store.put('input_intents',intent_key,intent)
        self.store.audit({'action':'ask','user':u['id'],'engine':result['engine'],'run':result['id'],'at':time.time()})
        return {'conversation':conversation,'run':self.public_run(result)}

    def handle(self,h):
        url=urllib.parse.urlsplit(h.path);path=url.path
        if self.static(h,path):
            return
        if path=='/api/login' and h.command=='POST':
            origin=h.headers.get('Origin')
            if origin and origin!='http://'+h.headers.get('Host',''):
                raise Fault(403,'origin_denied')
            b=h.body()
            user,token,csrf=self.identity.login(str(b.get('username','')),str(b.get('password','')))
            h.reply(200,{'user':user,'csrf':csrf},{'Set-Cookie':'hub_session='+token+'; HttpOnly; SameSite=Strict; Path=/'})
            return
        u,session=self.identity.authenticate(h)
        require(u,'read')
        if h.command not in ['GET','POST','PUT','PATCH','DELETE']:
            raise Fault(405,'method_not_allowed')
        if h.command!='GET' and u['role']=='viewer' and path!='/api/logout':
            raise Fault(403,'viewer_read_only')
        parts=path.split('/')
        if path=='/api/me' and h.command=='GET':
            result={'user':u,'csrf':session['csrf']}
        elif path=='/api/logout' and h.command=='POST':
            session['expires']=0
            from http.cookies import SimpleCookie
            from .common import digest
            c=SimpleCookie(h.headers['Cookie'])
            self.store.put('auth',digest(c['hub_session'].value),session)
            h.reply(200,{'logged_out':True},{'Set-Cookie':'hub_session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/'})
            return
        elif path=='/api/summary' and h.command=='GET':
            cached=self.manager.call('/runs')
            conversations=[self.project_conversation(c,cached) for c in self.store.all('conversations') if visible(u,c)]
            by_id={c['id']:c for c in conversations}
            result={'nodes':self.nodes(u),'engines':u['engines'],
                'conversations':conversations,
                'runs':[self.public_run(r) for r in cached if r['conversation'] in by_id and r['owner']==by_id[r['conversation']]['owner']
                    and r['engine']==by_id[r['conversation']]['engine'] and r['space']==by_id[r['conversation']]['space']],
                'manager':'LOCAL_REFERENCE_NOT_INTERNAL',
                'model_modes':{n['engine']:n.get('model','webui-node-fixture') for n in self.cfg['nodes'] if n['engine'] in u['engines']}}
        elif path=='/api/ask' and h.command=='POST':
            result=self.ask(u,h.body())
        elif path=='/api/route' and h.command=='POST':
            require(u,'chat')
            result=self.router.select(u,h.body())
            require(u,'chat',result['engine'],result['space'])
        elif parts[1:3]==['api','conversations'] and len(parts)>=4:
            c=self.conversation(u,parts[3])
            if h.command=='GET' and len(parts)==4:
                c=self.project_conversation(c,self.manager.call('/runs'))
                result={**c,'runs':[self.public_run(self.run(u,t['run'])) for t in c['turns']]}
            elif h.command=='POST' and len(parts)==5 and parts[4]=='share':
                require(u,'chat',c['engine'])
                if c['owner']!=u['id']:
                    raise Fault(403,'owner_required')
                b=h.body();names=b.get('users',[])
                if not isinstance(names,list):
                    raise Fault(400,'invalid_share')
                for name in names:
                    target=self.store.get('users',name)
                    if not target or c['engine'] not in target['engines']:
                        raise Fault(400,'share_scope_mismatch')
                c['shared_with']=names
                self.store.put('conversations',c['id'],c)
                for t in c['turns']:
                    ref=self.store.get('run_refs',t['run']);ref['shared_with']=names
                    self.store.put('run_refs',t['run'],ref)
                self.store.audit({'action':'share','user':u['id'],'conversation':c['id'],'users':names})
                result=c
            else:
                raise Fault(405,'method_not_allowed')
        elif parts[1:3]==['api','runs'] and len(parts)>=4:
            r=self.run(u,parts[3])
            if h.command=='GET' and len(parts)==4:
                result=self.public_run(r)
            elif h.command=='POST' and len(parts)==5 and parts[4]=='cancel':
                if r['owner']==u['id']:
                    require(u,'cancel_own',r['engine'])
                else:
                    require(u,'manage_runs',r['engine'])
                result=self.public_run(self.manager.cancel(r['id'],u['id']))
                self.store.audit({'action':'cancel','user':u['id'],'run':r['id']})
            elif h.command=='GET' and len(parts)==5 and parts[4]=='events':
                events=self.manager.events(r['id'])
                raw=('event: run\ndata: '+canonical({'run':self.public_run(r),'events':events})+'\n\n').encode()
                h.send_response(200);h.send_header('Content-Type','text/event-stream');h.send_header('Cache-Control','no-store')
                h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)
                return
            elif h.command=='GET' and len(parts)==5 and parts[4]=='download':
                result=self.manager.report(r['id'])
            else:
                raise Fault(405,'method_not_allowed')
        elif path=='/api/config':
            require(u,'config')
            if h.command=='GET':
                result={'nodes':self.nodes(u,True),'instances':{k:v for k,v in self.cfg['instances'].items() if v['engine'] in u['engines']},
                    'secrets':'REDACTED','tool_policy':'read_only'}
            elif h.command=='PATCH':
                if u.get('spaces') is not None:raise Fault(403,'engine_config_requires_engine_scope')
                b=h.body()
                if set(b)!={'node','enabled'} or not isinstance(b['enabled'],bool):
                    raise Fault(400,'config_allowlist')
                n=next((n for n in self.cfg['nodes'] if n['id']==b['node'] and n['engine'] in u['engines']),None)
                if not n:
                    raise Fault(404,'not_found')
                result=self.manager.call('/nodes/'+n['id'],'PATCH',{'enabled':b['enabled'],'actor':u['id']})
                n['enabled']=b['enabled']
                self.store.put('node_policy',n['id'],{'enabled':n['enabled']})
                self.store.audit({'action':'config_write','user':u['id'],'node':n['id'],'enabled':n['enabled']})
            else:
                raise Fault(405,'method_not_allowed')
        elif path=='/api/diagnostics' and h.command=='GET':
            require(u,'diagnostics')
            with self.store.connect() as db:
                audit=[json.loads(x[0]) for x in db.execute('SELECT data FROM audit ORDER BY seq DESC LIMIT 60')]
            result={'nodes':self.nodes(u,True),'audit':[r for r in audit if r.get('user')==u['id']],
                'limits':{'http_threads':24,'gateway_active_runs_per_node':1,'manager_active_runs':6,
                    'node_address_space_bytes':3*1024**3,'per_issue_arbitrary_code_isolation':'NOT_RUN'}}
        elif parts[1:3]==['api','nodes'] and len(parts)==6 and parts[4]=='state':
            require(u,'state')
            n=next((n for n in self.cfg['nodes'] if n['id']==parts[3] and n['engine'] in u['engines']),None)
            if not n:
                raise Fault(404,'not_found')
            if self.cfg.get('owned_local_lab'):
                self.manager.call('/nodes/'+n['id']+'/state-ready','POST',{})
            b=None
            if h.command=='PUT':
                b=h.body();b['actor']=u['id']
            elif h.command!='GET':
                raise Fault(405,'method_not_allowed')
            result=request(n['state_url'],'/v1/state/'+parts[5],h.command,b,n['state_admin_key'],service=True)
        elif parts[1:3]==['api','assets'] and len(parts)>=4:
            engine=parts[3];require(u,'read',engine)
            action='/'+('/'.join(parts[4:]) or 'current')
            if h.command=='GET':
                if action=='/candidates':
                    if 'evaluate' not in u['extra']:
                        require(u,'candidate',engine)
                elif action not in ['/current','/history'] and not (len(parts)==6 and parts[4]=='releases'):
                    raise Fault(404,'not_found')
                result=self.assets.call(engine,action)
                if action=='/candidates' and 'evaluate' not in u['extra']:
                    result=[r for r in result if r['author']==u['id']]
            else:
                b=h.body()
                if action=='/candidates':
                    require(u,'candidate',engine)
                    b['author']=u['id']
                    source=b.get('source',{})
                    source_run=self.run(u,source.get('run',''))
                    if source_run['owner']!=u['id'] or source_run['engine']!=engine or source_run['status']!='completed':
                        raise Fault(403,'source_scope_mismatch')
                    b['source']={'run':source_run['id'],'owner':u['id'],'engine':engine,
                        'node':source_run['node'],'conversation':source_run['conversation'],'report_sha256':source_run['report_sha256']}
                    n=next(n for n in self.cfg['nodes'] if n['id']==source_run['node'])
                    if self.cfg.get('owned_local_lab'):
                        self.manager.call('/nodes/'+n['id']+'/state-ready','POST',{})
                    raw=self.manager.query(source_run['id'])
                    draft=request(n['state_url'],'/v1/drafts','POST',{'owner':u['id'],
                        'conversation':source_run['conversation'],'context':raw['context_id'],
                        'content':b.get('knowledge','')},n['state_admin_key'],service=True)
                    b['source']['private_draft']={'id':draft['id'],'sha256':draft['sha256'],'node':n['id']}
                elif action.endswith('/evaluate'):
                    require(u,'evaluate',engine);b['reviewer']=u['id']
                elif action.endswith('/approve') or action.endswith('/withdraw') or action=='/rollback':
                    require(u,'publish',engine);b['reviewer']=u['id']
                else:
                    raise Fault(404,'not_found')
                result=self.assets.call(engine,action,'POST',b)
                self.store.audit({'action':'asset_write','path':action,'engine':engine,'user':u['id']})
        elif path=='/api/users':
            require(u,'users')
            if h.command=='GET':
                result=[self.identity.public(x) for x in self.store.all('users') if set(x['engines'])<=set(u['engines'])]
            elif h.command=='POST':
                b=h.body()
                if not set(b.get('engines',[]))<=set(u['engines']) or self.store.get('users',b.get('name','')):
                    raise Fault(409,'user_scope_or_conflict')
                if not b.get('name','').isalnum() or len(b.get('password',''))<12:
                    raise Fault(400,'invalid_user')
                spaces=b.get('spaces')
                if spaces is not None and (not isinstance(spaces,list) or not all(isinstance(x,str) for x in spaces)):
                    raise Fault(400,'invalid_spaces')
                if u.get('spaces') is not None and (spaces is None or not set(spaces)<=set(u['spaces'])):
                    raise Fault(403,'user_space_escalation')
                self.identity.add(b['name'],b['password'],b['role'],b['engines'],spaces=spaces)
                self.store.audit({'action':'user_create','user':u['id'],'target':b['name']})
                result={'created':b['name']}
            else:
                raise Fault(405,'method_not_allowed')
        else:
            raise Fault(404,'not_found')
        h.reply(200,result)
