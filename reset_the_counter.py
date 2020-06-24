from datetime import datetime as dt
import backoff
import requests
from db import *
import praw

negation_list = ["dont", "do not", "don't"]


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException)
def get_comments_since(keyword, after):
    pd_url = f'https://api.pushshift.io/reddit/search/comment/'
    # pd_url = f'https://api.pushshift.io/reddit/search/comment/?filter=author,body,created_utc,id,link_id'

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


def respond_to_reset(author):
    try:
        from secret import secret, password, username, app_id

        reddit = praw.Reddit(client_id="my client id",
                             client_secret="my client secret",
                             user_agent="Reset Bot")
    except ModuleNotFoundError:
        print("secrets.py not found")
        print("create secrets.py file with following paramters secret, password, username, app_id")

def find_resets(last_date=""):
    comments = get_comments_since('"reset the counter"', last_date)
    for comment in comments:
        if comment['link_id'] == comment['parent_id']:
            last_date = comment['created_utc']
            date = dt.fromtimestamp(last_date)
            author = comment['author']
            body = comment['body']
            reset_id = comment['id']
            post_id = comment['link_id'].split('_')[1]
            user, created_user = User.get_or_create(username=author)
            post, created_post = Post.get_or_create(post_id=post_id)
            real = is_real(body)
            if real:
                respond_to_reset(author)
            save_reset(reset_id, body, date, post, user, real)
            print(date, author, reset_id, post_id, real)
    print(f"Executed {len(comments)} times")
    if len(comments) == 500:
        find_resets(last_date)


def save_reset(reset_id, body, date, post, user, real=True):
    defaults = {'user': user, 'date': date, 'body': body, 'post': post, 'real': real}
    reset, create = Reset.get_or_create(id=reset_id, defaults=defaults)
    return reset


def get_last_reset():
    last_reset = (Reset.select(Reset.date).limit(1).order_by(Reset.date.desc()))
    for reset in last_reset:
        return reset


def top_reseters():
    print(Reset.filter(real=0).count())
    resets = (User.select(User.username.alias("user"), fn.COUNT(Reset.id).alias("number"))
              .limit(3)
              .join(Reset)
              .where(Reset.real == True)
              .group_by(User.username)
              .order_by(SQL("number").desc()))
    # print(keyword)
    for user_reset in resets:
        print(user_reset.user, user_reset.number)


def disable_false_resets():
    for reset in (Reset.select()):
        reset.real = is_real(reset.body)
        reset.save()


disable_false_resets()
query = (Reset.select(Reset.date).limit(1).order_by(Reset.date.desc()))
for last_reset in query:
    find_resets(last_reset.date)
