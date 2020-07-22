# -*- coding: utf-8 -*-
from django.db import migrations

from gdpr_assist.upgrading import MigrateGdprAnonymised


class Migration(migrations.Migration):
    dependencies = [
        ("anonymised_migration", "0001_initial"),
        ("gdpr_assist", "0002_privacyanonymised"),
    ]
    operations = [MigrateGdprAnonymised("ModelWithPrivacyMeta")]
