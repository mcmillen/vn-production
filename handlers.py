# TODO: change all prices to integer ISK-cents?

import json
import logging

import bottle
from bottle import *
from google.appengine.api import users

import evelink.appengine

import item_db
import models
import ores


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
  return template('add_material')


@app.get('/materials/edit/<name>')
def edit_material_page(name):
  if not is_current_user_admin():
    abort(403)
  material = item_db.get(name)
  if not material:
    abort(404)
  return template('edit_material', material=material)


@app.post('/materials/edit')
def edit_material_submit():
  if not is_current_user_admin():
    abort(403)
  name = request.forms.get('name')
  try:
    buy_price = float(request.forms.get('buy_price', ''))
  except ValueError:
    buy_price = None
  try:
    desired_quantity = int(request.forms.get('desired_quantity', ''))
  except ValueError:
    desired_quantity = 0
  material = item_db.get(name)
  if not material:
    abort(404)
  material.buy_price = buy_price
  material.desired_quantity = desired_quantity
  redirect('/materials')


@app.get('/materials')
def materials_page():
  materials = item_db.all_materials()
  salvage = item_db.all_salvage()
  item_quantities = get_item_quantities()

  ore_data = []
  for ore_name in sorted(ores.ORES):
    ore = ores.ORES[ore_name]
    variants = []
    for ore_variant in [ore.name, ore.name5, ore.name10]:
      buy_price = ore.calculate_buy_price(materials, ore_variant)
      variants.append((ore_variant, buy_price, buy_price / ore.volume))
    ore_data.append((ore_name, variants))
  if request.query.get('format') == 'json':
    return dict((material.name, material.to_dict(
          item_quantities.get(material.name, 0))) for material in materials)
  return template('materials',
                  is_current_user_admin=is_current_user_admin(),
                  materials=materials,
                  salvage=salvage,
                  ores=ore_data,
                  item_quantities=item_quantities)


def get_buy_price(materials, name):
  ore_name = name.split()[-1]
  if ore_name == 'Ochre':
    ore_name = 'Dark Ochre'
  if ore_name in ores.ORES:
    return ores.ORES[ore_name].calculate_buy_price(materials, name)
  materials = dict([(material.name, material) for material in materials])
  if name not in materials:
    abort(400, 'Invalid material: %s' % name)
  return materials[name].buy_price


@app.post('/materials/compute')
def materials_compute():
  materials = item_db.all()
  # List of (material name, buy price, quantity, value).
  result = []
  total_value = 0.0
  for name in sorted(request.forms):
    quantity = request.forms[name]
    if not quantity:
      continue
    try:
      quantity = int(quantity)
    except ValueError:
      abort(400, 'Invalid quantity of %s' % name)
    buy_price = get_buy_price(materials, name)
    value = buy_price * quantity
    total_value += value
    result.append((name,
                   buy_price,
                   format_number(quantity),
                   format_number(value)))
  return template('compute_materials.html',
                  materials=result,
                  buy_price=format_number(total_value),
                  sell_price=format_number(total_value * 1.05))


@app.get('/login')
def login():
  redirect('/')


# TODO: remove this, replace with datastore
production_item_types = {
  597: 'Punisher',
  603: 'Merlin',
  594: 'Incursus',
  11132: 'Minmatar Shuttle',
  24702: 'Hurricane',
  633: 'Celestis',
  657: 'Iteron Mark V',
  585: 'Slasher',
  24700: 'Myrmidon',
  16240: 'Catalyst',
  629: 'Rupture',
  627: 'Thorax',
  17478: 'Retriever',
  645: 'Dominix',
  16238: 'Cormorant',
  16242: 'Thrasher',
  587: 'Rifter',
  24698: 'Drake',
  16236: 'Coercer',
  632: 'Blackbird',
  620: 'Osprey',
  626: 'Vexor',
  16229: 'Brutix',
}


def get_item_quantities():
  materials = item_db.all()
  material_item_types = dict((m.item_type, m.name) for m in materials)

  api_key = models.ApiKey().all().get()
  api_key = (api_key.key_id, api_key.verification_code)
  api = evelink.appengine.AppEngineAPI(api_key=api_key)
  corp = evelink.corp.Corp(api=api)

  items = corp.assets().values()
  item_quantities = {}
  while items:
    item = items.pop()
    if 'contents' in item:
      items.extend(item['contents'])
    if item.get('location_flag') == 0:
      continue
    # TODO: add ore
    if item.get('item_type_id') in material_item_types:
      name = material_item_types[item.get('item_type_id')]
      item_quantities.setdefault(name, 0)
      item_quantities[name] += item['quantity']
    if item.get('item_type_id') in production_item_types:
      name = production_item_types[item.get('item_type_id')]
      item_quantities.setdefault(name, 0)
      item_quantities[name] += item['quantity']
  return item_quantities


@app.get('/experimental/itemquantities')
def gaetest():
  return json.dumps(get_item_quantities())


bottle.run(app=app, server='gae')
