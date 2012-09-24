from google.appengine.api import memcache

import logging
import models


class Material(object):
  def __init__(self, name, item_type):
    self._name = name
    self._item_type = item_type
    self._cache_key = 'material-%s' % self._name

  def _fetch_data(self):
    result = memcache.get(self._cache_key)
    if result:
      logging.debug('memcache hit for %s' % self._cache_key)
      return result
    logging.debug('memcache miss for %s' % self._cache_key)
    model = self._fetch_model()
    result = {'buy_price': model.buy_price,
              'desired_quantity': model.desired_quantity}
    memcache.set(self._cache_key, result, 60 * 60 * 24)
    return result

  def _fetch_model(self):
    result = models.Material.all().filter('name =', self.name).get()
    if result:
      return result
    material = models.Material()
    material.name = self.name
    material.buy_price = 0.0
    material.desired_quantity = 0
    material.put()
    return material

  def to_dict(self, current_quantity=None):
    return {'name': self.name,
            'item_type': self.item_type,
            'buy_price': self.buy_price,
            'desired_quantity': self.desired_quantity,
            'current_quantity': current_quantity}

  @property
  def name(self):
    return self._name

  @property
  def item_type(self):
    return self._item_type

  @property
  def buy_price(self):  
    return self._fetch_data().get('buy_price', 0)

  @buy_price.setter
  def buy_price(self, value):
    if value == self.buy_price:
      return
    memcache.delete(self._cache_key)
    model = self._fetch_model()
    model.buy_price = value
    model.put()

  @property
  def desired_quantity(self):
    return self._fetch_data().get('desired_quantity', 0)

  @desired_quantity.setter
  def desired_quantity(self, value):
    if value == self.desired_quantity:
      return
    memcache.delete(self._cache_key)
    model = self._fetch_model()
    model.desired_quantity = value
    model.put()


_materials = [
  Material('Tritanium', 34),
  Material('Pyerite', 35),
  Material('Mexallon', 36),
  Material('Isogen', 37),
  Material('Nocxium', 38),
  Material('Zydrine', 39),
  Material('Megacyte', 40),
  Material('Morphite', 11399)
]


_MATERIALS = dict((m.name, m) for m in _materials)


_salvage = [
  Material('Alloyed Tritanium Bar', 25595),
  Material('Armor Plates', 25605),
  Material('Broken Drone Transceiver', 25596),
  Material('Burned Logic Circuit', 25600),
  Material('Charred Micro Circuit', 25599),
  Material('Conductive Polymer', 25604),
  Material('Contaminated Lorentz Fluid', 25591),
  Material('Contaminated Nanite Compound', 25590),
  Material('Damaged Artificial Neural Network', 25597),
  Material('Defective Current Pump', 25592),
  Material('Fried Interface Circuit', 25601),
  Material('Malfunctioning Shield Emitter', 25589),
  Material('Melted Capacitor Console', 25603),
  Material('Scorched Telemetry Processor', 25588),
  Material('Smashed Trigger Unit', 25593),
  Material('Tangled Power Conduit', 25594),
  Material('Thruster Console', 25602),
  Material('Tripped Power Circuit', 25598),
  Material('Ward Console', 25606),
]


_SALVAGE = dict((m.name, m) for m in _salvage)


def all_materials():
  return sorted(_MATERIALS.values(), key=lambda m: m.item_type)


def get_material(name):
  return _MATERIALS.get(name)


def all_salvage():
  return sorted(_SALVAGE.values(), key=lambda m: m.name)


def get_salvage(name):
  return _SALVAGE.get(name)


def get(name):
  return get_material(name) or get_salvage(name) or None


def all():
  return all_materials() + all_salvage()
