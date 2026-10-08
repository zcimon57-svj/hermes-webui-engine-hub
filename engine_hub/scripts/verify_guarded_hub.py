"""Recheck the final runtime in cold-node batches under the hard 1 GiB envelope."""
import datetime
import json
import pathlib
import secrets
import subprocess
import time
from engine_hub.scripts import verify_live as v
from engine_hub.resources import host_snapshot,require_containment
from engine_hub.common import Fault,request,digest
from engine_hub.manager import ManagerClient


def main():
    require_containment()
    root=v.ROOT;cfg=json.loads((root/'.local/config.json').read_text());s=json.loads((root/'.local/secrets.json').read_text())
    admin=v.Client('admin',s['passwords']['admin']);viewer=v.Client('viewer',s['passwords']['viewer']);chat=v.Client('chat',s['passwords']['chat'])
    restricted=v.Client('restricted',s['passwords']['restricted'])
    v.check('viewer_no_direct_writes',viewer.denied('/ask','POST',{'text':'pg'},403)['error']=='viewer_read_only')
    chat.denied('/config',status=403);chat.denied('/diagnostics',status=403)
    v.check('restricted_summary_no_unreadable_nodes',{n['engine'] for n in restricted.ok('/summary')['nodes']}=={'pg'})
    results=[]
    for engine in ['mysql','pg','cassandra','cassandra','redis','redis']:
        asked=admin.ok('/ask','POST',{'engine':engine,'text':engine+' guarded cold-worker consumption probe'})
        r=v.terminal(admin,asked['run']['id']);identity=v.identity(r['report'])
        v.check('guarded_route_'+r['node'],identity['node']==r['node'] and identity['engine']==engine and identity['release']==r['knowledge_release'])
        v.check('approved_script_consumed_'+r['node'],bool(identity['script_output']) and identity['other_node_paths_denied'])
        n=next(n for n in cfg['nodes'] if n['id']==r['node'])
        try:
            request(n['state_url'],'/v1/state/memory','PUT',{'content':'forbidden'},n['consume_key'],service=True)
            raise AssertionError('Consumer mutated state')
        except Fault as e:v.check('consumer_write_denied_'+r['node'],e.status==403)
        try:
            request(n['state_url'],'/v1/state/memory',token=n['key'],service=True)
            raise AssertionError('Gateway key granted state admin')
        except Fault as e:v.check('gateway_key_is_not_state_admin_'+r['node'],e.status==401)
        snapshot=host_snapshot();v.check('aggregate_budget_'+r['node'],snapshot['owned_bytes']<896*1024**2 and snapshot['owned_tasks']<184,snapshot)
        results.append(r)
    v.check('six_identities_after_guard',{r['node'] for r in results}=={'node-01','node-02','node-03','node-04','node-05','node-06'})
    original=results[-1]
    second=admin.ok('/ask','POST',{'conversation':original['conversation'],'text':'followup guarded continuity'})
    second=v.terminal(admin,second['run']['id'])
    v.check('followup_new_run_same_pinned_node',second['conversation']==original['conversation'] and second['node']==original['node'] and second['gateway_run']!=original['gateway_run'])
    # Atomic idempotency checks through the Manager protocol against a completed row.
    manager=ManagerClient(cfg);raw=manager.query(second['id'])
    v.check('report_receipt_hash',manager.report(second['id'])['sha256']==digest(second['report']) and manager.delivery(second['id'])['external_delivery']=='NOT_RUN')
    admin.ok('/conversations/'+original['conversation']+'/share','POST',{'users':['viewer','chat']})
    viewer.ok('/runs/'+original['id']+'/events');viewer.ok('/runs/'+original['id']+'/download')
    chat.denied('/runs/'+original['id']+'/cancel','POST',{},403)
    cancelled=chat.ok('/ask','POST',{'engine':'redis','text':'redis controlled cancellation FIXTURE_DELAY=8'})
    chat.ok('/runs/'+cancelled['run']['id']+'/cancel','POST',{})
    cancelled=v.terminal(chat,cancelled['run']['id'])
    v.check('guarded_actual_cancel',cancelled['status']=='cancelled')
    # Restart the light UI only; no full lab restart, no reset or new worker.
    subprocess.run(['python3','-m','engine_hub.scripts.lab','restart-ui'],cwd=root.parent,check=True,stdout=subprocess.DEVNULL)
    for _ in range(20):
        try:
            if admin.ok('/me')['user']['id']=='admin':break
        except Exception:time.sleep(.2)
    v.check('guarded_restart_records',admin.ok('/runs/'+second['id'])['report_sha256']==second['report_sha256'])
    (root/'.local/guarded-runs.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('guarded-hub-%Y%m%dT%H%M%S.json')
    status='PASS';error=None
    try:main()
    except Exception as e:status='FAIL';error=str(e);raise
    finally:
        (v.ROOT/'evidence'/stamp).write_text(json.dumps({'status':status,'error':error,'checks':v.CHECKS,'trace':v.TRACE,
            'boundary':'Final code, actual Gateway/MCP/remote WeKnora, one warm node at a time; fixture model. Simultaneous six-node claims are not inferred.'},indent=2)+'\n')
        print(json.dumps({'status':status,'checks':len(v.CHECKS),'evidence':stamp,'error':error}))
