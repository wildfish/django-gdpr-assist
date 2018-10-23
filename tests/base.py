"""
Base classes for tests
"""
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase


class MigrationTestCase(TestCase):
    """
    Based on django.tests.migrations.test_+writer.WriterTests
    """
    def safe_exec(self, string, value=None):
        d = {}
        try:
            exec(string, globals(), d)
        except Exception as e:
            if value:
                self.fail("Could not exec %r (from value %r): %s" % (string.strip(), value, e))
            else:
                self.fail("Could not exec %r: %s" % (string.strip(), e))
        return d

    def serialize(self, value):
        """
        Test a value can be serialised by the MigrationWriter
        """
        string, imports = MigrationWriter.serialize(value)
        return string, imports

    def serialize_round_trip(self, value):
        """
        Test a value can be serialised and deserialised
        """
        string, imports = self.serialize(value)
        return self.safe_exec("%s\ntest_value_result = %s" % ("\n".join(imports), string), value)['test_value_result']
