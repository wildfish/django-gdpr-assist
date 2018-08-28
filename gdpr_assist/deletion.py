"""
Fields and field utils for gdpr-assist
"""
from django.db.models import CASCADE, PROTECT


class ANONYMISE(object):
    def __init__(self, action):
        if action in [CASCADE, PROTECT]:
            raise ValueError('Cannot ANONYMISE({})'.format(action.__name__))
        self.action = action

    def __call__(self, collector, field, sub_objs, using):
        self.action(collector, field, sub_objs, using)

    def deconstruct(self):
        return ('gdpr_assist.ANONYMISE', (self.action,), {})
