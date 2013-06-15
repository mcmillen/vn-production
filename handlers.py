import datetime
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


MINERAL_SELL_MARKUP = 1.05


def is_current_user_admin():
  return users.is_current_user_admin()


def format_commas(amount):
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


def format_magnitude(amount):
  return '0'


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
  if isinstance(material, item_db.Ship):
    redirect('/ships')
  elif isinstance(material, item_db.Module):
    redirect('/modules')
  else:
    redirect('/materials')


@app.get('/materials')
def materials_page():
  materials = item_db.all_materials()
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
                  salvage=[],
                  ores=ore_data,
                  item_quantities=item_quantities,
                  formatter=format_commas)


# TODO: use item_db.all_materials() instead of passing it in.
def get_buy_price(materials, name):
  ore_name = name.split()[-1]
  if ore_name == 'Ochre':
    ore_name = 'Dark Ochre'
  if ore_name in ores.ORES:
    return ores.ORES[ore_name].calculate_buy_price(materials, name)
  materials = dict([(material.name, material) for material in materials])
  if name not in materials:
    return None
  return materials[name].buy_price


@app.post('/materials/compute')
def materials_compute():
  materials = item_db.all_materials()
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
    if buy_price is None:
      abort(400, 'Invalid material: %s' % name)
    value = buy_price * quantity
    total_value += value
    result.append((name,
                   buy_price,
                   format_commas(quantity),
                   format_commas(value)))
  # TODO: add sell_price to Item and use that instead of hard-coding here.
  return template('compute_materials.html',
                  materials=result,
                  buy_price=format_commas(total_value),
                  sell_price=format_commas(total_value * MINERAL_SELL_MARKUP))


@app.get('/ships')
def ships():
  item_quantities = get_item_quantities()
  ships = item_db.all_ships()
  def sort_key(ship):
    if item_quantities.get(ship.name) or ship.desired_quantity > 0:
      return ship.buy_price
    else:
      return ship.buy_price - 1000000000
  ships.sort(key=sort_key, reverse=True)
  return template('ships', ships=ships, formatter=format_commas,
                  item_quantities=item_quantities,
                  is_current_user_admin=is_current_user_admin())


@app.get('/modules')
def modules():
  item_quantities = get_item_quantities()
  modules = item_db.all_modules()
  return template('modules', modules=modules,
                  item_quantities=item_quantities,
                  is_current_user_admin=is_current_user_admin())


# TODO: generate the reports in a cron job and just have /assets
# return the latest.
@app.get('/assets/generate')
def assets():
  MASTER_WALLET_DIVISION = 1000
  item_quantities = get_item_quantities()
  master_wallet = get_wallet_details(MASTER_WALLET_DIVISION)
  escrow = get_market_escrow()
  total_cash = master_wallet + escrow

  result = '<tt><pre>'
  result += '%-21s %14s\n' % ('Master wallet', format_commas(master_wallet))
  result += '%-21s %14s\n' % ('Cash in market escrow', format_commas(escrow))
  result += '-' * 36
  result += '\n'
  result += '%-21s %14s\n\n' % ('Total cash', format_commas(total_cash))

  # TODO: separate data from display.
  result += 'Mineral quantities:\n'
  total_mineral_value = 0
  for item_name in sorted(item_quantities):
    material = item_db.get_material(item_name)
    if not material:
      continue
    quantity = item_quantities[item_name]
    # We use buy price instead of sell price here so that we don't
    # magically print ISK when we buy minerals in bulk.  We use sell
    # price for ships because that includes the value added by paying
    # for blueprints, manufacturing time, etc.
    value = material.buy_price * quantity
    total_mineral_value += value
    result += '%-21s %14s @ %-7.2f (%.1f%% of target)\n' % (
        item_name,
        format_commas(value),
        material.buy_price,
        100.0 * quantity / material.desired_quantity)
  result += '-' * 36
  result += '\n'
  result += '%-21s %14s\n\n' % (
    'Total mineral value', format_commas(total_mineral_value))

  # TODO: enable this once our materials actually include ore.
  # result += 'Ore quantities:\n'
  # total_ore_value = 0
  # for item_name in sorted(item_quantities):
  #   if item_db.get_material(item_name):
  #     continue
  #   buy_price = get_buy_price(item_db.all_materials(), item_name)
  #   if buy_price is None:
  #     continue
  #   quantity = item_quantities[item_name]
  #   value = buy_price * quantity
  #   total_ore_value += value
  #   result += '%-21s %14s @ %-7.2f\n' % (
  #       item_name, format_commas(value), buy_price)
  # result += '-' * 36
  # result += '\n'
  # result += '%-21s %14s\n\n' % (
  #   'Total ore value', format_commas(total_ore_value))

  result += 'Ship quantities:\n'
  total_ship_value = 0
  for item_name in sorted(item_quantities):
    ship = item_db.get_ship(item_name)
    if not ship:
      continue
    quantity = item_quantities[item_name]
    value = ship.sell_price * quantity
    total_ship_value += value
    result += '%-21s %14s @ %s each\n' % (
        '%s x%d' % (item_name, quantity),
        format_commas(value),
        format_commas(ship.sell_price))

  result += '-' * 36
  result += '\n'
  result += '%-21s %14s\n\n' % (
      'Total ship value', format_commas(total_ship_value))

  # TODO: include value of modules that are explicitly stocked by corp.

  # TODO: include line-items per item type in the report.
  report = models.AssetReport()
  report.cash = int(total_cash)
  report.mineral_value = int(total_mineral_value)
  report.ship_value = int(total_ship_value)
  report.put()

  result += '%-21s %14s' % ('Total assets', format_commas(report.total_assets))
  result += '</pre></tt>'

  return result

@app.get('/assets')
def assets_chart():
  reports = models.AssetReport().all().order('-creation_time').fetch(
    24 * 30 * 6)
  reports.reverse()
  for report in reports:
    delta = (report.creation_time - reports[0].creation_time).total_seconds()
    report.delta = delta
  return template('assets_chart.html', reports=reports)


@app.get('/login')
def login():
  redirect('/')


# TODO: put these data-fetching functions elsewhere.
def get_evelink_corp():
  api_key = models.ApiKey().all().get()
  api_key = (api_key.key_id, api_key.verification_code)
  api = evelink.appengine.AppEngineAPI(api_key=api_key)
  return evelink.corp.Corp(api=api)


def get_item_quantities():
  corp = get_evelink_corp()

  materials = item_db.all()
  material_item_types = dict((m.item_type, m.name) for m in materials)

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
  return item_quantities


def get_wallet_details(division):
  corp = get_evelink_corp()
  wallet_info = corp.wallet_info()
  return int(wallet_info[division]['balance'])


def get_market_escrow():
  corp = get_evelink_corp()
  total_escrow = 0
  orders = corp.orders()
  for order in orders.values():
    if order['type'] != 'buy':
      continue
    total_escrow += order['escrow']
  return total_escrow


bottle.run(app=app, server='gae')
