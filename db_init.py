from db import *

with db:
    db.drop_tables([User, Reset, Post])
    db.create_tables([User, Reset, Post])
