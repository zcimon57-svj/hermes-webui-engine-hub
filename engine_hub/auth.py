import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie
from .common import Fault, digest

DEFAULTS = {
    'admin': {'read','chat','cancel_own','manage_runs','config','diagnostics','users','state'},
    'viewer': {'read'},
    'chat': {'read','chat','cancel_own'},
}


class Identity:
    def __init__(self, store):
        self.store = store

    def add(self, name, password, role, engines, extra=(),spaces=None):
        if role not in DEFAULTS or not engines:
            raise Fault(400, 'invalid_user')
        salt = secrets.token_hex(16)
        self.store.put('users', name, {'id':name, 'role':role, 'engines':engines,
            'extra':list(extra),'spaces':spaces, 'enabled':True, 'salt':salt,
            'password':hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000).hex()})

    def public(self, u):
        return {**{k:u[k] for k in ('id','role','engines','extra','enabled')},'spaces':u.get('spaces')}

    def login(self, name, password):
        u = self.store.get('users', name)
        salt = u['salt'] if u else 'missing'
        got = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000).hex()
        if not u or not u['enabled'] or not hmac.compare_digest(got, u['password']):
            raise Fault(401, 'invalid_login')
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self.store.put('auth', digest(token), {'user':name,'expires':time.time()+8*3600,'csrf':csrf})
        self.store.audit({'action':'login','user':name,'at':time.time()})
        return self.public(u), token, csrf

    def authenticate(self, handler):
        cookies = SimpleCookie()
        try:
            cookies.load(handler.headers.get('Cookie',''))
            token = cookies['hub_session'].value
        except (KeyError, ValueError):
            raise Fault(401, 'login_required') from None
        session = self.store.get('auth', digest(token))
        u = self.store.get('users', session['user']) if session else None
        if not session or session['expires'] <= time.time() or not u or not u['enabled']:
            raise Fault(401, 'session_expired')
        if handler.command != 'GET':
            if not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''), session['csrf']):
                raise Fault(403, 'csrf_required')
        return self.public(u), session


def require(user, capability, engine=None,space=None):
    if capability not in DEFAULTS[user['role']] | set(user['extra']):
        raise Fault(403, 'capability_denied')
    if engine and engine not in user['engines']:
        raise Fault(404, 'not_found')
    if space and user.get('spaces') is not None and space not in user['spaces']:
        raise Fault(404,'not_found')


def visible(user, row):
    return row['engine'] in user['engines'] and (user.get('spaces') is None or row.get('space') in user['spaces']) and (
        row['owner'] == user['id'] or user['id'] in row.get('shared_with', []))


def owned(user, row):
    if not row or not visible(user, row):
        raise Fault(404, 'not_found')
