import re
from .common import Fault

VERSION = 'rules-2'
ENGINES = ('mysql','pg','cassandra','redis')
PATTERNS = {'mysql':r'\bmysql\b|innodb', 'pg':r'\bpg\b|postgres(?:ql)?|vacuum',
    'cassandra':r'cassandra|sstable|compaction', 'redis':r'\bredis\b|rdb|aof'}


class RuleClassifier:
    """Classifier contract: suggest only already-authorized candidates. No quality claim."""
    def classify(self, text, allowed):
        matches = [e for e in allowed if re.search(PATTERNS[e], text, re.I)]
        if re.search(r'忽略.*规则|ignore.*rules|请选择.*(?:mysql|pg|cassandra|redis)|默认.*(?:节点|引擎)|(?:节点|引擎).*默认',text,re.I):
            matches=[]
        return {'candidates':matches or list(allowed), 'selected':matches[0] if len(matches)==1 else None,
            'reason':'explicit_engine_terms' if len(matches)==1 else 'clarification_required',
            'version':VERSION, 'quality':'RULES_ONLY_REAL_SEMANTIC_NOT_RUN'}


class Router:
    def __init__(self, instances, classifier=None):
        self.instances = instances
        self.classifier = classifier or RuleClassifier()

    def select(self, user, body, conversation=None):
        if set(body) & {'url','api_key','kb_id','profile','node_id','gateway','knowledge_base_ids'}:
            raise Fault(400, 'untrusted_route_fields')
        requested = body.get('engine')
        if requested and requested not in user['engines']:
            raise Fault(404, 'not_found')
        if conversation and (not requested or requested == conversation['engine']):
            return {'engine':conversation['engine'],'space':conversation['space'],
                'reason':'conversation_binding','version':VERSION,'candidates':[conversation['engine']]}
        instance = body.get('instance')
        if instance:
            binding = self.instances.get(instance)
            if not binding or binding['engine'] not in user['engines']:
                raise Fault(404, 'not_found')
            if requested and requested != binding['engine']:
                raise Fault(409, 'instance_engine_conflict')
            return {**binding,'reason':'registered_instance','version':VERSION,'candidates':[binding['engine']]}
        if requested:
            return {'engine':requested,'space':requested+'-ops','reason':'explicit_authorized_engine',
                'version':VERSION,'candidates':[requested]}
        result = self.classifier.classify(body.get('text',''), tuple(user['engines']))
        if not result['selected']:
            raise Fault(409, 'clarification_required', routing=result)
        e = result['selected']
        if e not in user['engines']:
            raise Fault(403, 'classifier_scope_rejected')
        return {**result,'engine':e,'space':e+'-ops'}
