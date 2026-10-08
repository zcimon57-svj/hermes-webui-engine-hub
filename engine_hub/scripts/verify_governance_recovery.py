import concurrent.futures
import datetime
import json
import pathlib
import secrets
import subprocess
import time
from engine_hub.scripts import verify_live as v
from engine_hub.common import canonical,digest,request,Fault,Store
from engine_hub.assets import ReleaseClient
from engine_hub.manager import ManagerClient
from engine_hub.scripts.lab import stop,start,registry,live,LOCAL,PY,ROOT


def main():
    cfg=json.loads((v.ROOT/'.local/config.json').read_text())
    s=json.loads((v.ROOT/'.local/secrets.json').read_text())
    admin=v.Client('admin',s['passwords']['admin']);reviewer=v.Client('reviewer',s['passwords']['reviewer']);chat=v.Client('chat',s['passwords']['chat'])
    runs=json.loads((v.ROOT/'.local/verified-runs.json').read_text())
    source=next(r for r in reversed(runs) if r['engine']=='cassandra')
    base=admin.ok('/assets/cassandra/current')
    others={e:admin.ok('/assets/'+e+'/current')['id'] for e in ['mysql','pg','redis']}
    package={'SKILL.md':'---\nname: engine-ops\ndescription: Synthetic Cassandra updated method\n---\nSYNTHETIC CASSANDRA v2; verify pinned evidence.',
        'references/method.md':'Synthetic cassandra v2 method; no production diagnosis claim.',
        'scripts/probe.py':'from pathlib import Path\nprint("EXECUTED:cassandra:v2:"+Path("references/method.md").read_text())'}
    body={'source':{'run':source['id']},'knowledge':'SYNTHETIC cassandra knowledge v2 '+secrets.token_hex(6),
        'package':package,'share_consent':True,'base':base['id'],'origin':'MANUAL_SYNTHETIC'}
    # A pinned run starts before the publication changes.
    pinned=admin.ok('/ask','POST',{'engine':'cassandra','text':'cassandra pinned in-flight FIXTURE_DELAY=8'})
    candidates=[admin.ok('/assets/cassandra/candidates','POST',body) for _ in range(2)]
    v.check('node_case_private_draft_before_candidate',all(c['source'].get('private_draft') for c in candidates),[c['source'] for c in candidates])
    v.check('unpublished_pointer_unchanged',admin.ok('/assets/cassandra/current')['id']==base['id'])
    admin.denied('/assets/pg/candidates','POST',body,403)
    admin.denied('/assets/cassandra/candidates','POST',{**body,'share_consent':False},400)
    for c in candidates:
        reviewer.ok('/assets/cassandra/candidates/'+c['id']+'/evaluate','POST',{'passed':True,'evidence':['FUNCTIONAL_GOVERNANCE_ONLY']})
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        approvals=list(pool.map(lambda c:reviewer.api('/assets/cassandra/candidates/'+c['id']+'/approve','POST',{'base':base['id']}),candidates))
    v.check('concurrent_publish_one_winner',sorted(st for st,_ in approvals)==[200,409],approvals)
    winner=next(result for st,result in approvals if st==200)
    old=v.terminal(admin,pinned['run']['id'])
    v.check('inflight_pin_consumed_old_release',old['knowledge_release']==base['id'] and v.identity(old['report'])['release']==base['id'])
    adopted=[]
    for _ in range(2):
        result=admin.ok('/ask','POST',{'engine':'cassandra','text':'cassandra consume new approved version'})
        r=v.terminal(admin,result['run']['id']);actual=v.identity(r['report']);adopted.append(r)
        v.check('next_run_remote_updated_'+r['node'],actual['release']==winner['id'] and 'v2' in actual['script_output'] and actual['knowledge']['content']==body['knowledge'])
    v.check('both_cassandra_nodes_adopted',{r['node'] for r in adopted}=={'node-02','node-05'})
    v.check('other_engines_unchanged',all(admin.ok('/assets/'+e+'/current')['id']==id for e,id in others.items()))
    failed=admin.ok('/assets/cassandra/candidates','POST',{**body,'base':winner['id']})
    reviewer.ok('/assets/cassandra/candidates/'+failed['id']+'/evaluate','POST',{'passed':False,'evidence':['REPLAY_REJECTED']})
    reviewer.denied('/assets/cassandra/candidates/'+failed['id']+'/approve','POST',{'base':winner['id']},409)
    package_bad={**package,'../leak':'forbidden'}
    admin.denied('/assets/cassandra/candidates','POST',{**body,'base':winner['id'],'package':package_bad},400)
    frozen={r['id']:r['report_sha256'] for r in adopted}
    reviewer.ok('/assets/cassandra/releases/'+winner['id']+'/withdraw','POST',{'reason':'Synthetic withdrawal probe'})
    admin.denied('/assets/cassandra/releases/'+winner['id'],status=410)
    admin.denied('/ask','POST',{'engine':'cassandra','text':'cassandra revoked cache must not execute'},410)
    manager=ManagerClient(cfg);raw=manager.query(adopted[0]['id']);n=next(n for n in cfg['nodes'] if n['id']==raw['node'])
    try:
        request(n['state_url'],'/v1/contexts/'+raw['context_id']+'/consume',token=n['key'],service=True)
        raise AssertionError('Revoked snapshot executed')
    except Fault as e:
        v.check('revoked_existing_cache_ineligible',e.status==410)
    reviewer.ok('/assets/cassandra/rollback','POST',{'base':winner['id'],'target':base['id']})
    v.check('rollback_single_pointer',admin.ok('/assets/cassandra/current')['id']==base['id'])
    v.check('old_reports_immutable',all(admin.ok('/runs/'+id)['report_sha256']==sha for id,sha in frozen.items()))
    # Fixed owned Gateway loss, accurate health, same-engine alternative remains live.
    stop('node-04')
    try:
        summary=chat.ok('/summary')
        nodes={n['id']:n for n in summary['nodes']}
        v.check('offline_truth_not_substitute',not nodes['node-04']['online'] and nodes['node-06']['online'])
        result=chat.ok('/ask','POST',{'engine':'redis','text':'redis offline pool probe'})
        r=v.terminal(chat,result['run']['id']);v.check('offline_new_task_eligible_node',r['node']=='node-06' and v.identity(r['report'])['node']=='node-06')
    finally:
        subprocess.run(['python3','-m','engine_hub.scripts.lab','start-node','node-04'],cwd=v.ROOT.parent,check=True,stdout=subprocess.DEVNULL)
    # UI and Manager restart while Hermes owns a pending run.
    running=chat.ok('/ask','POST',{'engine':'pg','text':'pg restart continuity FIXTURE_DELAY=8'})
    before=manager.query(running['run']['id']);resources=registry();old_ui=resources['ui'];old_manager=resources['manager']
    stop('ui');stop('manager')
    subprocess.run(['python3','-m','engine_hub.scripts.lab','start'],cwd=v.ROOT.parent,check=True,stdout=subprocess.DEVNULL)
    for _ in range(30):
        try:
            chat.ok('/me');break
        except (AssertionError,ConnectionError,Exception):
            time.sleep(.3)
    restored=v.terminal(chat,running['run']['id']);after=manager.query(restored['id'])
    v.check('new_pid_same_durable_identity',registry()['ui']['pid']!=old_ui['pid'] and registry()['manager']['pid']!=old_manager['pid'])
    v.check('restart_kept_auth_and_run',chat.user['id']=='chat' and restored['status']=='completed' and after['gateway_run']==before['gateway_run'] and after['attempt']==before['attempt'])
    v.check('recovery_contract_no_duplicate',manager.recovery()['authority']=='LOCAL_REFERENCE_NOT_INTERNAL_MANAGER')
    v.check('restart_release_pointer_preserved',admin.ok('/assets/cassandra/current')['id']==base['id'])
    v.check('domain_quality_not_upgraded',winner['semantic_quality']=='NOT_RUN')


if __name__=='__main__':
    name=datetime.datetime.now(datetime.timezone.utc).strftime('governance-recovery-%Y%m%dT%H%M%S.json')
    status='PASS';error=None
    try:
        main()
    except Exception as e:
        status='FAIL';error=str(e);raise
    finally:
        (v.ROOT/'evidence'/name).write_text(json.dumps({'status':status,'error':error,'checks':v.CHECKS,'trace':v.TRACE,
            'boundary':'Actual owned Gateway/WeKnora/node-state and local reference Manager; synthetic knowledge/candidates; real learning quality NOT_RUN'},indent=2)+'\n')
        print(json.dumps({'status':status,'checks':len(v.CHECKS),'evidence':name,'error':error}))
