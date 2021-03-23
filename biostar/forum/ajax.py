from functools import wraps, partial
import logging
import json
from ratelimit.decorators import ratelimit
from urllib import request as builtin_request
# import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
from urllib.parse import quote

from django.core.cache import cache
from django.conf import settings
from django.db.models import Q, Count
from django.shortcuts import reverse, redirect
from django.template import loader
from django.http import JsonResponse

from whoosh.searching import Results

from biostar.accounts.models import Profile, User
from . import auth, util, forms, tasks, search, views, const
from .models import Post, Vote, Subscription, delete_post_cache


def ajax_msg(msg, status, **kwargs):
    payload = dict(status=status, msg=msg)
    payload.update(kwargs)
    return JsonResponse(payload)


logger = logging.getLogger("engine")
ajax_success = partial(ajax_msg, status='success')
ajax_error = partial(ajax_msg, status='error')

MIN_TITLE_CHARS = 10
MAX_TITLE_CHARS = 180

HOURLY_RATE = settings.HOURLY_RATE
MINUTE_RATE = settings.MINUTE_RATE

RATELIMIT_KEY = settings.RATELIMIT_KEY


class ajax_error_wrapper:
    """
    Used as decorator to trap/display  errors in the ajax calls
    """

    def __init__(self, method, login_required=True):
        self.method = method
        self.login_required = login_required

    def __call__(self, func, *args, **kwargs):

        @wraps(func)
        def _ajax_view(request, *args, **kwargs):

            if request.method != self.method:
                return ajax_error(f'{self.method} method must be used.')

            if not request.user.is_authenticated and self.login_required:
                return ajax_error('You must be logged in.')

            if request.user.is_authenticated and request.user.profile.is_spammer:
                return ajax_error('You must be logged in.')

            try:
                return func(request, *args, **kwargs)
            except Exception as exc:
                return ajax_error(f'Error: {exc}')

        return _ajax_view


def ajax_test(request):
    """
    Creates a commment on a top level post.
    """
    msg = "OK"
    print(f"HeRe= {request.POST} ")
    return ajax_error(msg=msg)


@ajax_error_wrapper(method="GET")
def user_image(request, username):
    user = User.objects.filter(username=username).first()

    gravatar_url = auth.gravatar(user=user)
    return redirect(gravatar_url)


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="POST")
def ajax_vote(request):
    was_limited = getattr(request, 'limited', False)

    if was_limited:
        return ajax_error(msg="Too many votes from same IP address. Temporary ban.")

    user = request.user
    type_map = dict(upvote=Vote.UP, bookmark=Vote.BOOKMARK, accept=Vote.ACCEPT)

    vote_type = request.POST.get('vote_type')

    vote_type = type_map.get(vote_type)

    post_uid = request.POST.get('post_uid')

    # Check the post that is voted on.
    post = Post.objects.filter(uid=post_uid).first()

    if post.author == user and vote_type == Vote.UP:
        return ajax_error("You can not upvote your own post.")

    if post.author == user and vote_type == Vote.ACCEPT:
        return ajax_error("You can not accept your own post.")

    not_moderator = user.is_authenticated and not user.profile.is_moderator
    if post.root.author != user and not_moderator and vote_type == Vote.ACCEPT:
        return ajax_error("Only moderators or the person asking the question may accept answers.")

    msg, vote, change = auth.apply_vote(post=post, user=user, vote_type=vote_type)

    # Expire post cache upon vote.
    delete_post_cache(post)

    return ajax_success(msg=msg, change=change)


def validate_drop(request):
    """
    Vaildates drag and drop and makes
    """
    parent_uid = request.POST.get("parent", '')
    uid = request.POST.get("uid", '')
    user = request.user
    parent = Post.objects.filter(uid=parent_uid).first()
    post = Post.objects.filter(uid=uid).first()

    if not post:
        msg = "Post does not exist."
        return False, msg

    if parent_uid == "NEW":
        return True, "Valid drop."

    if not parent:
        msg = "Parent needs to be provided."
        return False, msg

    if not (user.profile.is_moderator or post.author == user):
        msg = "Only moderators or the author can move posts."
        return False, msg

    children = set()
    auth.walk_down_thread(parent=post, collect=children)

    if parent == post or (parent in children) or parent.root != post.root:
        msg = "Can not move post here."
        return False, msg

    if post.is_toplevel:
        msg = "Top level posts can not be moved."
        return False, msg

    return True, "Valid drop"


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="POST", login_required=True)
def drag_and_drop(request):
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        return ajax_error(msg="Too many request from same IP address. Temporary ban.")

    parent_uid = request.POST.get("parent", '')
    uid = request.POST.get("uid", '')

    parent = Post.objects.filter(uid=parent_uid).first()
    post = Post.objects.filter(uid=uid).first()
    post_type = Post.COMMENT

    valid, msg = validate_drop(request)
    if not valid:
        return ajax_error(msg=msg)

    # Dropping comment as a new answer
    if parent_uid == "NEW":
        parent = post.root
        post_type = Post.ANSWER

    Post.objects.filter(uid=post.uid).update(type=post_type, parent=parent)

    post.update_parent_counts()
    redir = post.get_absolute_url()

    return ajax_success(msg="success", redir=redir)


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="POST")
def ajax_subs(request):
    was_limited = getattr(request, 'limited', False)

    if was_limited:
        return ajax_error(msg="Too many request from same IP address. Temporary ban.")

    type_map = dict(messages=Subscription.LOCAL_MESSAGE, email=Subscription.EMAIL_MESSAGE,
                    unfollow=Subscription.NO_MESSAGES)

    # Get the root and sub type.
    root_uid = request.POST.get('root_uid')
    sub_type = request.POST.get("sub_type")
    sub_type = type_map.get(sub_type, Subscription.NO_MESSAGES)
    user = request.user

    # Get the post that is subscribed to.
    root = Post.objects.filter(uid=root_uid).first()

    auth.create_subscription(post=root, user=user, sub_type=sub_type)

    return ajax_success(msg="Changed subscription.")


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="POST")
def ajax_digest(request):
    was_limited = getattr(request, 'limited', False)
    user = request.user
    if was_limited:
        return ajax_error(msg="Too many request from same IP address. Temporary ban.")
    type_map = dict(daily=Profile.DAILY_DIGEST, weekly=Profile.WEEKLY_DIGEST,
                    monthly=Profile.MONTHLY_DIGEST)
    if user.is_anonymous:
        return ajax_error(msg="You need to be logged in to edit your profile.")

    # Get the post and digest preference.
    pref = request.POST.get('pref')
    pref = type_map.get(pref, Profile.NO_DIGEST)
    Profile.objects.filter(user=user).update(digest_prefs=pref)

    return ajax_success(msg="Changed digest options.")


def validate_recaptcha(token):
    """
    Send recaptcha token to API to check if user response is valid
    """
    url = 'https://www.google.com/recaptcha/api/siteverify'
    values = {
        'secret': settings.RECAPTCHA_PRIVATE_KEY,
        'response': token
    }
    data = urlencode(values).encode("utf-8")
    response = builtin_request.urlopen(url, data)
    result = json.load(response)

    if result['success']:
        return True, ""

    return False, "Invalid reCAPTCHA. Please try again."


def validate_toplevel_fields(fields={}):
    """Validate fields found in top level posts"""

    title = fields.get('title', '')
    tag_list = fields.get('tag_list', [])
    tag_val = fields.get('tag_val', '')
    post_type = fields.get('post_type', '')
    title_length = len(title.replace(' ', ''))
    allowed_types = [opt[0] for opt in Post.TYPE_CHOICES]
    tag_length = len(tag_list)

    if title_length <= forms.MIN_CHARS:
        msg = f"Title too short, please add more than {forms.MIN_CHARS} characters."
        return False, msg

    if title_length > forms.MAX_TITLE:
        msg = f"Title too long, please add less than {forms.MAX_TITLE} characters."
        return False, msg

    if post_type not in allowed_types:
        msg = "Not a valid post type."
        return False, msg
    if tag_length > forms.MAX_TAGS:
        msg = f"Too many tags, maximum of {forms.MAX_TAGS} tags allowed."
        return False, msg

    if len(tag_val) > 100:
        msg = f"Tags have too many characters, maximum of 100 characters total allowed in tags."
        return False, msg

    return True, ""


def validate_post_fields(fields={}, is_toplevel=False):
    """
    Validate fields found in dictionary.
    """
    content = fields.get('content', '')
    content_length = len(content.replace(' ', ''))

    # Validate fields common to all posts.
    if content_length <= forms.MIN_CHARS:
        msg = f"Content too short, please add more than {forms.MIN_CHARS} characters."
        return False, msg
    if content_length > forms.MAX_CONTENT:
        msg = f"Content too long, please add less than {forms.MAX_CONTENT} characters."
        return False, msg

    # Validate fields found in top level posts
    if is_toplevel:
        return validate_toplevel_fields(fields=fields)

    return True, ""


def get_fields(request, post=None):
    """
    Used to retrieve all fields in a request used for editing and creating posts.
    """
    user = request.user
    content = request.POST.get("content", "") or post.content
    title = request.POST.get("title", "") or post.title
    post_type = request.POST.get("type", Post.QUESTION)

    post_type = int(post_type) if str(post_type).isdigit() else Post.QUESTION
    recaptcha_token = request.POST.get("recaptcha_response")

    # Fields found in top level posts
    tag_list = {x.strip() for x in request.POST.getlist("tag_val", [])}
    tag_val = ','.join(tag_list) or post.tag_val

    fields = dict(content=content, title=title, post_type=post_type, tag_list=tag_list, tag_val=tag_val,
                  user=user, recaptcha_token=recaptcha_token, )

    return fields


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="POST", login_required=True)
def ajax_edit(request, uid):
    """
    Edit post content using ajax.
    """
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        return ajax_error(msg="Too many request from same IP address. Temporary ban.")

    post = Post.objects.filter(uid=uid).first()
    if not post:
        return ajax_error(msg="Post does not exist")

    # Get the fields found in the request
    fields = get_fields(request=request, post=post)

    if not (request.user.profile.is_moderator or request.user == post.author):
        return ajax_error(msg="Only moderators or the author can edit posts.")

    # Validate fields in request.POST
    valid, msg = validate_post_fields(fields=fields, is_toplevel=post.is_toplevel)
    if not valid:
        return ajax_error(msg=msg)

    # Set the fields for this post.
    if post.is_toplevel:
        post.title = fields.get('title', post.title)
        post.type = fields.get('post_type', post.type)
        post.tag_val = fields.get('tag_val', post.tag_val)

    post.lastedit_user = request.user
    post.lastedit_date = util.now()
    post.content = fields.get('content', post.content)
    post.save()

    # Get the newly set tags to render
    tags = post.tag_val.split(",")
    context = dict(post=post, tags=tags, show_views=True)
    tmpl = loader.get_template('widgets/post_tags.html')
    tag_html = tmpl.render(context)

    # Get the newly updated user line
    context = dict(post=post, avatar=post.is_comment)
    tmpl = loader.get_template('widgets/post_user_line.html')
    user_line = tmpl.render(context)

    # Prepare the new title to render
    new_title = f'{post.get_type_display()}: {post.title}'

    return ajax_success(msg='success', html=post.html, title=new_title, user_line=user_line, tag_html=tag_html)


@ajax_error_wrapper(method="POST", login_required=True)
def ajax_delete(request):
    uid = request.POST.get('uid')
    user = request.user
    post = Post.objects.filter(uid=uid).first()

    if not post:
        return ajax_error(msg="Post does not exist")

    if not (user.profile.is_moderator or post.author == user):
        return ajax_error(msg="Only moderators and post authors can delete.")

    url, msg = auth.delete_post(post=post, user=user)

    return ajax_success(msg=msg, url=url)


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="POST")
def ajax_comment_create(request):
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        return ajax_error(msg="Too many request from same IP address. Temporary ban.")

    # Fields common to all posts
    user = request.user
    content = request.POST.get("content", "")

    parent_uid = request.POST.get('parent', '')
    parent = Post.objects.filter(uid=parent_uid).first()
    if not parent:
        return ajax_error(msg='Parent post does not exist.')

    fields = dict(content=content, user=user, parent=parent)

    # Validate the fields
    valid, msg = validate_post_fields(fields=fields, is_toplevel=False)
    if not valid:
        return ajax_error(msg=msg)

    # Create the comment.
    post = Post.objects.create(type=Post.COMMENT, content=content, author=user, parent=parent)

    return ajax_success(msg='Created post', redirect=post.get_absolute_url())


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="GET")
def handle_search(request):
    """
    Used to search by the user handle.
    """

    query = request.GET.get('query')
    if query:
        users = User.objects.filter(username__icontains=query
                                    ).values_list('username', flat=True
                                                  ).order_by('profile__score')
    else:
        users = User.objects.order_by('profile__score').values_list('username', flat=True)

    users = list(users[:20])
    # Return list of users matching username
    return ajax_success(users=users, msg="Username searched")


@ratelimit(key=RATELIMIT_KEY, rate=HOURLY_RATE)
@ratelimit(key=RATELIMIT_KEY, rate=MINUTE_RATE)
@ajax_error_wrapper(method="GET")
def inplace_form(request):
    """
    Used to render inplace forms for editing posts.
    """
    MIN_LINES = 10
    user = request.user
    if user.is_anonymous:
        return ajax_error(msg="You need to be logged in to edit or create posts.")

    # Get the current post uid we are editing
    uid = request.GET.get('uid', '')
    post = Post.objects.filter(uid=uid).first()
    if not post:
        return ajax_error(msg="Post does not exist.")

    add_comment = request.GET.get('add_comment', False)

    html = "" if add_comment else post.html

    # Load the content and form template
    template = "forms/form_inplace.html"
    tmpl = loader.get_template(template_name=template)

    nlines = post.num_lines(offset=3)
    rows = nlines if nlines >= MIN_LINES else MIN_LINES
    form = forms.PostLongForm(user=request.user)

    content = '' if add_comment else post.content
    context = dict(user=user, post=post, new=add_comment, html=html,
                   captcha_key=settings.RECAPTCHA_PUBLIC_KEY, rows=rows, form=form,
                   content=content)

    form = tmpl.render(context)

    return ajax_success(msg="success", inplace_form=form)


def similar_posts(request, uid):
    """
    Return a feed populated with posts similar to the one in the request.
    """

    post = Post.objects.filter(uid=uid).first()
    if not post:
        ajax_error(msg='Post does not exist.')

    cache_key = f"{const.SIMILAR_CACHE_KEY}-{post.uid}"
    results = cache.get(cache_key)

    if results is None:
        logger.debug("Setting similar posts cache.")
        results = search.more_like_this(uid=post.uid)
        # Set the results cache for 1 hour
        cache.set(cache_key, results, 3600)

    template_name = 'widgets/similar_posts.html'

    tmpl = loader.get_template(template_name)
    context = dict(results=results)
    results_html = tmpl.render(context)

    return ajax_success(html=results_html, msg="success")
