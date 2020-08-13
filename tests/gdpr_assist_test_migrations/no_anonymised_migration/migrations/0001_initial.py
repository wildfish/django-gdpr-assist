# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2020-07-16 12:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    run_before = [("gdpr_assist", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ModelWithoutPrivacyMeta",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("anonymised", models.BooleanField(default=False)),
                ("chars", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254)),
            ],
        )
    ]