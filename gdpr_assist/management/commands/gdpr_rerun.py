"""
Re-run a GDPR operations log
"""
from django.core.management import BaseCommand

from ...models import EventLog


class Command(BaseCommand):
    help = 'Re-runs a GDPR operations log'

    def handle(self, *args, **options):
        for log in EventLog.objects.all():
            target = log.get_target()
            if not target:
                continue

            if log.event == EventLog.EVENT_DELETE:
                target.delete()

            elif log.event == EventLog.EVENT_ANONYMISE:
                # Make sure we re-anonymise in case fields have been changed in
                # a migration since the last anonymisation
                target.anonymise(force=True)

            else:  # pragma: no cover
                raise ValueError('Unexpected event type')
