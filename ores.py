class Ore(object):
  def __init__(self, name, name5, name10, volume, batch_size, refines):
    self.name = name
    self.name5 = name5
    self.name10 = name10
    self.volume = volume
    self.batch_size = batch_size
    self.refines = refines

  def calculate_buy_price(self, materials, name=''):
    price_per_batch = 0.0
    materials = dict([(material.name, material) for material in materials])
    for mineral_name, quantity in self.refines.items():
      # TODO: complain if one of the minerals doesn't exist yet.
      mineral = materials.get(mineral_name)
      if mineral:
        price_per_batch += quantity * mineral.buy_price
    # We shouldn't lose money on this assuming that refiners have 5/4/3.
    result = 0.9 * price_per_batch / self.batch_size
    if name == self.name10:
      return 1.1 * result
    elif name == self.name5:
      return 1.05 * result
    else:
      return result


ORES = {
  'Arkonor': Ore('Arkonor',
                 'Crimson Arkonor',
                 'Prime Arkonor',
                 16,
                 200,
                 {'Megacyte': 333,
                  'Tritanium': 10000,
                  'Zydrine': 166}),
  'Bistot': Ore('Bistot',
                'Triclinic Bistot',
                'Monoclinic Bistot',
                16,
                200,
                {'Megacyte': 170,
                 'Pyerite': 12000,
                 'Zydrine': 341}),
  'Crokite': Ore('Crokite',
                 'Sharp Crokite',
                 'Crystalline Crokite',
                 16,
                 250,
                 {'Nocxium': 331,
                  'Tritanium': 38000,
                  'Zydrine': 663}),
  'Dark Ochre': Ore('Dark Ochre',
                    'Onyx Dark Ochre',
                    'Obsidian Dark Ochre',
                    8,
                    400,
                    {'Nocxium': 500,
                     'Tritanium': 25500,
                     'Zydrine': 250}),
  'Gneiss': Ore('Gneiss',
                'Iridescent Gneiss',
                'Primatic Gneiss',
                5,
                400,
                {'Isogen': 700,
                 'Mexallon': 3700,
                 'Tritanium': 3700,
                 'Zydrine': 137}),
  'Hedbergite': Ore('Hedbergite',
                    'Vitric Hedbergite',
                    'Glazed Hedbergite',
                    3,
                    500,
                    {'Isogen': 708,
                     'Nocxium': 354,
                     'Pyerite': 290,
                     'Zydrine': 32}),
  'Hemorphite': Ore('Hemorphite',
                    'Vivid Hemorphite',
                    'Radiant Hemorphite',
                    3,
                    500,
                    {'Isogen': 212,
                     'Mexallon': 60,
                     'Nocxium': 424,
                     'Pyerite': 260,
                     'Tritanium': 650,
                     'Zydrine': 28}),
  'Jaspet': Ore('Jaspet',
                'Pure Jaspet',
                'Pristine Jaspet',
                2,
                500,
                {'Mexallon': 518,
                 'Nocxium': 259,
                 'Pyerite': 259,
                 'Tritanium': 259,
                 'Zydrine': 8}),
  'Kernite': Ore('Kernite',
                 'Luminous Kernite',
                 'Fiery Kernite',
                 1.2,
                 400,
                 {'Isogen': 386,
                  'Mexallon': 773,
                  'Tritanium': 386}),
  'Mercoxit': Ore('Mercoxit',
                  'Magma Mercoxit',
                  'Vitreous Mercoxit',
                  40,
                  530,
                  {'Morphite': 250}),
  'Omber': Ore('Omber',
               'Silvery Omber',
               'Golden Omber',
               0.6,
               500,
               {'Isogen': 307,
                'Pyerite': 123,
                'Tritanium': 307}),
  'Plagioclase': Ore('Plagioclase',
                     'Azure Plagioclase',
                     'Rich Plagioclase',
                     0.35,
                     333,
                     {'Mexallon': 256,
                      'Pyerite': 512,
                      'Tritanium': 256}),
  'Pyroxeres': Ore('Pyroxeres',
                   'Solid Pyroxeres',
                   'Viscous Pyroxeres',
                   0.3,
                   333,
                   {'Mexallon': 120,
                    'Nocxium': 11,
                    'Pyerite': 59,
                    'Tritanium': 844}),
  'Scordite': Ore('Scordite',
                  'Condensed Scordite',
                  'Massive Scordite',
                  0.15,
                  333,
                  {'Pyerite': 416,
                   'Tritanium': 833}),
  'Spodumain': Ore('Spodumain',
                   'Bright Spodumain',
                   'Gleaming Spodumain',
                   16,
                   250,
                   {'Megacyte': 140,
                    'Pyerite': 9000,
                    'Tritanium': 71000}),
  'Veldspar': Ore('Veldspar',
                  'Concentrated Veldspar',
                  'Dense Veldspar',
                  0.1,
                  333,
                  {'Tritanium': 1000})
}
