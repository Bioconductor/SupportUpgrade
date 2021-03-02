# Inherit from the main settings file.
import os, sys


from biostar.accounts.settings import *

# Inherit from the accounts settings file.
from biostar.planet.settings import *

def join(*args):
    return os.path.abspath(os.path.join(*args))

# Django debug flag.
DEBUG = True

SITE_NAME = 'Biostar Forum'

# Site settings.
POSTS_PER_PAGE = 50
USERS_PER_PAGE = 100
MESSAGES_PER_PAGE = 100
TAGS_PER_PAGE = 50
AWARDS_PER_PAGE = 50

STATS_DIR = os.path.join(BASE_DIR, "export", "stats")

# Enable image upload
PAGEDOWN_IMAGE_UPLOAD_ENABLED = True

# Upload path for pagedown images, relative to media root.
PAGEDOWN_IMAGE_UPLOAD_PATH = "images"

# File containing list of tags,
# with atleast one required when making a post.
REQUIRED_TAGS = ''

# Link to display when showing error msg in forms.
REQUIRED_TAGS_URL = "/"

# The gravatar image used for users, applied to all users.
GRAVATAR_ICON = None

# Valid options; block, disabled, threaded, uwsgi, celery.
TASK_RUNNER = 'celery'

# Threshold to classify spam
SPAM_THRESHOLD = .5

# Allows post closing.
ALLOW_POST_CLOSING = False

# Classify posts and assign a spam score on creation.
CLASSIFY_SPAM = True

# Log the time for each request
TIME_REQUESTS = True

# Number of results to display in total.
SEARCH_LIMIT = 50

# Initialize the planet app.
INIT_PLANET = True

# Minimum amount of characters to preform searches
SEARCH_CHAR_MIN = 1

# How many posts to index in one job.
BATCH_INDEXING_SIZE = 1000

# Add another context processor to first template.
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'biostar.forum.context.forum'
]

# Set the number of items in each feed.
VOTE_FEED_COUNT = 10
LOCATION_FEED_COUNT = 5
AWARDS_FEED_COUNT = 10
REPLIES_FEED_COUNT = 15

SIMILAR_FEED_COUNT = 30

SESSION_UPDATE_SECONDS = 60

# Maximum number of awards every SESSION_UPDATE_SECONDS.
MAX_AWARDS = 2

# Search index name
INDEX_NAME = os.environ.setdefault("INDEX_NAME", "index")
# Relative index directory

INDEX_DIR = os.environ.setdefault("INDEX_DIR", "search")
# Absolute path to index directory in export/
INDEX_DIR = os.path.abspath(os.path.join(MEDIA_ROOT, '..', INDEX_DIR))

# Spam index used to classify new posts as spam or ham.
SPAM_INDEX_NAME = os.getenv("SPAM_INDEX_NAME", "spam")
SPAM_INDEX_DIR = 'spammers'

# Absolute path to spam index directory in export/
SPAM_INDEX_DIR = join(MEDIA_ROOT, '..', SPAM_INDEX_DIR)

SOCIALACCOUNT_EMAIL_VERIFICATION = None
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_QUERY_EMAIL = True

LOGIN_REDIRECT_URL = "/"
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True

SOCIALACCOUNT_ADAPTER = "biostar.accounts.adapter.SocialAccountAdapter"

PAGEDOWN_APP = ['pagedown.apps.PagedownConfig']

FORUM_APPS = [

    'biostar.forum.apps.ForumConfig',
]

# Additional middleware.
MIDDLEWARE += [
    #'biostar.forum.middleware.ban_ip',
    'biostar.forum.middleware.user_tasks',
    'biostar.forum.middleware.benchmark',
]

# Post types displayed when creating, empty list displays all types.
ALLOWED_POST_TYPES = []


# Import the default pagedown css first, then our custom CSS sheet
# to avoid having to specify all the default styles
PAGEDOWN_WIDGET_CSS = ('pagedown/demo/browser/demo.css',)

INSTALLED_APPS = DEFAULT_APPS + FORUM_APPS + PAGEDOWN_APP + PLANET_APPS + ACCOUNTS_APPS + EMAILER_APP

# Documentation for docs
FORUM_DOCS = os.path.join(DOCS_ROOT, "forum")

# Add docs to static files directory
STATICFILES_DIRS += [DOCS_ROOT]

ROOT_URLCONF = 'biostar.forum.urls'

WSGI_APPLICATION = 'biostar.wsgi.application'

# Time between two accesses from the same IP to qualify as a different view (seconds)
POST_VIEW_TIMEOUT = 300

# This flag is used flag situation where a data migration is in progress.
# Allows us to turn off certain type of actions (for example sending emails).
DATA_MIGRATION = False

# Default cache
CACHES = {
    'default': {
        #'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Tries to load up secret settings from a predetermined module
# This is for convenience only!
try:
    from conf.run.site_secrets import *
    #print(f"Loaded secrets from: conf.run.secrets")
except Exception as exc:
    print(f"Secrets module not imported: {exc}", file=sys.stderr)
    pass

# Enable debug toolbar specific functions
if DEBUG_TOOLBAR:
    INSTALLED_APPS.extend([
        'debug_toolbar',
    ])
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
