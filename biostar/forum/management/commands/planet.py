
from django.conf import settings

from biostar.planet.models import Blog, BlogPost
from django.core.management.base import BaseCommand
import os
import logging

from biostar.planet import auth

logger = logging.getLogger('engine')


def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))


class Command(BaseCommand):
    help = 'Create search index for the forum app.'

    def add_arguments(self, parser):

        parser.add_argument('--add', dest='add', help='adds blogs to the database')
        parser.add_argument('--download', dest='download', action="store_true", default=False,
                            help='downloads latest feeds')
        parser.add_argument('--report', action='store_true', default=False, help="Reports on the content of the index.")
        parser.add_argument('--update', dest='update', default=0, type=int, help='updates existing blogs with latest feeds')

    def handle(self, *args, **options):
        # Create the planet directory if it is missing
        os.makedirs(settings.PLANET_DIR, exist_ok=True)

        #BlogPost.objects.all().delete()
        #Blog.objects.all().delete()

        fname = options['add']
        if fname:
            fname = os.path.abspath(os.path.join(settings.PLANET_DIR, fname))
            auth.add_blogs(fname)

        if options['download']:
            fname = os.path.abspath(os.path.join(settings.PLANET_DIR, 'example-feeds.txt'))
            auth.add_blogs(fname)
            auth.download_blogs()

        count = options['update']
        if count:
            auth.update_entries(count)
