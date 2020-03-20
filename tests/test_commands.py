"""
Test management commands
"""
import six
import sys
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .gdpr_assist_tests_app.models import ModelWithPrivacyMeta


# If True, display output from call_command - use for debugging tests
DISPLAY_CALL_COMMAND = False


class Capturing(list):
    "Capture stdout and stderr to a string"
    # Based on http://stackoverflow.com/questions/16571150/how-to-capture-stdout-output-from-a-python-function-call
    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = sys.stderr = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        # Ensure output is unicode
        self.extend(
            six.text_type(line)
            for line in self._stringio.getvalue().splitlines()
        )
        sys.stdout = self._stdout
        sys.stderr = self._stderr


class CommandTestCase(TestCase):
    def run_command(self, command, *args, **kwargs):
        # Silent
        kwargs['verbosity'] = 1

        with Capturing() as output:
            call_command(
                command,
                *args,
                **kwargs
            )

        if DISPLAY_CALL_COMMAND:
            print('>> {} {} {}'.format(
                command,
                ' '.join(args),
                ' '.join([
                    '{}={}'.format(key, val)
                    for key, val in kwargs.items()
                ]),
            ))
            print('\n'.join(output))
            print('<<')

        return output


class TestAnonymiseCommand(CommandTestCase):
    def test_anonymise_command__anonymises_data(self):
        obj_1 = ModelWithPrivacyMeta.objects.create(
            chars='test',
            email='test@example.com',
            anonymised=False,
        )
        self.assertFalse(obj_1.anonymised)
        self.run_command('anonymise_db', interactive=False)

        obj_1.refresh_from_db()
        self.assertTrue(obj_1.anonymised)
        self.assertEqual(obj_1.chars, six.text_type(obj_1.pk))
        self.assertEqual(obj_1.email, '{}@anon.example.com'.format(obj_1.pk))

    def test_anonymise_disabled__raises_error(self):

        with self.assertRaises(ValueError) as cm:
            with self.settings(GDPR_CAN_ANONYMISE_DATABASE=False):
                self.run_command('anonymise_db', interactive=False)

        self.assertEqual(
            'Database anonymisation is not enabled',
            str(cm.exception),
        )


class TestRerunCommand(CommandTestCase):
    def test_gdpr_delete__deletes_object(self):
        obj_1 = ModelWithPrivacyMeta.objects.create(
            chars='test',
            email='test@example.com',
        )

        # Log deletion without deleting to simulate deletion and db restore
        obj_1._log_gdpr_delete()

        self.run_command('gdpr_rerun')

        self.assertEqual(ModelWithPrivacyMeta.objects.count(), 0)

    def test_gdpr_anonymise__anonymises_object(self):
        obj_1 = ModelWithPrivacyMeta.objects.create(
            chars='test',
            email='test@example.com',
            anonymised=False,
        )

        # Log anonymise without anonymising to simulate deletion and db restore
        obj_1._log_gdpr_anonymise()

        self.run_command('gdpr_rerun')

        self.assertEqual(ModelWithPrivacyMeta.objects.count(), 1)
        obj_1.refresh_from_db()
        self.assertTrue(obj_1.anonymised)
        self.assertEqual(obj_1.chars, six.text_type(obj_1.pk))
        self.assertEqual(obj_1.email, '{}@anon.example.com'.format(obj_1.pk))
