# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-08 17:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr_assist', '0009_retentionpolicyitem_anonymised'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventlog',
            name='event',
            field=models.CharField(choices=[('delete', 'Delete'), ('anonymise', 'Anonymise'), ('anonymisation recursion start', 'Anonymisation Recursion Start'), ('anonymisation recursion end', 'Anonymisation Recursion End'), ('anonymisation abandoned, already done', 'Snonymisation Sbandoned, Already Done')], max_length=37),
        ),
    ]