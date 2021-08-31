"""
Anonymise all personal data in the database
"""
from django.apps import apps
from django.core.management import BaseCommand, CommandError

from ... import app_settings
from ...models import PrivacyModel
from ...registry import registry


class StrategyHelper:
    CATEGORY_ANONYMISABLE = "anonymisable"
    CATEGORY_UNANONYMISABLE = "unanonymisable"
    CATEGORY_UNTAGGED = "untagged"

    STRATEGY_ANONYMISE = "anonymise"
    STRATEGY_DELETE = "delete"
    STRATEGY_RETAIN = "retain"

    AVAILABLE_STRATEGIES = {
        STRATEGY_ANONYMISE,
        STRATEGY_DELETE,
        STRATEGY_RETAIN,
    }

    DEFAULT_STRATEGIES = {
        CATEGORY_ANONYMISABLE: "anonymise",
        CATEGORY_UNANONYMISABLE: "retain",
        CATEGORY_UNTAGGED: "retain",
    }

    @staticmethod
    def parse(text):
        strategies = {}
        for token in text.split(","):
            if not token:
                continue
            try:
                category, strategy = token.strip().split(":")
            except ValueError:
                raise CommandError("Could not parse strategy assignment: {}".format(token))
            if category not in StrategyHelper.DEFAULT_STRATEGIES:
                raise CommandError("Unknown data category: {}".format(category))
            if strategy not in StrategyHelper.AVAILABLE_STRATEGIES:
                raise CommandError("Unknown anonymisation strategy: {}".format(strategy))
            strategies[category] = strategy

        # Assign a default strategy for any remaining categories
        for category in StrategyHelper.DEFAULT_STRATEGIES:
            if category not in strategies:
                strategies[category] = StrategyHelper.DEFAULT_STRATEGIES[category]

        return strategies

    @staticmethod
    def category_for_model(model):
        if not issubclass(model, PrivacyModel):
            return StrategyHelper.CATEGORY_UNTAGGED
        privacy_meta = model.get_privacy_meta()
        if privacy_meta.can_anonymise:
            return StrategyHelper.CATEGORY_ANONYMISABLE
        return StrategyHelper.CATEGORY_UNANONYMISABLE


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
            "--data-strategies",
            "--strategies",
            "-s",
            dest="strategies",
            default="anonymisable:anonymise, unanonymisable:retain, untagged:retain",
            help="Configures the anonymisation strategies that will be applied.",
        )

    def handle(self, *args, **options):
        if not app_settings.GDPR_CAN_ANONYMISE_DATABASE:
            raise ValueError("Database anonymisation is not enabled")

        interactive = options["interactive"]
        strategies = StrategyHelper.parse(options["strategies"])

        if interactive:  # pragma: no cover
            self.stdout.write(
                "The following data anonymisation strategies will be applied:"
            )
            for category, strategy in strategies.items():
                self.stdout.write(" - {category} data: {strategy.upper()}")

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
            # Validate that we can determine a specific anonymisation strategy
            # for every model in the application before modifying any data
            for model in apps.get_models():
                category = StrategyHelper.category_for_model(model)
                strategy = strategies.get(category)
                if strategy is None:
                    raise CommandError(
                        """Missing anonymisation strategy for model {model}!""",
                        """Please check your anonymisation settings."""
                    )

            # Begin applying the requested anonymisation strategy to each model
            for model in apps.get_models():
                category = StrategyHelper.category_for_model(model)
                strategy = strategies.get(category)

                if strategy == StrategyHelper.STRATEGY_ANONYMISE:
                    if issubclass(model, PrivacyModel) and model.check_can_anonymise():
                        model.objects.all().anonymise()
                    else:
                        raise CommandError(
                            """Cannot anonymise {category} model {model}!""",
                            """Please check your anonymisation settings."""
                        )

                elif strategy == StrategyHelper.STRATEGY_DELETE:
                    model.objects.all.delete()

                elif strategy == StrategyHelper.STRATEGY_RETAIN:
                    if issubclass(model, PrivacyModel) and model.check_can_anonymise():
                        raise CommandError(
                            """Refusing to retain anonymisable model {model}!""",
                            """Please check your anonymisation settings."""
                        )

            msg = "{} models anonymised.".format(
                len(registry.models_allowed_to_anonymise())
            )
            self.stdout.write(msg)

        else:  # pragma: no cover
            self.stdout.write("Anonymisation cancelled.")
