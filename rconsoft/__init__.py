# Read LICENSE for licensing details.

import logging

import rconsoft
from rconsoft.command import CommandHandler
from rconsoft.rcon.client import RconClient
from rconsoft.rcon.receiver import RconReceiver

__all__ = ['rcon_client', 'command_handler', 'rcon_receiver', 'irc_client']

#==============================
def __figure_version():
  try:
    from pkg_resources import require
    import os
    # NOTE: this only works when the package is either installed,
    # or has an .egg-info directory present (i.e. wont work with raw
    # SVN checkout)
    info = require(rconsoft.__name__)[0]
    if os.path.dirname(os.path.dirname(__file__)) == info.location:
      return info.version
    else:
      return '(not installed)'
  except:
    return '(not installed)'
        
__version__ = __figure_version()

command_handler = CommandHandler()
rcon_client = RconClient()
rcon_receiver = RconReceiver()