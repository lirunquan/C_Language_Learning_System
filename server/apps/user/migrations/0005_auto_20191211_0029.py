# Generated by Django 2.2 on 2019-12-10 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_auto_20191210_0116'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='is_login',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='teacher',
            name='is_login',
            field=models.BooleanField(default=False),
        ),
    ]
