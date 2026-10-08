"""Create only new eh158-* containers/networks/volumes; never change adjacent labs."""
import json
import pathlib
import secrets
import subprocess
import time
from engine_hub.resources import check_admission,ensure_slice,SLICE,CPU

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
PREFIX = 'eh158'
CONTAINER_PREFIX = 'eh158r'
LIMITS={'embedding':'64m','postgres':'128m','redis':'32m','weknora':'320m'}

def fullname(name):
    return CONTAINER_PREFIX+'-'+name+('-r2' if name=='weknora' else '')


def run(*args):
    return subprocess.check_output(list(map(str, args)), text=True, stderr=subprocess.STDOUT).strip()


def envfile(name, values):
    p = LOCAL / (name + '.env')
    p.write_text(''.join(k+'='+str(v)+'\n' for k,v in values.items()))
    p.chmod(0o600)
    return ['--env-file', str(p)]


def container(name, image, options=(), command=()):
    full = fullname(name)
    existing = run('docker', 'ps', '-a', '--format', '{{.Names}}').splitlines()
    if full in existing:
        data = json.loads(run('docker','inspect',full))[0]
        if data['Config']['Labels'].get('engine-hub') != PREFIX:
            raise RuntimeError('Resource ownership conflict: '+full)
        if not data['State']['Running']:
            if data['HostConfig']['CgroupParent']!=SLICE:
                raise RuntimeError('Refuse uncontained existing resource: '+full)
            check_admission(128*1024**2 if name=='weknora' else 32*1024**2)
            run('docker','start',full)
        return
    old=PREFIX+'-'+name
    if old in existing and json.loads(run('docker','inspect',old))[0]['State']['Running']:
        raise RuntimeError('Prior uncontained lab container is running; do not share writable volumes')
    check_admission(192*1024**2 if name=='weknora' else 32*1024**2)
    helper=LOCAL/'affinity-launcher'
    if not helper.exists():raise RuntimeError('Compile the static affinity launcher before container startup')
    metadata=json.loads(run('docker','image','inspect',image))[0]['Config']
    entry=metadata.get('Entrypoint') or []
    payload=[*(entry or ['/usr/local/bin/python']),*(command or metadata.get('Cmd') or [])]
    if payload[0]=='docker-entrypoint.sh':payload[0]='/usr/local/bin/docker-entrypoint.sh'
    if not entry and command and command[0]=='python':payload=['/usr/local/bin/python',*command[1:]]
    run('docker','run','-d','--name',full,'--label','engine-hub='+PREFIX,
        '--network',PREFIX+'-net','--cgroup-parent',SLICE,'--memory',LIMITS[name],
        '--memory-swap',LIMITS[name],'--pids-limit','64','--entrypoint','/engine-hub-affinity',
        '-v',str(helper)+':/engine-hub-affinity:ro',*options,image,str(CPU),*payload)
    d=json.loads(run('docker','inspect',full))[0]
    pid=d['State']['Pid']
    if '/eh158.slice/' not in pathlib.Path('/proc/'+str(pid)+'/cgroup').read_text():
        run('docker','stop','--time','2',full)
        raise RuntimeError('Docker cgroup placement mismatch; owned container stopped')
    if __import__('os').sched_getaffinity(pid)!={CPU}:
        run('docker','stop','--time','2',full)
        raise RuntimeError('Docker CPU affinity mismatch; owned container stopped')


def main():
    check_admission(128*1024**2)
    from engine_hub.scripts.lab import ensure_watchdog
    ensure_watchdog()
    LOCAL.mkdir(exist_ok=True, mode=0o700)
    sp = LOCAL/'infra-secrets.json'
    if not sp.exists():
        sp.write_text(json.dumps({'db':secrets.token_hex(20),'jwt':secrets.token_hex(32),
            'aes':secrets.token_hex(16)}))
        sp.chmod(0o600)
    s = json.loads(sp.read_text())
    nets = run('docker','network','ls','--format','{{.Name}}').splitlines()
    if PREFIX+'-net' not in nets:
        run('docker','network','create','--label','engine-hub='+PREFIX,PREFIX+'-net')
    else:
        labels = json.loads(run('docker','network','inspect',PREFIX+'-net'))[0]['Labels']
        assert labels.get('engine-hub') == PREFIX
    for name in ('postgres','redis','weknora'):
        full = PREFIX+'-'+name+'-data'
        if full not in run('docker','volume','ls','--format','{{.Name}}').splitlines():
            run('docker','volume','create','--label','engine-hub='+PREFIX,full)
        else:
            assert json.loads(run('docker','volume','inspect',full))[0]['Labels'].get('engine-hub') == PREFIX
    container('embedding','python:3.11-slim', ['-v',str(ROOT/'scripts/embedding_fixture.py')+':/app/fixture.py:ro'], ['python','/app/fixture.py'])
    container('postgres','paradedb/paradedb:v0.22.2-pg17', ['-v',PREFIX+'-postgres-data:/var/lib/postgresql/data',
        *envfile('postgres',{'POSTGRES_USER':'enginehub','POSTGRES_PASSWORD':s['db'],'POSTGRES_DB':'weknora'})])
    container('redis','redis:7.0-alpine',['-v',PREFIX+'-redis-data:/data'])
    # This rootless Docker daemon has an unavailable embedded DNS listener.
    # Use addresses on this owned network; record and revalidate them at startup.
    def ip(name):
        d = json.loads(run('docker','inspect',fullname(name)))[0]
        return d['NetworkSettings']['Networks'][PREFIX+'-net']['IPAddress']
    for _ in range(30):
        p = subprocess.run(['docker','exec',CONTAINER_PREFIX+'-postgres','pg_isready','-U','enginehub'], capture_output=True)
        if p.returncode == 0:
            break
        time.sleep(1)
    container('weknora','weknora-ops-app:d97ad7a4', ['-p','127.0.0.1:15802:8080',
        '-v',PREFIX+'-weknora-data:/data', *envfile('weknora',{
        'DB_DRIVER':'postgres','DB_HOST':ip('postgres'),'DB_PORT':'5432','DB_USER':'enginehub',
        'DB_PASSWORD':s['db'],'DB_NAME':'weknora','REDIS_ADDR':ip('redis')+':6379','REDIS_PASSWORD':'',
        'RETRIEVE_DRIVER':'postgres','JWT_SECRET':s['jwt'],'SYSTEM_AES_KEY':s['aes'],
        'STORAGE_TYPE':'local','LOCAL_STORAGE_BASE_DIR':'/data/files','DISABLE_REGISTRATION':'false',
        'SSRF_WHITELIST_EXTRA':ip('embedding'),'GIN_MODE':'release','AUTO_MIGRATE':'true',
        'WEKNORA_SANDBOX_DOCKER_ENABLED':'false','WEKNORA_TENANT_ENABLE_CROSS_TENANT_ACCESS':'false',
        'DUCKDB_SKIP_EXTENSION_LOAD':'1','GOMAXPROCS':'1','CONCURRENCY_POOL_SIZE':'1'})])
    images = {}
    for name in ('embedding','postgres','redis','weknora'):
        d = json.loads(run('docker','inspect',fullname(name)))[0]
        images[name] = {'container':d['Name'], 'image_id':d['Image'], 'configured_image':d['Config']['Image'],
            'memory_limit':d['HostConfig']['Memory'], 'pids_limit':d['HostConfig']['PidsLimit']}
    (ROOT/'evidence'/('infra-guarded-'+str(time.time_ns())+'.json')).write_text(json.dumps(images,indent=2)+'\n')
    print('Owned isolated WeKnora dependencies started; no adjacent service changed.')


if __name__ == '__main__':
    main()
