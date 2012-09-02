import locale

import bottle
from bottle import *
from google.appengine.api import users

import models
import ores

# TODO: favicon.ico
# TODO: use templates instead of LOL HTML

app = Bottle()


def is_current_user_admin():
  return users.is_current_user_admin()


def format_number(amount):
  amount = int(amount)
  result = ''
  if amount == 0:
    return '0'
  while amount > 0:
    amount, mod = divmod(amount, 1000)
    if result:
      result = ',' + result
    result = '%03d' % mod + result
  result = result.lstrip('0')
  return result


@app.get('/')
def home():
  redirect('/materials')


@app.get('/materials/add')
def add_material_page():
    return """
<html>
<body>
<form action="/materials/edit" method="POST">
Name: <input type="text" name="name"><br>
Item type: <input type="text" name="item_type"><br>
Buy price: <input type="text" name="buy_price"><br>
Desired quantity: <input type="text" name="desired_quantity"><br>
<input type="Submit">
</form>
</body>
</html>
"""


@app.get('/materials/edit/<name>')
def edit_material_page(name):
  material = models.Material.all().filter('name =', name).get()
  if not material:
    return ''
  return """
<html>
<body>
<b>Editing %s</b>
<form action="/materials/edit" method="POST">
<input type="hidden" name="name" value="%s"><br>
Item type: <input type="text" name="item_type" value="%d"><br>
Buy price: <input type="text" name="buy_price" value="%.2f"><br>
Desired quantity: <input type="text" name="desired_quantity" value="%d"><br>
<input type="Submit">
</form>
</body>
</html>
""" % (name, name, material.item_type, material.buy_price or 0,
       material.desired_quantity or 0)


@app.post('/materials/edit')
def edit_material_submit():
  name = request.forms.get('name')
  item_type = int(request.forms.get('item_type'))
  try:
    buy_price = float(request.forms.get('buy_price', ''))
  except ValueError:
    buy_price = None
  try:
    desired_quantity = int(request.forms.get('desired_quantity', ''))
  except ValueError:
    desired_quantity = 0
  material = models.Material.all().filter('name =', name).get()
  if not material:
    material = models.Material()
  material.name = name
  material.item_type = item_type
  material.buy_price = buy_price
  material.desired_quantity = desired_quantity
  material.put()
  redirect('/materials')


@app.get('/materials')
def materials_page():
  materials = models.Material.all().order('item_type')
  result = '<html><body><font face="sans-serif"><form action="/materials/compute" method="post">'
  result += '<input type="submit" value="Compute Value">'
  result += '<table><tr>'
  result += '<tr><th>Material</th><th>Price</th>'
  result += '<th>Quantity</th>'
  if is_current_user_admin():
    result += '<th>Desired Quantity</th><th></th>'
  result += '</tr>'
  for material in materials:
    buy_price_str = 'N/A'
    if material.buy_price:
      buy_price_str = '%.2f' % material.buy_price
    result += '<tr><td>%s</td><td>%s</td>' % (
        material.name, buy_price_str)
    result += '<td><input type="text" name="%s" size="10"></td>' % (
        material.name)
    if is_current_user_admin():
      result += '<td>%s</td>' % material.desired_quantity
      result += '<td><a href="/materials/edit/%s">Edit</a></td>' % (
          material.name)
      result += '</tr>'
  for ore_name in sorted(ores.ORES):
    result += '<tr><td>&nbsp;</td></tr>'
    ore = ores.ORES[ore_name]
    for ore_variant in [ore.name, ore.name5, ore.name10]:
      buy_price = ore.calculate_buy_price(materials, ore_variant)
      result += '<tr><td>%s</td><td>%.2f (%.2f/m<sup>3</sup>)</td>' % (
          ore_variant, buy_price, buy_price / ore.volume)
      result += '<td><input type="text" name="%s" size="10"></td></tr>' % (
          ore_variant)
  result += '</table></form></font></body></html>'
  return result


def get_buy_price(materials, name):
  ore_name = name.split()[-1]
  if ore_name == 'Ochre':
    ore_name = 'Dark Ochre'
  if ore_name in ores.ORES:
    return ores.ORES[ore_name].calculate_buy_price(materials, name)
  materials = dict([(material.name, material) for material in materials])
  if name not in materials:
    # TODO: error?
    return 0.0
  return materials[name].buy_price


@app.post('/materials/compute')
def materials_compute():
  materials = models.Material.all().fetch(10000)
  result = '<html><body><font face="sans-serif">'
  total_value = 0.0
  for name in sorted(request.forms):
    quantity = request.forms[name]
    try:
      quantity = int(quantity)
    except ValueError:
      continue  # TODO: show the user an error
    buy_price = get_buy_price(materials, name)
    value = buy_price * quantity
    total_value += value
    result += '%s @ %.2f x %s: %s<br>' % (
        name, buy_price, format_number(quantity), format_number(value))
  result += '<br>Total value: <b>%s</b> ISK' % format_number(total_value)
  result += '<p>To buy this stuff from corp, the price is: '
  result += '<b>%s</b> ISK' % format_number(total_value * 1.05)
  return result


bottle.run(app=app, server='gae')
