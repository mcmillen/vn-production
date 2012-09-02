from google.appengine.ext import db

class Material(db.Model):
  name = db.StringProperty()
  item_type = db.IntegerProperty()
  buy_price = db.FloatProperty()
  desired_quantity = db.IntegerProperty()
