#!/usr/bin/env python3

from datetime import datetime as dt

import backoff
import praw
import requests

from db import *

negation_list = ["dont", "do not", "don't"]
reddit_prefix = "https://www.reddit.com"


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException)
def get_comments_since(keyword, after):
    filter_params = "filter=author,body,created_utc,id,link_id,parent_id,permalink"
    pd_url = f'https://api.pushshift.io/reddit/search/comment/?{filter_params}'

    params = {
        'size': 500,
        'after': after,
        'subreddit': 'chess',
        'q': keyword,
        'sort_type': 'created_utc',
        'sort': 'asc'
    }

    r = requests.get(pd_url, params=params)
    if r.status_code != 200:
        raise requests.exceptions.RequestException('API response: {}'.format(r.status_code))

    data = r.json()
    return data['data']


def is_real(body):
    for neg in negation_list:
        if neg in body.lower():
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


def respond_to_reset(reset_id, author, reset_date):
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
        comment = reddit.comment(id=reset_id)
        number_of_resets = get_user_reset_number(author)
        if number_of_resets is None:
            number_of_resets_text = f"Congratulations on your first reset /u/{author}!"
        else:
            number_of_resets_text = f"/u/{author} reset the counter {number_of_resets + 1} times."
        time_delta = reset_date - last_reset.date
        template = f"""Counter is reset! There's been no reset for: {time_delta}

{number_of_resets_text}

[Last reset]({reddit_prefix}{last_reset.permalink}) was on {last_reset.date} by /u/{last_reset.user.username}
"""
        comment.reply(template)
        # print(template)
    except ModuleNotFoundError:
        raise ModuleNotFoundError("secrets.py not found, create secrets.py file "
              "with following variables: secret, password, username, app_id")


def is_first(post_id):
    return bool(Post.get_or_none(post_id == post_id))


def find_resets(last_date=""):
    comments = get_comments_since('"reset the counter"', last_date)
    top_level_comments = [tlc for tlc in comments if tlc['link_id'] == tlc['parent_id']]
    for comment in top_level_comments:
        last_date = comment['created_utc']
        date = dt.fromtimestamp(last_date)
        author = comment['author']
        body = comment['body']
        reset_id = comment['id']
        permalink = comment['permalink']
        post_id = comment['link_id'].split('_')[1]
        real = is_real(body)
        post, created_post = Post.get_or_create(post_id=post_id)
        user, created_user = User.get_or_create(username=author)
        if real and created_post:
            respond_to_reset(reset_id, author, date)
        save_reset(reset_id, body, date, post, user, real, permalink)
    print(f"Executed {len(top_level_comments)} times")
    if len(comments) == 500:
        find_resets(last_date)


def save_reset(reset_id, body, date, post, user, real, permalink):
    # print(date, user.username, reset_id, post.post_id, real)

    defaults = {'user': user, 'date': date, 'body': body, 'post': post, 'real': real, 'permalink': permalink}
    reset, create = Reset.get_or_create(id=reset_id, defaults=defaults)
    return reset


def get_last_reset():
    last_reset = (Reset.select(Reset.id, Reset.date, User.username, Reset.permalink)
                  .limit(1)
                  .join(User)
                  .where(Reset.real == True)
                  .order_by(Reset.date.desc()))
    for reset in last_reset:
        return reset


def top_reseters(num):
    # print(Reset.filter(real=0).count())
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
        print(f"{i+1}. /u/{user.user} – {user.number} resets")


def entry_point():
    find_resets(get_last_reset().date)
    # update_about()


entry_point()
