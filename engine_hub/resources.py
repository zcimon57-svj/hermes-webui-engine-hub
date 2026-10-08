"""One hard resource envelope for the owned lab, plus host admission and trips.

No global WSL/Windows settings, cache dropping or unrelated services are changed.
Missing measurements or containment refuse new work.
"""
import fcntl
import json
import os
import pathlib
import subprocess
import time
from .common import Fault

ROOT=pathlib.Path(__file__).parent
LOCAL=ROOT/'.local'
SLICE='eh158.slice'
MAX_BYTES=1024**3
HIGH_BYTES=896*1024**2
MAX_TASKS=192
RESERVE_LINUX=2*1024**3
RESERVE_WINDOWS=512*1024**2
CGROUP=pathlib.Path('/sys/fs/cgroup')
CPU=min(os.sched_getaffinity(0))


def command(args,timeout=8):
    return subprocess.check_output(args,text=True,stderr=subprocess.PIPE,timeout=timeout).strip()


def boot_id():
    return pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def slice_path():
    own=pathlib.Path('/proc/self/cgroup').read_text().split('::',1)[-1].strip()
    if '/'+SLICE+'/' in own:
        relative=own.split('/'+SLICE+'/',1)[0]+'/'+SLICE
        bound=CGROUP/relative.lstrip('/')
        if bound.exists():return bound
    value=command(['systemctl','--user','show',SLICE,'--property=ControlGroup','--value'])
    if not value.endswith('/'+SLICE):
        raise Fault(503,'resource_slice_missing')
    return CGROUP/value.lstrip('/')


def ensure_slice():
    try:
        p=slice_path()
    except (Fault,subprocess.SubprocessError):
        command(['busctl','--user','call','org.freedesktop.systemd1','/org/freedesktop/systemd1',
            'org.freedesktop.systemd1.Manager','StartTransientUnit','ssa(sv)a(sa(sv))',SLICE,'fail','7',
            'MemoryMax','t',str(MAX_BYTES),'MemoryHigh','t',str(HIGH_BYTES),
            'MemorySwapMax','t','0','CPUQuotaPerSecUSec','t','1000000','TasksMax','t',str(MAX_TASKS),
            'MemoryAccounting','b','true','CPUAccounting','b','true','0'])
        p=slice_path()
    # Read actual kernel values; accepted systemd properties alone are insufficient.
    values={f:(p/f).read_text().strip() for f in ['memory.max','memory.high','memory.swap.max','pids.max']}
    if (p/'cpu.max').exists():
        values['cpu.max']=(p/'cpu.max').read_text().strip()
        quota,period=values['cpu.max'].split()
        if quota=='max' or int(quota)>int(period):raise Fault(503,'resource_cpu_limit_drift')
        values['cpu_enforcement']='cgroup_quota_and_single_core_affinity'
    else:
        # This WSL user manager delegates only memory/pids. Never claim its
        # accepted CPUQuota property means an effective kernel quota.
        values['cpu_enforcement']='single_core_sched_affinity; cpu controller unavailable'
    if (values['memory.max']!=str(MAX_BYTES) or values['memory.high']!=str(HIGH_BYTES)
        or values['memory.swap.max']!='0' or values['pids.max']!=str(MAX_TASKS)):
        raise Fault(503,'resource_limit_drift')
    return p,values


def host_snapshot():
    mem={}
    for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1)
        if key in ['MemAvailable','MemTotal','SwapTotal','SwapFree']:
            mem[key]=int(value.split()[0])*1024
    cpu=pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:]
    snapshot={'at':time.time(),'boot_id':boot_id(),'linux_available':mem['MemAvailable'],
        'linux_total':mem['MemTotal'],'swap_used':mem['SwapTotal']-mem['SwapFree'],
        'cpu_ticks':list(map(int,cpu)), 'memory_psi':pathlib.Path('/proc/pressure/memory').read_text(),
        'windows_required':'microsoft' in pathlib.Path('/proc/sys/kernel/osrelease').read_text().lower()}
    if snapshot['windows_required']:
        exe='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
        script="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); $o=Get-CimInstance Win32_OperatingSystem; @{available=[long]$o.FreePhysicalMemory*1024;total=[long]$o.TotalVisibleMemorySize*1024}|ConvertTo-Json -Compress"
        try:
            result=subprocess.run([exe,'-NoProfile','-NonInteractive','-Command',script],capture_output=True,timeout=8)
            data=json.loads(result.stdout.decode('utf-8'))
            if result.returncode or not isinstance(data.get('available'),int):
                raise ValueError()
            snapshot['windows_available']=data['available']
            snapshot['windows_total']=data['total']
        except (OSError,ValueError,subprocess.SubprocessError):
            snapshot['windows_available']=None
    try:
        p=slice_path()
        snapshot['owned_bytes']=int((p/'memory.current').read_text())
        snapshot['owned_tasks']=int((p/'pids.current').read_text())
        snapshot['memory_events']=(p/'memory.events').read_text()
    except (Fault,OSError,ValueError,subprocess.SubprocessError):
        snapshot['owned_bytes']=0
        snapshot['owned_tasks']=0
    return snapshot


def admission_errors(snapshot,reservation):
    errors=[]
    if snapshot.get('linux_available',0)<RESERVE_LINUX+reservation:
        errors.append('linux_headroom')
    if snapshot.get('windows_required'):
        free=snapshot.get('windows_available')
        if free is None:
            errors.append('windows_measurement_missing')
        elif free<RESERVE_WINDOWS+reservation:
            errors.append('windows_headroom')
    if snapshot.get('swap_used',0)>256*1024**2:
        errors.append('swap_pressure')
    if snapshot.get('owned_bytes',0)+reservation>HIGH_BYTES:
        errors.append('owned_memory_budget')
    if snapshot.get('owned_tasks',0)>MAX_TASKS-24:
        errors.append('owned_task_budget')
    return errors


def check_admission(reservation=64*1024**2):
    ensure_slice()
    if (LOCAL/'resource-trip.json').exists():
        raise Fault(503,'resource_trip_requires_reconcile')
    snapshot=host_snapshot()
    errors=admission_errors(snapshot,reservation)
    for reclaim_attempt in range(4):
        if errors!=['owned_memory_budget']:break
        # Reclaim only this project's charged cache, never /proc drop_caches or
        # other cgroups. The hard total stays unchanged. EAGAIN remains a refusal.
        p=slice_path()
        stat={x.split()[0]:int(x.split()[1]) for x in (p/'memory.stat').read_text().splitlines()}
        if stat.get('file',0)>64*1024**2:
            try:
                (p/'memory.reclaim').write_text(str(min(128*1024**2,reservation)))
            except OSError:
                pass
            snapshot=host_snapshot();errors=admission_errors(snapshot,reservation)
            snapshot['owned_cache_reclaim_attempted']=True
        else:break
    LOCAL.mkdir(exist_ok=True,mode=0o700)
    with (LOCAL/'resource-samples.jsonl').open('a') as f:
        f.write(json.dumps({'type':'admission','reservation':reservation,'errors':errors,**snapshot})+'\n')
    if errors:
        raise Fault(503,'resource_admission_denied',reasons=errors)
    return snapshot


def contained():
    return '/'+SLICE+'/' in pathlib.Path('/proc/self/cgroup').read_text()


def require_containment():
    if not contained():
        raise Fault(503,'resource_scope_required')
    ensure_slice()
    if os.sched_getaffinity(0)!={CPU}:raise Fault(503,'resource_cpu_affinity_required')


def scope_command(name,args):
    return ['systemd-run','--user','--scope','--quiet','--unit='+name,'--slice='+SLICE,
        'taskset','--cpu-list',str(CPU),*map(str,args)]


def acquire_model_slot():
    """Cross-process singleton: classifier, bridge and standalone eval share it."""
    require_containment()
    check_admission(192*1024**2)
    path=LOCAL/'model-slot.lock'
    lock=path.open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise Fault(429,'global_model_budget') from None
    return lock


def trip_errors(snapshot):
    errors=[]
    if snapshot['linux_available']<RESERVE_LINUX:
        errors.append('linux_headroom')
    if snapshot.get('windows_required') and (snapshot.get('windows_available') is None or snapshot['windows_available']<RESERVE_WINDOWS):
        errors.append('windows_headroom_or_measurement')
    if snapshot.get('owned_bytes',0)>=HIGH_BYTES:
        errors.append('owned_memory_high')
    if snapshot.get('owned_tasks',0)>=MAX_TASKS-8:
        errors.append('owned_task_high')
    if snapshot.get('swap_used',0)>256*1024**2:
        errors.append('swap_pressure')
    return errors


def stop_envelope(reasons,snapshot):
    LOCAL.mkdir(exist_ok=True,mode=0o700)
    # Persist intent before stopping any external resource. A trip never auto-resumes.
    (LOCAL/'resource-trip.json').write_text(json.dumps({'at':time.time(),'boot_id':boot_id(),
        'reasons':reasons,'snapshot':snapshot,'policy':'NO_AUTOMATIC_RESTART'},indent=2)+'\n')
    try:
        # Only the dedicated, verified lab slice. No host/WSL/global user slice stop.
        ensure_slice()
        subprocess.run(['systemctl','--user','stop',SLICE],timeout=12,check=False,capture_output=True)
    except (Fault,subprocess.SubprocessError):
        pass


def watchdog():
    while True:
        snapshot=host_snapshot();errors=trip_errors(snapshot)
        try:
            path=slice_path()
            escaped=[]
            for file in path.rglob('cgroup.procs'):
                for id in file.read_text().split():
                    try:
                        for tid in pathlib.Path('/proc/'+id+'/task').iterdir():
                            if os.sched_getaffinity(int(tid.name))!={CPU}:escaped.append(int(tid.name))
                    except (FileNotFoundError,ProcessLookupError):pass
            if escaped:errors.append('cpu_affinity_escape')
            snapshot['cpu_affinity_escape_tasks']=escaped
        except (Fault,OSError,subprocess.SubprocessError):
            errors.append('containment_measurement_missing')
        with (LOCAL/'resource-samples.jsonl').open('a') as f:
            f.write(json.dumps({'type':'watchdog','errors':errors,**snapshot})+'\n')
        if errors:
            stop_envelope(errors,snapshot)
            return
        time.sleep(5)


if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['watchdog']:
        watchdog()
    elif sys.argv[1:] == ['reconcile']:
        check_snapshot=host_snapshot()
        errors=admission_errors(check_snapshot,128*1024**2)
        if errors:raise Fault(503,'resource_admission_denied',reasons=errors)
        trip=LOCAL/'resource-trip.json'
        if trip.exists():
            dest=LOCAL/('resource-trip-reconciled-'+str(time.time_ns())+'.json')
            trip.rename(dest)
        print(json.dumps({'reconciled':True,'snapshot':check_snapshot}))
    else:
        print(json.dumps(host_snapshot(),indent=2))
