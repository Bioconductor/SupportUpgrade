# Generated by Django 3.1 on 2021-02-20 21:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0012_delete_sync'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='award',
            name='uid',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='uid',
        ),
        migrations.RemoveField(
            model_name='vote',
            name='uid',
        ),
    ]
