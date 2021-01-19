import functools
from biostar.accounts.tasks import create_messages
from biostar.emailer.tasks import send_email
from django.conf import settings
import time
from biostar.utils.decorators import spooler, threaded
from biostar.celery import celery_task


from django.db.models import Q
#
# Do not use logging in tasks! Deadlocking may occur!
#
# https://github.com/unbit/uwsgi/issues/1369

if settings.TASKS_CELERY:
    task = celery_task
elif settings.TASKS_UWSGI:
    task = spooler
else:
    task = threaded


def message(msg, level=0):
    print(f"{msg}")


@task
def spam_scoring(post):
    """
    Score the spam with a slight delay.
    """
    from biostar.forum import spam

    # Give spammers the illusion of success with a slight delay
    time.sleep(1)

    try:
        # Give this post a spam score and quarantine it if necessary.
        spam.score(post=post)
    except Exception as exc:
        message(exc)


def tpatt(tag):
    """
    Return pattern matching a tag found in comma separated string.
    (?i)             : case-insensitive flag
    ^{tag}\\s*,      : matches beginning
    ,\\s*{tag}\\s*,  : matches middle
    ,\\s*{tag}$      : matches end
    ^{tag}[^\\w+]    : matches single entry ( no commas )
    """
    patt = fr"(?i)(^{tag}\s*,|,\s*{tag}\s*,|,\s*{tag}$|^{tag}$)"
    return patt


@task
def notify_watched_tags(post, extra_context):
    """
    Notify users watching a given tag found in post.
    """
    from biostar.accounts.models import User
    from django.conf import settings

    users = [User.objects.filter(profile__watched_tags__iregex=tpatt(tag.name)).distinct()
             for tag in post.root.tags.all()]

    # Flatten nested users queryset and get email.
    emails = set(u.email for o in users for u in o)

    from_email = settings.DEFAULT_NOREPLY_EMAIL

    send_email(template_name='messages/watched_tags.html',
               extra_context=extra_context,
               name=post.author.profile.name,
               recipient_list=emails,
               from_email=from_email,
               mass=True)

    return


@task
def update_spam_index(post):
    """
    Update spam index with this post.
    """
    from biostar.forum import spam

    # Index posts explicitly marked as SPAM or NOT_SPAM
    # indexing SPAM increases true positives.
    # indexing NOT_SPAM decreases false positives.
    if not (post.is_spam or post.not_spam):
        return

    # Update the spam index with most recent spam posts
    try:
        spam.add_spam(post=post)
    except Exception as exc:
        message(exc)


@task
def created_post(pid):
    message(f"Created post={pid}")
    pass


#
# This timer leads to problems as described in
#
# https://github.com/unbit/uwsgi/issues/1369
#

# #@timer(secs=180)
# def update_index(*args):
#     """
#     Index 1000 posts every 3 minutes
#     """
#     from biostar.forum.models import Post
#     from biostar.forum import search
#     from django.conf import settings
#
#     # Get un-indexed posts
#     posts = Post.objects.filter(indexed=False)[:settings.BATCH_INDEXING_SIZE]
#
#     # Nothing to be done.
#     if not posts:
#         message("No new posts found")
#         return
#
#     message(f"Indexing {len(posts)} posts.")
#
#     # Update indexed field on posts.
#     Post.objects.filter(id__in=posts.values('id')).update(indexed=True)
#
#     try:
#         search.index_posts(posts=posts)
#         message(f"Updated search index with {len(posts)} posts.")
#     except Exception as exc:
#         message(f'Error updating index: {exc}')
#         Post.objects.filter(id__in=posts.values('id')).update(indexed=False)
#
#     return

# Set in the settings.
# if celery:
#     task = app.task
# elif uwsgi:
#     task = spool
# else:
#     task = threaded
#
#@spool(pass_arguments=True)
# Do this with celery.
#@shared_task
#@task
@task
def create_user_awards(user_id):

    from biostar.accounts.models import User
    from biostar.forum.models import Award, Badge, Post
    from biostar.forum.awards import ALL_AWARDS

    user = User.objects.filter(id=user_id).first()
    # debugging
    # Award.objects.all().delete()

    for award in ALL_AWARDS:
        # Valid award targets the user has earned
        targets = award.validate(user)

        for target in targets:
            date = user.profile.last_login
            post = target if isinstance(target, Post) else None
            badge = Badge.objects.filter(name=award.name).first()

            # Do not award a post multiple times.
            already_awarded = Award.objects.filter(user=user, badge=badge, post=post).exists()
            if post and already_awarded:
                continue

            # Create an award for each target.
            Award.objects.create(user=user, badge=badge, date=date, post=post)

            message(f"award {badge.name} created for {user.email}")


@task
def mailing_list(users, post, extra_context={}):
    """
    Generate notification for mailing list users.
    """
    from django.conf import settings

    # Prepare the templates and emails
    email_template = "messages/mailing_list.html"
    emails = [user.email for user in users]
    author = post.author.profile.name
    from_email = settings.DEFAULT_NOREPLY_EMAIL

    send_email(template_name=email_template,
               extra_context=extra_context,
               name=author,
               from_email=from_email,
               recipient_list=emails,
               mass=True)


@task
def notify_followers(subs, author, extra_context={}):
    """
    Generate notification to users subscribed to a post, excluding author, a message/email.
    """
    from biostar.forum.models import Subscription
    from biostar.accounts.models import Profile
    from django.conf import settings

    # Template used to send local messages
    local_template = "messages/subscription_message.md"

    # Template used to send emails with
    email_template = "messages/subscription_email.html"

    # Does not have subscriptions.
    if not subs:
        return

    users = [sub.user for sub in subs]
    # Every subscribed user gets local messages with any subscription type.
    create_messages(template=local_template,
                    extra_context=extra_context,
                    rec_list=users,
                    sender=author)

    # Select users with email subscriptions.
    # Exclude mailing list users to avoid duplicate emails.
    email_subs = subs.filter(type=Subscription.EMAIL_MESSAGE)
    email_subs = email_subs.exclude(user__profile__digest_prefs=Profile.ALL_MESSAGES)

    # No email subscriptions
    if not email_subs:
        return

    recipient_list = [sub.user.email for sub in email_subs]
    from_email = settings.DEFAULT_NOREPLY_EMAIL

    send_email(template_name=email_template,
               extra_context=extra_context,
               name=author.profile.name,
               from_email=from_email,
               recipient_list=recipient_list,
               mass=True)
