# Generated by Django 3.1 on 2021-03-30 15:43

from django.db import migrations, models


def init_ranks(apps, schema_editor):

    BlogPost = apps.get_model('planet', 'BlogPost')
    for post in BlogPost.objects.all():
        post.rank = post.creation_date
        post.save()


class Migration(migrations.Migration):

    dependencies = [
        ('planet', '0002_blog_remote'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='rank',
            field=models.DateTimeField(db_index=True, null=True),
        ),
        migrations.RunPython(init_ranks),
    ]
