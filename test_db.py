from peewee import *

db = SqliteDatabase('data/test.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    username = CharField(unique=True)


class Post(BaseModel):
    post_id = CharField(unique=True)


class Reset(BaseModel):
    id = CharField(unique=True)
    user = ForeignKeyField(User, backref='resets')
    post = ForeignKeyField(Post, backref='resets')
    body = TextField()
    date = DateTimeField()
    real = BooleanField()
    permalink = CharField()
