from google.appengine.api import memcache
from google.appengine.api import urlfetch

import logging
import os
import re

import models


eve_marketdata_regex = re.compile(r'<\?xml version="1.0" encoding="utf-8"\?>'
    r'<eve><price id="(\d+)">([0-9.]+)</price></eve>')


# TODO: move the next couple functions to a utility file.
def create_cache_key(key):
  return '%s-%s' % (key, os.environ['CURRENT_VERSION_ID'])


def fetch_jita_price(item_type):
  url = 'http://eve-marketdata.com/api/item_prices_jita.xml?type_ids=%d' % (
      item_type)
  result = urlfetch.fetch(url)
  if result.status_code != 200:
    raise Exception("Can't fetch market data. :(")
  # WHOO I AM PARSING XML WITH REGEX
  match = eve_marketdata_regex.match(result.content)
  if not match:
    raise Exception('Trouble parsing eve-marketdata, tell Rethyl pls: %s' %
                    result.content)
  type_id = int(match.group(1))
  if item_type != type_id:
    raise Exception('Trouble parsing eve-marketdata, tell Rethyl pls: '
                    '%s != %s' % (item_type, type_id))
  price = float(match.group(2))
  logging.debug('eve-marketdata price for %d: %f' % (type_id, price))
  return price


class Item(object):
  def __init__(self, name, item_type, needed_materials=None):
    self._name = name
    self._item_type = item_type
    self._cache_key = create_cache_key('material-%s' % self._name)
    if needed_materials:
      self._needed_materials = needed_materials
    else:
      self._needed_materials = []

  def _fetch_data(self):
    result = memcache.get(self._cache_key)
    if result is not None:
      logging.debug('memcache hit for %s' % self._cache_key)
      return result
    logging.debug('memcache miss for %s' % self._cache_key)
    model = self._fetch_model()
    result = {'buy_price': model.buy_price,
              'desired_quantity': model.desired_quantity}
    memcache.set(self._cache_key, result, 60 * 60)
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


class Material(Item):
  pass


class Mineral(Material):
  def _calculate_buy_price(self):
    jita_price = fetch_jita_price(self.item_type)
    return jita_price * 0.93

  def _fetch_model(self):
    result = models.Material.all().filter('name =', self.name).get()
    if result:
      result.buy_price = self._calculate_buy_price()
      return result
    material = models.Material()
    material.name = self.name
    material.buy_price = self._calculate_buy_price()
    material.desired_quantity = 0
    material.put()
    return material


class Module(Item):
  pass


class Ship(Item):
  def production_materials(self, material_efficiency):
    result = {}
    for material, base_quantity in self._needed_materials.items():
      quantity = base_quantity * (1.0 + 0.1 / (material_efficiency + 1))
      quantity = int(round(quantity))
      result[material] = quantity
    return result

  @property
  def buy_price(self):
    material_efficiency = 5
    materials = self.production_materials(material_efficiency)
    total_cost = 0.0
    for material_id, quantity in materials.items():
      total_cost += quantity * get(material_id).buy_price
    return int(total_cost)

  @buy_price.setter
  def buy_price(self, value):
    pass  # Intentional no-op.  Buy price is computed from materials, per above.

  @property
  def sell_price(self):
    return int(self.buy_price * 1.1)


_ITEMS_BY_TYPE = {}

_materials = [
  Mineral('Tritanium', 34),
  Mineral('Pyerite', 35),
  Mineral('Mexallon', 36),
  Mineral('Isogen', 37),
  Mineral('Nocxium', 38),
  Mineral('Zydrine', 39),
  Mineral('Megacyte', 40),
  Mineral('Morphite', 11399)
]


_MATERIALS = dict((m.name, m) for m in _materials)
_ITEMS_BY_TYPE.update((m.item_type, m) for m in _materials)


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
_ITEMS_BY_TYPE.update((m.item_type, m) for m in _salvage)


# TODO: Make sure minerals taken from the newest DB dump.
# TODO: Add mining barges and industrials.
_ships = [
Ship('Abaddon', 24692, {34: 13351216, 35: 3337012, 36: 764192, 37: 208410, 38: 52180, 39: 8118, 40: 3922}),
Ship('Amarr Shuttle', 11134, {34: 2500}),
Ship('Apocalypse', 642, {34: 7577636, 35: 1894803, 36: 474674, 37: 118524, 38: 29622, 39: 7168, 40: 2683}),
Ship('Arbitrator', 628, {34: 245790, 35: 61844, 36: 18236, 37: 4184, 38: 1001, 39: 229, 40: 55}),
Ship('Armageddon', 643, {34: 4300840, 35: 1075896, 36: 271172, 37: 67405, 38: 16816, 39: 3952, 40: 1835}),
Ship('Atron', 608, {34: 1837, 35: 609, 36: 551, 37: 8, 39: 1}),
Ship('Augoror', 625, {34: 204846, 35: 51606, 36: 14903, 37: 3371, 38: 846, 39: 191, 40: 43}),
Ship('Badger', 648, {34: 24611, 35: 6541, 36: 2505, 37: 381, 38: 131, 39: 25}),
Ship('Badger Mark II', 649, {34: 53362, 35: 13792, 36: 5212, 37: 842, 38: 246, 39: 37, 40: 6}),
Ship('Bantam', 582, {34: 2706, 35: 725, 36: 40, 37: 46, 38: 2, 39: 2}),
Ship('Bellicose', 630, {34: 245798, 35: 61843, 36: 18748, 37: 4255, 38: 1017, 39: 223, 40: 53}),
Ship('Bestower', 1944, {34: 32811, 35: 8600, 36: 3830, 37: 509, 38: 163, 39: 37, 40: 2}),
Ship('Blackbird', 632, {34: 245798, 35: 61845, 36: 18234, 37: 4113, 38: 1002, 39: 229, 40: 53}),
Ship('Breacher', 598, {34: 15438, 35: 13477, 36: 2435, 37: 14, 39: 2}),
Ship('Brutix', 16229, {34: 1904428, 35: 421189, 36: 151522, 38: 8940, 39: 1648, 40: 857}),
Ship('Burst', 599, {34: 2662, 35: 283, 36: 462, 37: 1}),
Ship('Caldari Shuttle', 672, {34: 2500}),
Ship('Caracal', 621, {34: 307488, 35: 77204, 36: 25309, 37: 5284, 38: 1276, 39: 276, 40: 76}),
Ship('Catalyst', 16240, {34: 46806, 35: 13200, 36: 5784, 38: 242, 39: 41, 40: 24}),
Ship('Celestis', 633, {34: 245798, 35: 61846, 36: 17979, 37: 4043, 38: 1004, 39: 230, 40: 48}),
Ship('Coercer', 16236, {34: 50274, 35: 18300, 36: 4872, 37: 1023, 39: 89, 40: 18}),
Ship('Condor', 583, {34: 1999, 35: 1422, 36: 146, 37: 68}),
Ship('Cormorant', 16238, {34: 35328, 35: 10677, 36: 4596, 37: 963, 38: 299, 39: 96, 40: 8}),
#Ship('Covetor', 17476, {34: 2120040, 35: 645030, 36: 61280, 37: 17842, 38: 3972, 39: 1030, 40: 270}),
Ship('Crucifier', 2161, {34: 11600, 35: 9858, 36: 570, 38: 2, 39: 2, 40: 3}),
Ship('Cyclone', 16231, {34: 1623468, 35: 405001, 36: 97844, 37: 28977, 39: 1743, 40: 684}),
Ship('Dominix', 645, {34: 4300840, 35: 1075894, 36: 270905, 37: 67399, 38: 16790, 39: 3844, 40: 1407}),
Ship('Drake', 24698, {34: 2444312, 35: 612070, 36: 168645, 37: 17467, 38: 12364, 39: 3603, 40: 839}),
Ship('Executioner', 589, {34: 2752, 35: 2510, 36: 130, 37: 2}),
Ship('Exequror', 634, {34: 204846, 35: 51605, 36: 15158, 37: 3389, 38: 845, 39: 193, 40: 48}),
Ship('Ferox', 16227, {34: 1539680, 35: 387080, 36: 107188, 37: 11089, 38: 7941, 39: 2254, 40: 524}),
Ship('Gallente Shuttle', 11129, {34: 2500}),
Ship('Griffin', 584, {34: 11972, 35: 10371, 36: 1499, 38: 2, 39: 2}),
Ship('Harbinger', 24696, {34: 3493836, 35: 747201, 36: 187588, 37: 30449, 39: 2954, 40: 1170}),
Ship('Heron', 605, {34: 7485, 35: 4153, 36: 941, 37: 124, 38: 6}),
Ship('Hoarder', 651, {34: 32894, 35: 8671, 36: 3665, 37: 507, 38: 164, 39: 13, 40: 3}),
Ship('Hurricane', 24702, {34: 2630020, 35: 656103, 36: 158507, 37: 46949, 39: 2848, 40: 1108}),
Ship('Hyperion', 24690, {34: 12639108, 35: 3160111, 36: 759888, 37: 197299, 38: 49356, 39: 12135, 40: 3143}),
Ship('Imicus', 607, {34: 6629, 35: 5422, 36: 1295, 37: 1, 39: 1}),
Ship('Incursus', 594, {34: 11528, 35: 9882, 36: 3656, 37: 7}),
Ship('Inquisitor', 590, {34: 14494, 35: 11347, 36: 2566, 37: 3, 38: 4, 40: 1}),
Ship('Iteron', 650, {34: 20524, 35: 5527, 36: 1835, 37: 317, 38: 117, 39: 16, 40: 4}),
Ship('Iteron Mark II', 654, {34: 24638, 35: 6609, 36: 2323, 37: 381, 38: 133, 39: 16, 40: 2}),
Ship('Iteron Mark III', 655, {34: 28735, 35: 7634, 36: 3098, 37: 445, 38: 149, 39: 18, 40: 5}),
Ship('Iteron Mark IV', 656, {34: 41072, 35: 10720, 36: 4439, 37: 638, 38: 199, 39: 24, 40: 7}),
Ship('Iteron Mark V', 657, {34: 77944, 35: 19939, 36: 7788, 37: 1298, 38: 362, 39: 62, 40: 10}),
Ship('Kestrel', 602, {34: 14852, 36: 2579, 37: 861, 38: 1, 39: 1}),
Ship('Maelstrom', 24694, {34: 10617760, 35: 2654764, 36: 663953, 37: 165851, 38: 41419, 39: 9867, 40: 2275}),
Ship('Magnate', 29248, {34: 12456, 35: 888, 36: 599, 37: 52, 39: 6, 40: 2}),
Ship('Maller', 624, {34: 593884, 35: 149060, 36: 39028, 37: 9357, 38: 2306, 39: 576, 40: 145}),
Ship('Mammoth', 652, {34: 65650, 35: 16867, 36: 6505, 37: 1102, 38: 301, 39: 50, 40: 8}),
Ship('Maulus', 609, {34: 13748, 35: 11099, 36: 1831, 37: 8, 39: 2}),
Ship('Megathron', 641, {34: 7372840, 35: 1843894, 36: 462130, 37: 115316, 38: 28787, 39: 6830, 40: 2103}),
Ship('Merlin', 603, {34: 18964, 35: 8444, 36: 2814, 37: 531, 38: 2, 39: 2, 40: 2}),
Ship('Minmatar Shuttle', 11132, {34: 2500}),
Ship('Moa', 623, {34: 552920, 35: 138810, 36: 35916, 37: 8718, 38: 2148, 39: 541, 40: 160}),
Ship('Myrmidon', 24700, {34: 2885176, 35: 642378, 36: 215466, 38: 13483, 39: 2523, 40: 1236}),
Ship('Naga', 4306, {34: 3666468, 35: 918105, 36: 252968, 37: 26201, 38: 18546, 39: 5405, 40: 1259}),
Ship('Navitas', 592, {34: 2730, 35: 214, 36: 303, 37: 4, 38: 2, 39: 2}),
Ship('Omen', 2006, {34: 307478, 35: 77204, 36: 25566, 37: 5350, 38: 1276, 39: 276, 40: 70}),
Ship('Oracle', 4302, {34: 5240754, 35: 1120802, 36: 281382, 37: 45674, 39: 4431, 40: 1755}),
Ship('Osprey', 620, {34: 204436, 35: 51606, 36: 12837, 37: 3200, 38: 840, 39: 192, 40: 50}),
Ship('Probe', 586, {34: 8234, 35: 2448, 36: 1372, 37: 99, 38: 31}),
#Ship('Procurer', 17480, {34: 233476, 35: 14703, 36: 6002, 37: 509, 38: 49, 39: 29, 40: 9}),
Ship('Prophecy', 16233, {34: 2280140, 35: 489013, 36: 125053, 37: 20021, 39: 1973, 40: 784}),
Ship('Punisher', 597, {34: 20518, 35: 5520, 36: 2654, 37: 361, 38: 79, 39: 15}),
Ship('Raven', 638, {34: 7577632, 35: 1894802, 36: 474675, 37: 118519, 38: 29595, 39: 7060, 40: 2254}),
#Ship('Retriever', 17478, {34: 512884, 35: 54279, 36: 11093, 37: 7131, 38: 1574, 39: 404, 40: 78}),
Ship('Rifter', 587, {34: 20524, 35: 5529, 36: 1841, 37: 317, 38: 118, 39: 13, 40: 1}),
Ship('Rokh', 24688, {34: 10783548, 35: 3172713, 36: 666484, 37: 169034, 38: 48623, 39: 12392, 40: 3029}),
Ship('Rupture', 629, {34: 450484, 35: 112774, 36: 29243, 37: 7053, 38: 1747, 39: 454, 40: 172}),
Ship('Scorpion', 640, {34: 5324832, 35: 1131610, 36: 303530, 37: 83100, 38: 18013, 39: 4022, 40: 1677}),
Ship('Scythe', 631, {34: 204838, 35: 51606, 36: 14134, 37: 3305, 38: 844, 39: 189, 40: 44}),
Ship('Sigil', 19744, {34: 32811, 35: 8600, 36: 3574, 37: 509, 38: 167, 39: 36, 40: 3}),
Ship('Slasher', 585, {40: 1, 34: 1854, 35: 918, 36: 218, 37: 10}),
Ship('Stabber', 622, {34: 307484, 35: 77203, 36: 25832, 37: 5350, 38: 1280, 39: 269, 40: 61}),
Ship('Talos', 4308, {34: 4327764, 35: 963567, 36: 323199, 38: 20225, 39: 3785, 40: 1854}),
Ship('Tempest', 639, {34: 7372852, 35: 1843893, 36: 462643, 37: 115378, 38: 28778, 39: 6794, 40: 1957}),
Ship('Thorax', 627, {34: 524216, 35: 131210, 36: 34124, 37: 8270, 38: 2035, 39: 510, 40: 130}),
Ship('Thrasher', 16242, {34: 43116, 35: 10335, 36: 3579, 37: 1581, 39: 81, 40: 12}),
Ship('Tormentor', 591, {34: 2229, 35: 218, 36: 556, 37: 2}),
Ship('Tornado', 4310, {34: 3945030, 35: 984155, 36: 237761, 37: 70424, 39: 4272, 40: 1662}),
Ship('Tristan', 593, {34: 20974, 35: 5661, 36: 2654, 37: 358, 38: 74, 39: 9, 40: 1}),
Ship('Typhoon', 644, {34: 5120040, 35: 1280694, 36: 322370, 37: 80265, 38: 19995, 39: 4678, 40: 1722}),
Ship('Vexor', 626, {34: 307734, 35: 77202, 36: 26179, 37: 5349, 38: 1276, 39: 261, 40: 53}),
Ship('Vigil', 3766, {34: 12786, 35: 3606, 36: 2130, 37: 222, 38: 34, 39: 2}),
Ship('Wreathe', 653, {34: 20522, 35: 5518, 36: 2192, 37: 318, 38: 119, 39: 32}),
]


_SHIPS = dict((m.name, m) for m in _ships)
_ITEMS_BY_TYPE.update((m.item_type, m) for m in _ships)


_modules = [
    Module("Small F-S9 Regolith Shield Induction", 8521),
    Module("Medium F-S9 Regolith Shield Induction", 8517),
    Module("Medium Azeotropic Ward Salubrity I", 8433),
    Module("Large F-S9 Regolith Shield Induction", 8529),
    Module("425mm Medium 'Scout' Autocannon I", 9135),
    Module("425mm Medium Prototype Automatic Cannon", 9141),
    Module("720mm 'Scout' Artillery I", 9451),
    Module("720mm Prototype Siege Cannon", 9457),
    Module("Fleeting Propulsion Inhibitor I", 4027),
    Module("X5 Prototype Engine Enervator", 4025),
    Module("Faint Warp Disruptor I", 5403),
    Module("J5 Prototype Warp Disruptor I", 5399),
    Module("Faint Epsilon Warp Scrambler I", 5443),
    Module("J5b Phased Prototype Warp Scrambler I", 5439),
    Module("Local Hull Conversion Nanofiber Structure I", 5561),
    Module("Limited Adaptive Invulnerability Field I", 9632),
    Module("Limited 'Anointed' EM Ward Field", 9622),
    Module("Limited Thermic Dissipation Field I", 9660),
    Module("Counterbalanced Weapon Mounts I", 5933),
    Module("Magnetic Field Stabilizer I", 9944),
    Module("Republic Fleet Phased Plasma M", 21922 ),
    Module("Republic Fleet EMP M", 21896),
    Module("250mm Prototype Gauss Gun", 7367),
    Module("Experimental 1MN Afterburner I", 6003),
    Module("Limited 1MN Microwarpdrive I", 5973),
    Module("Experimental 10MN Afterburner I", 6005),
    Module("Experimental 10MN Microwarpdrive I", 5975),
    Module("F-23 Reciprocal Sensor Cluster Link", 5279),
    Module("Fourier Transform Tracking Program", 6325),
]


_MODULES = dict((m.name, m) for m in _modules)
_ITEMS_BY_TYPE.update((m.item_type, m) for m in _modules)


# TODO: make a more general function for querying items.
def all_materials():
  return sorted(_MATERIALS.values(), key=lambda m: m.name)


def get_material(name):
  return _MATERIALS.get(name)


def all_salvage():
  return sorted(_SALVAGE.values(), key=lambda m: m.name)


def get_salvage(name):
  return _SALVAGE.get(name)


def all_ships():
  return sorted(_SHIPS.values(), key=lambda m: m.name)


def get_ship(name):
  return _SHIPS.get(name)


def all_modules():
  return sorted(_MODULES.values(), key=lambda m: m.name)


def get_module(name):
  return _MODULES.get(name)


def get(name):
  if isinstance(name, int):
    return _ITEMS_BY_TYPE.get(name)
  else:
    return get_material(name) or get_salvage(name) or get_ship(name) or get_module(name) or None


def all():
  return all_materials() + all_salvage() + all_ships() + all_modules()
