"""
Anonymise all personal data in the database
"""
from django.core.management import BaseCommand

from ... import app_settings
from ...registry import registry


class Command(BaseCommand):
    help = "Anonymises all personal data in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            default=True,
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

        parser.add_argument(
            "--bulk",
            action="store_true",
            dest="bulk",
            default=True,
            help="Anonymise in bulk, default is per object.",
        )

    def handle(self, *args, **options):
        if not app_settings.GDPR_CAN_ANONYMISE_DATABASE:
            raise ValueError("Database anonymisation is not enabled")
        interactive = options["interactive"]
        bulk = options["bulk"]

        if interactive:  # pragma: no cover
            confirm = input(
                """Warning!
You have requested that all personal information in the database is anonymised.
This will IRREVERSIBLY OVERWRITE all personal data currently in the database.
Are you sure you want to do this?

    Type 'yes' to continue, or 'no' to cancel: """
            )

        else:
            confirm = "yes"
        if confirm == "yes":
            for model in registry.models_allowed_to_anonymise():
                if bulk:
                    model.anonymisable_manager().all().anonymise()
                else:
                    for obj in model.objects.all().iterator():
                        obj.anonymise()

            msg = "{} models anonymised.".format(
                len(registry.models_allowed_to_anonymise())
            )
            self.stdout.write(msg)

        else:  # pragma: no cover
            self.stdout.write("Anonymisation cancelled.")
