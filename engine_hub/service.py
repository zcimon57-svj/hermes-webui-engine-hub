import argparse
import json
import pathlib
from .common import BoundedServer,Handler,Store
from .assets import ReleaseAuthority
from .manager import ReferenceManager
from .companion import Companion


def main():
    from .resources import require_containment
    require_containment()
    p=argparse.ArgumentParser()
    p.add_argument('kind',choices=['assets','manager','companion','ui'])
    p.add_argument('--config',required=True)
    p.add_argument('--state',required=True)
    p.add_argument('--port',required=True,type=int)
    a=p.parse_args()
    cfg=json.loads(pathlib.Path(a.config).read_text())
    store=Store(a.state)
    if a.kind=='assets':
        app=ReleaseAuthority(store,cfg)
    elif a.kind=='manager':
        app=ReferenceManager(store,cfg)
    elif a.kind=='companion':
        app=Companion(cfg,cfg['node'],'/state','/workspace',store)
    else:
        from .server import Hub
        app=Hub(store,cfg)
    BoundedServer(('127.0.0.1',a.port),Handler,app).serve_forever()


if __name__=='__main__':
    main()
