# Generated by Django 3.1 on 2021-03-18 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_remove_message_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='user_icon',
            field=models.CharField(choices=[('default', 'Default'), ('mp', 'Mystery person'), ('retro', 'Retro'), ('identicon', 'Identicon'), ('monsterid', 'Monster'), ('robohash', 'Robohash')], default='default', max_length=100),
        ),
    ]
