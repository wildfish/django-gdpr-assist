# Generated by Django 3.1.13 on 2022-02-08 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr_assist', '0004_auto_20211215_1057'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventlog',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='privacyanonymised',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
