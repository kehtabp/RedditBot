#!/usr/bin/env python3

import argparse
import logging
import types
from datetime import datetime as dt

import backoff
import humanize as humanize
import praw
import requests

max_size = 100

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
parser.add_argument('--populate', action='store_true')
parser.add_argument('--test', action='store_true')
args = parser.parse_args()
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

negation_list = ["dont", "do not", "don't"]
reddit_prefix = "https://www.reddit.com"
if args.live or args.populate:
    subreddit = 'chess'
    from db import *

elif args.test:
    from test_db import *

    subreddit = 'testingground4bots'

phrase = "reset the counter"


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException)
def get_comments_since(keyword, after):
    filter_params = "filter=author,body,created_utc,id,link_id,parent_id,permalink"
    pd_url = f'https://api.pushshift.io/reddit/search/comment/?{filter_params}'

    params = {
        'size': max_size,
        'after': after,
        'subreddit': subreddit,
        'q': keyword,
        'sort_type': 'created_utc',
        'sort': 'asc'
    }

    r = requests.get(pd_url, params=params)
    if r.status_code != 200:
        raise requests.exceptions.RequestException('API response: {}'.format(r.status_code))

    data = r.json()
    return data['data']


def is_real(body: str):
    body_casefold = body.casefold()
    pre_body = body_casefold.split(phrase)[0]
    is_split = False
    for neg in negation_list:
        for splitter in ["?", ".", "!"]:
            if splitter in pre_body:
                is_split = True
                if neg in pre_body.split(splitter)[-1]:
                    return False
        if not is_split:
            if neg in pre_body:
                return False
    return True


def get_user_reset_number(author):
    reset_count = (User.select(User.username.alias("user"), fn.COUNT(Reset.id).alias("number"))
                   .join(Reset)
                   .where((Reset.real == True), (User.username == author))
                   .group_by(User.username)
                   .order_by(SQL("number").desc()))
    for count in reset_count:
        return count.number


def respond_to_reset(reset):
    try:
        from secret import secret, password, username, app_id

        reddit = praw.Reddit(client_id=app_id,
                             client_secret=secret,
                             username=username,
                             password=password,
                             user_agent="Reset Bot")
        last_reset = get_last_reset()
        if last_reset is None:
            return
        comment = reddit.comment(id=reset.id)
        number_of_resets = get_user_reset_number(reset.author)
        if number_of_resets is None:
            number_of_resets_text = f"Congratulations on your first reset /u/{reset.author}!"
        else:
            number_of_resets_text = f"/u/{reset.author} reset the counter {number_of_resets + 1} times."
        time_delta = humanize.precisedelta(reset.date - last_reset.date)

        body = f"""Counter is reset! There's been no reset for: {time_delta}

{number_of_resets_text}

[Last reset]({reddit_prefix}{last_reset.permalink}) was on {last_reset.date} by /u/{last_reset.user.username}
"""
        comment.reply(body)
        logging.info(f"Responding to {reset.id}")
    except ModuleNotFoundError:
        logging.critical("secrets.py  not found")
        raise ModuleNotFoundError("secrets.py not found, create secrets.py file "
                                  "with following variables: secret, password, username, app_id")


def is_first(post_id):
    return bool(Post.get_or_none(post_id == post_id))


def find_resets(comments):
    posted = 0
    found = 0
    last_date = ""
    for comment in comments:
        reset = types.SimpleNamespace()
        reset.body = comment['body']
        if comment['link_id'] != comment['parent_id'] or phrase not in reset.body.casefold():
            continue
        found += 1
        last_date = comment['created_utc']
        reset.date = dt.fromtimestamp(last_date)
        reset.author = comment['author']
        reset.id = comment['id']
        reset.permalink = comment['permalink']
        reset.post_id = comment['link_id'].split('_')[1]
        reset.post, created_post = Post.get_or_create(post_id=reset.post_id)
        reset.user, created_user = User.get_or_create(username=reset.author)
        reset.real = is_real(reset.body) and created_post
        if reset.real and (args.live or args.test):
            posted += 1
            respond_to_reset(reset)
        save_reset(reset)
    logging.info(f"Found {found} new comments. Posted {posted} times")
    if len(comments) == max_size:
        find_resets(get_comments_since('"reset the counter"', last_date))
    monitor()


def monitor():
    logging.info("Entering monitoring mode.")
    from secret import secret, password, username, app_id
    reddit = praw.Reddit(client_id=app_id,
                         client_secret=secret,
                         username=username,
                         password=password,
                         user_agent="Reset Bot")
    comments = reddit.subreddit(subreddit).stream.comments()
    for comment in comments:
        reset = types.SimpleNamespace()
        reset.body = comment.body
        if comment.link_id != comment.parent_id or phrase not in comment.body.casefold():
            continue

        last_date = comment.created_utc

        reset.date = dt.fromtimestamp(last_date)
        reset.author = comment.author
        reset.id = comment.id
        reset.permalink = comment.permalink
        reset.post_id = comment.link_id.split('_')[1]

        reset.post, created_post = Post.get_or_create(post_id=reset.post_id)
        reset.user, created_user = User.get_or_create(username=reset.author)
        reset.real = is_real(reset.body) and created_post
        if reset.real and (args.live or args.test):
            respond_to_reset(reset)
        save_reset(reset)


def save_reset(reset):
    # print(date, user.username, reset_id, post.post_id, real)

    defaults = {'user': reset.user, 'date': reset.date, 'body': reset.body, 'post': reset.post, 'real': reset.real,
                'permalink': reset.permalink}
    reset, created = Reset.get_or_create(id=reset.id, defaults=defaults)
    if created:
        logging.info(
            f"{reset.date}: Saving reset to db. User: {reset.user.username} Reset id: {reset.id}, "
            f"Post id:{reset.post.post_id}, Real: {reset.real}")
    return reset


def get_last_reset(real=True):
    if real:
        last_reset = (Reset.select(Reset.id, Reset.date, User.username, Reset.permalink)
                      .limit(1)
                      .join(User)
                      .where(Reset.real == True)
                      .order_by(Reset.date.desc()))
    else:
        last_reset = (Reset.select(Reset.id, Reset.date, User.username, Reset.permalink)
                      .limit(1)
                      .join(User)
                      .order_by(Reset.date.desc()))
    for reset in last_reset:
        return reset


def top_reseters(num):
    resets = (User.select(User.username.alias("user"), fn.COUNT(Reset.id).alias("number"))
              .limit(num)
              .join(Reset)
              .where(Reset.real == True)
              .group_by(User.username)
              .order_by(SQL("number").desc()))
    return resets


def disable_false_resets():
    for reset in (Reset.select()):
        reset.real = is_real(reset.body)
        reset.save()


# disable_false_resets()
def update_about():
    top = top_reseters(10)
    for i, user in enumerate(top):
        print(f"{i + 1}. /u/{user.user} – {user.number} resets")


def entry_point():
    if get_last_reset() is not None:
        date = get_last_reset(False).date
    else:
        date = None
    find_resets(get_comments_since('"reset the counter"', date))
    logging.info(f"It's live {args.live}")
    # TODO update_about()


if args.live or args.populate or args.test:
    entry_point()
else:
    print("Supply some args please")
