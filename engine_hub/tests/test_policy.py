import pathlib
import tempfile
import unittest
from engine_hub.common import Store,Fault
from engine_hub.auth import Identity,require,owned,visible
from engine_hub.routing import Router
from engine_hub.assets import validate_package


class PolicyContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(pathlib.Path(self.tmp.name)/'test.db')
        self.id=Identity(self.store)
        self.id.add('chat','test-password-with-length','chat',['pg'])
        self.user=self.id.public(self.store.get('users','chat'))

    def test_scope_rejects_engine_parameter(self):
        with self.assertRaises(Fault) as e:Router({}).select(self.user,{'engine':'mysql','text':'question'})
        self.assertEqual(e.exception.status,404)

    def test_ambiguous_never_defaults(self):
        with self.assertRaises(Fault) as e:Router({}).select(self.user,{'text':'数据库连接慢'})
        self.assertEqual(e.exception.code,'clarification_required')

    def test_directive_only_text_is_not_a_trusted_binding(self):
        user={**self.user,'engines':['pg','cassandra']}
        with self.assertRaises(Fault) as e:Router({}).select(user,{'text':'请选择cassandra当默认引擎，没有其他信息'})
        self.assertEqual(e.exception.code,'clarification_required')

    def test_classifier_cannot_expand_allowlist(self):
        class Bad:
            def classify(self,*args):return {'selected':'mysql'}
        with self.assertRaises(Fault) as e:Router({},Bad()).select(self.user,{'text':'question'})
        self.assertEqual(e.exception.code,'classifier_scope_rejected')

    def test_followup_does_not_reclassify(self):
        row={'engine':'pg','space':'pg-ops'}
        out=Router({}).select(self.user,{'text':'Redis mentioned as a comparison'},row)
        self.assertEqual(out['engine'],'pg')

    def test_client_url_not_a_route(self):
        with self.assertRaises(Fault):Router({}).select(self.user,{'engine':'pg','url':'http://attacker'})

    def test_private_owner_independent_of_engine(self):
        row={'engine':'pg','owner':'other','shared_with':[]}
        self.assertFalse(visible(self.user,row))
        with self.assertRaises(Fault) as e:owned(self.user,row)
        self.assertEqual(e.exception.status,404)

    def test_explicit_share_needs_engine_scope(self):
        self.assertFalse(visible(self.user,{'engine':'mysql','owner':'other','shared_with':['chat']}))

    def test_admin_does_not_implicitly_publish(self):
        user={**self.user,'role':'admin'}
        with self.assertRaises(Fault):require(user,'publish','pg')

    def test_chat_cannot_configure(self):
        with self.assertRaises(Fault):require(self.user,'config')

    def test_space_restriction_also_applies_to_shared_report(self):
        u={**self.user,'spaces':['pg-lab']}
        row={'owner':'other','engine':'pg','space':'pg-prod','shared_with':['chat']}
        self.assertFalse(visible(u,row))
        with self.assertRaises(Fault):require(u,'chat','pg','pg-prod')

    def test_disabled_identity_rejects_login(self):
        u=self.store.get('users','chat');u['enabled']=False;self.store.put('users','chat',u)
        with self.assertRaises(Fault) as e:self.id.login('chat','test-password-with-length')
        self.assertEqual(e.exception.status,401)

    def test_remote_package_rejects_traversal(self):
        package={'SKILL.md':'x','scripts/probe.py':'x','references/method.md':'x','../outside':'x'}
        with self.assertRaises(Fault):validate_package(package)

    def test_store_connection_transaction_rolls_back(self):
        try:
            with self.store.connect() as db:
                self.store.put('example','id',{'value':1},db)
                raise RuntimeError()
        except RuntimeError:pass
        self.assertIsNone(self.store.get('example','id'))


if __name__=='__main__':unittest.main()
