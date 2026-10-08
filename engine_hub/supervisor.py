"""Reference Manager's owned, bounded worker activation; never runs on UI reads."""
import time
from urllib.parse import urlsplit
from .common import Fault,request


class WorkerSupervisor:
    def __init__(self,cfg,store):
        self.cfg,self.store=cfg,store

    def ensure_state(self,node):
        if not self.cfg.get('owned_local_lab'):return
        from .scripts.lab import registry,live,stop,initialize,start_state
        state=registry().get(node['id']+'-state')
        if not state or not live(state):
            for n in self.cfg['nodes']:
                if n['id']==node['id']:continue
                r=registry().get(n['id']+'-state');gw=registry().get(n['id'])
                if r and live(r) and not (gw and live(gw)):stop(n['id']+'-state')
            initialize();start_state(node)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            try:
                r=request(node['state_url'],'/v1/identity',token=node['state_admin_key'])
                if r['node']==node['id'] and r['engine']==node['engine']:return
            except Fault:time.sleep(.2)
        raise Fault(503,'state_service_not_ready')

    def ensure(self,node):
        if not self.cfg.get('owned_local_lab'):
            return  # Remote/internal deployment is externally managed.
        from .scripts.lab import registry,live,stop,initialize,start_node
        record=registry().get(node['id'])
        if record and live(record):
            return self.ready(node)
        if urlsplit(node['url']).hostname not in ['127.0.0.1','localhost']:
            return
        active=self.store.all('runs')
        terminal={'completed','failed','cancelled','expired','interrupted'}
        # Keep one Gateway warm on this constrained host. No active or uncertain
        # run is evicted/migrated to create capacity for another engine.
        for n in self.cfg['nodes']:
            r=registry().get(n['id'])
            if r and live(r):
                if any(x['node']==n['id'] and x['status'] not in terminal for x in active):
                    raise Fault(503,'worker_capacity_busy')
                stop(n['id']);stop(n['id']+'-state')
        try:
            initialize();start_node(node)
        except (RuntimeError,Fault) as e:
            self.store.audit({'action':'worker_start_refused','node':node['id'],'reason':str(e)})
            raise Fault(503,'worker_resource_or_identity_refused') from None
        self.store.audit({'action':'worker_warm','node':node['id'],'engine':node['engine']})
        return self.ready(node)

    def ready(self,node):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            try:
                identity=request(node['state_url'],'/v1/identity',token=node['state_admin_key'],timeout=2)
                request(node['url'],'/health',token=node['key'],timeout=2)
                if identity['node']==node['id'] and identity['engine']==node['engine']:
                    return
                raise Fault(503,'worker_identity_mismatch')
            except Fault:
                time.sleep(.3)
        raise Fault(503,'worker_start_not_ready')
