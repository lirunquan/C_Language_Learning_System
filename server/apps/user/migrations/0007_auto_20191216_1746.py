# Generated by Django 2.2 on 2019-12-16 09:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_auto_20191214_1700'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='is_login',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='is_login',
        ),
    ]
