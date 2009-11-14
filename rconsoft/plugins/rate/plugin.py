# Read LICENSE for licensing details.

import os

from twisted.internet import reactor

from rconsoft.plugins import Plugin
from rconsoft import rcon_client, command_handler
from rconsoft.config import cget, has_access
from rconsoft.command import get_dispatcher, command, shell_parse

#------------------------------
class RatePlugin(Plugin):
  """Supported commands: rate, rateteam"""
  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
    
    self.performing_lo3 = False
    
    command_handler.event.connect(get_dispatcher(self))

  #==============================
  @command('rate', 'rateteam')
  def on_command(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True
    
    # No reason to do anything if we're silent.
    if silent:
      return True

    players = None
    
    if command == 'rate':
      # If they passed params, then get the players by their names
      parsed_params = shell_parse(params)
      if parsed_params:
        players = rcon_client.get_players(names=parsed_params)
      else: # Otherwise, just use all the players
        players = rcon_client.get_players()
    elif command == 'rateteam' and params:
      # Get the correct team name based on what they passed.
      team = None
      if params == 'c' or params == 'ct':
        team = 'CT'
      elif params == 't':
        team = 'TERRORIST'
      # If we have a team, get the players on that team.
      if team:
        players = rcon_client.find_players('team', team)
    
    if players:
      for player in players:
        player = players[player]
        rcon_client.hsay('', '%s - rate[%s] updaterate[%s]' % (player['name'], player['rate'], player['cl_updaterate']))

    # Keep processing other plugins.
    return True


