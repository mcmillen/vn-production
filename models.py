from google.appengine.ext import db

import json


class Material(db.Model):
  name = db.StringProperty()
  buy_price = db.FloatProperty()
  desired_quantity = db.IntegerProperty()


class ApiKey(db.Model):
  key_id = db.IntegerProperty()
  verification_code = db.StringProperty()
