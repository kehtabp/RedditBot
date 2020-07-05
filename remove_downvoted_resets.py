#!/usr/bin/env python3
import argparse

import backoff
import praw
import requests

from db import Reset

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()

negation_list = ["dont", "do not", "don't"]


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException)
def get_user_comments(reddit_client, author):
    return reddit_client.redditor(author).comments.new(limit=20)


def make_reset_unreal(comment_id):
    for reset in (Reset.select().where(Reset.id == comment_id, Reset.real == True)):
        reset.real = False
        reset.save()
        return True
    return False


try:
    from secret import secret, password, username, app_id

    reddit = praw.Reddit(client_id=app_id,
                         client_secret=secret,
                         username=username,
                         password=password,
                         user_agent="Reset Bot")
    for comment in get_user_comments(reddit, "r_chess_bot"):
        # print(comment.score)
        if comment.score < 1:
            parent_id = comment.parent_id.split('_')[1]
            if make_reset_unreal(parent_id) and args.live:
                print(f"removing {parent_id} for being downvoted with score: {comment.score}")
                body_parts = comment.body.split("\n\n")
                removed_body = f"This reset has been downvoted so it won't count\n\n{body_parts[2]}"
                comment.edit(removed_body)


except ModuleNotFoundError:
    raise ModuleNotFoundError("secrets.py not found, create secrets.py file "
                              "with following variables: secret, password, username, app_id")
