from google.appengine.ext import db

import json


class Material(db.Model):
  name = db.StringProperty()
  buy_price = db.FloatProperty()
  desired_quantity = db.IntegerProperty()


class ApiKey(db.Model):
  key_id = db.IntegerProperty()
  verification_code = db.StringProperty()


class AssetReport(db.Model):
  creation_time = db.DateTimeProperty(auto_now_add=True)
  cash = db.IntegerProperty()
  mineral_value = db.IntegerProperty()
  ship_value = db.IntegerProperty()

  @property
  def total_assets(self):
    return self.cash + self.mineral_value + self.ship_value

