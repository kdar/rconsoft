# Read LICENSE for licensing details.

"""A config module for RconSoft."""

import os
import sys
from configobj import ConfigObj, Section

__all__ = ['config', 'has_access', 'INSTALLDIR', 'cget']

INSTALLDIR = os.path.dirname(sys.modules[__name__].__file__)

#==============================
def mergeif(self, indict):
  """
  A recursive update - useful for merging config files. Will only merge
  if the values in indict are not in this config already.
  """
  for key, val in indict.items():
    if (key in self and isinstance(self[key], dict) and isinstance(val, dict)):
      self[key].mergeif(val)
    elif key not in self:
      self[key] = val
Section.mergeif = mergeif

#++++++++++++++++++++++++++++++

config = ConfigObj(os.path.join(INSTALLDIR, 'rconsoft.conf'))

#==============================
def cget(first_arg, *args, **kwargs):
  """A nice helper function to retrieve a configuration option. If the option doesn't
  exist, it will return whatever you pass as default or None. This will NOT put the values
  in the config object (which is intended).
  
  Example: cget('global', 'plugins', default=['core'])
  """
  try:
    d = config[first_arg]
    for arg in args:
      d = d[arg]
    return d
  except KeyError, e:
    return kwargs.get('default', None)

#++++++++++++++++++++++++++++++

ACCESS_LEVELS = [
  'master',
  'admin',
  'user',
  'guest'
]

#==============================
def has_access(uniqueid, access):
  level = ACCESS_LEVELS.index(access)
  for user in config['users']:
    entry = config['users'][user]
    if entry['uniqueid'] == uniqueid and ACCESS_LEVELS.index(entry['access']) <= level:
      return True
  return False
