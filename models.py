from google.appengine.ext import db

import json

class Material(db.Model):
  name = db.StringProperty()
  item_type = db.IntegerProperty()
  buy_price = db.FloatProperty()
  desired_quantity = db.IntegerProperty()

  def ToDict(self, current_quantity=None):
    return {'name': self.name,
            'item_type': self.item_type,
            'buy_price': self.buy_price,
            'desired_quantity': self.desired_quantity,
            'current_quantity': current_quantity}


class ApiKey(db.Model):
  key_id = db.IntegerProperty()
  verification_code = db.StringProperty()

