# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-06 18:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr_assist', '0007_auto_20200706_1756'),
    ]

    operations = [
        migrations.AlterField(
            model_name='retentionpolicyitem',
            name='start_date',
            field=models.DateTimeField(null=True),
        ),
    ]