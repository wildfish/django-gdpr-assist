# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-29 11:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr_assist', '0002_auto_20200628_1625'),
    ]

    operations = [
        migrations.AddField(
            model_name='retentionpolicyitem',
            name='description',
            field=models.CharField(default='', max_length=255),
        ),
    ]