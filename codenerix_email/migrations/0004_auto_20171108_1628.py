# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-11-08 15:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('codenerix_email', '0003_auto_20170921_1206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailattachment',
            name='path',
            field=models.FileField(upload_to='', verbose_name='Path'),
        ),
    ]
