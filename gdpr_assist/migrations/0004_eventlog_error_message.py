# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-01 12:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr_assist', '0003_retentionpolicyitem_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventlog',
            name='error_message',
            field=models.CharField(blank=True, default=None, max_length=1000, null=True),
        ),
    ]