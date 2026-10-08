import hashlib
import contextlib
import json
import pathlib
import socket
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Fault(Exception):
    def __init__(self, status, code, **details):
        self.status, self.code, self.details = status, code, details
        super().__init__(code)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def request(base, path, method='GET', data=None, token=None, headers=None, timeout=8, service=False):
    """Fixed server-owned target; no redirects, system proxies or credential fallbacks."""
    h = {'Content-Type': 'application/json', **(headers or {})}
    if token:
        h['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(base.rstrip('/') + path,
        data=None if data is None else canonical(data).encode(), headers=h, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise Fault(502, 'upstream_response_too_large')
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        if service:
            try:
                import re
                error=json.loads(e.read(8192)).get('error','')
                if re.fullmatch(r'[a-z_]{1,80}',error):
                    raise Fault(e.code,error) from None
            except (ValueError,TypeError,AttributeError):
                pass
        # Never reflect raw upstream bodies: they may include credentials/paths.
        raise Fault(502, 'upstream_http', upstream_status=e.code) from None
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError):
        raise Fault(503, 'target_unavailable') from None


class Store:
    def __init__(self, path):
        self.path = str(path)
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            # Some locked Hermes interpreters use SQLite 3.50.4. Avoid its
            # WAL-reset bug rather than changing a shared interpreter installation.
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)')

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA busy_timeout=10000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, kind, id, db=None):
        if db is None:
            with self.connect() as conn:
                return self.get(kind, id, conn)
        row = db.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, id)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, kind, id, value, db=None):
        if db is None:
            with self.connect() as conn:
                return self.put(kind, id, value, conn)
        db.execute('INSERT INTO records VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',
            (kind, id, canonical(value)))

    def all(self, kind):
        with self.connect() as db:
            return [json.loads(x[0]) for x in db.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid', (kind,))]

    def audit(self, value):
        with self.connect() as db:
            db.execute('INSERT INTO audit(data) VALUES(?)', (canonical(value),))


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32
    def __init__(self, address, handler, app, max_connections=24):
        self.app = app
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            try:
                request.sendall(b'HTTP/1.0 503 Busy\r\nContent-Length: 0\r\n\r\n')
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            request.settimeout(20)
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Authentication payloads and URLs do not belong in logs.

    def reply(self, status, data, headers=None):
        raw = canonical(data).encode()
        self.send_response(status)
        for k, v in {'Content-Type':'application/json; charset=utf-8', 'Cache-Control':'no-store',
            'X-Content-Type-Options':'nosniff', **(headers or {})}.items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 1024 * 1024:
                raise Fault(413, 'body_too_large')
            value = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, json.JSONDecodeError):
            raise Fault(400, 'invalid_json') from None

    def dispatch(self):
        try:
            self.server.app.handle(self)
        except Fault as e:
            self.reply(e.status, {'error':e.code, **e.details})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print('Unhandled:', type(e).__name__, flush=True)
            self.reply(500, {'error':'internal_error'})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = dispatch
