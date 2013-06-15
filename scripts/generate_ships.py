import collections
import json
import os
import pprint
import sys


SHIP_NAMES = [
    'Abaddon',
    'Algos',
    'Amarr Shuttle',
    'Apocalypse',
    'Arbitrator',
    'Armageddon',
    'Atron',
    'Augoror',
    'Badger',
    'Badger Mark II',
    'Bantam',
    'Bellicose',
    'Bestower',
    'Blackbird',
    'Breacher',
    'Brutix',
    'Burst',
    'Caldari Shuttle',
    'Caracal',
    'Catalyst',
    'Celestis',
    'Coercer',
    'Condor',
    'Corax',
    'Cormorant',
    'Covetor',
    'Crucifier',
    'Cyclone',
    'Dominix',
    'Dragoon',
    'Drake',
    'Executioner',
    'Exequror',
    'Ferox',
    'Gallente Shuttle',
    'Griffin',
    'Harbinger',
    'Heron',
    'Hoarder',
    'Hurricane',
    'Hyperion',
    'Imicus',
    'Incursus',
    'Inquisitor',
    'Iteron',
    'Iteron Mark II',
    'Iteron Mark III',
    'Iteron Mark IV',
    'Iteron Mark V',
    'Kestrel',
    'Maelstrom',
    'Magnate',
    'Maller',
    'Mammoth',
    'Maulus',
    'Megathron',
    'Merlin',
    'Minmatar Shuttle',
    'Moa',
    'Myrmidon',
    'Naga',
    'Navitas',
    'Omen',
    'Oracle',
    'Osprey',
    'Probe',
    'Procurer',
    'Prophecy',
    'Punisher',
    'Raven',
    'Retriever',
    'Rifter',
    'Rokh',
    'Rupture',
    'Scorpion',
    'Scythe',
    'Sigil',
    'Slasher',
    'Stabber',
    'Talos',
    'Talwar',
    'Tempest',
    'Thorax',
    'Thrasher',
    'Tormentor',
    'Tornado',
    'Tristan',
    'Typhoon',
    'Venture',
    'Vexor',
    'Vigil',
    'Wreathe',
]


def main(args):
  if len(args) != 2:
    print 'Usage: generate_ships.py invTypes.json invTypeMaterials.json'
    return 1
  inv_types = json.load(open(os.path.expanduser(args[0])))
  inv_type_materials = json.load(open(os.path.expanduser(args[1])))

  type_id_to_name = {}
  name_to_type_id = {}
  type_id_to_materials = collections.defaultdict(dict)
  for item in inv_types['data']:
    if item.get('typeName') not in SHIP_NAMES:
      continue
    assert item['typeName'] not in name_to_type_id
    assert item['typeID'] not in type_id_to_name
    type_id_to_name[item['typeID']] = item['typeName']
    name_to_type_id[item['typeName']] = item['typeID']

  for item in inv_type_materials['data']:
    if item['typeID'] not in type_id_to_name:
      continue
    ship_id = item['typeID']
    material_id = item['materialTypeID']
    quantity = item['quantity']
    type_id_to_materials[ship_id][material_id] = quantity

  for ship in SHIP_NAMES:
    print "    Ship('%s', %d, %s)," % (
      ship, name_to_type_id[ship], type_id_to_materials[name_to_type_id[ship]])


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))

