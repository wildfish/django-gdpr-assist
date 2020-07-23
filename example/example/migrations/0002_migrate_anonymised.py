# -*- coding: utf-8 -*-
from django.db import migrations

from gdpr_assist.upgrading import MigrateGdprAnonymised


class Migration(migrations.Migration):
    dependencies = [
        ("example", "0001_initial"),
        ("gdpr_assist", "0002_privacyanonymised"),
    ]
    operations = [
        MigrateGdprAnonymised("HealthRecord"),
        MigrateGdprAnonymised("MailingListLog"),
        MigrateGdprAnonymised("Person"),
        MigrateGdprAnonymised("PersonProfile"),
    ]
