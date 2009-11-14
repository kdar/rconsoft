# Read LICENSE for licensing details.

import urllib
import logging
from xml.etree import ElementTree as etree

from twisted.internet import reactor

from rconsoft.plugins import Plugin
from rconsoft import rcon_client, rcon_receiver, command_handler
from rconsoft.config import cget, has_access
from rconsoft.command import get_dispatcher, command, shell_parse

URL = 'http://steamid.esportsea.com/?action=search&type=single&key=steam_id&query=%s&output=xml&version=extended'

log = logging.getLogger('general')
log_detail = logging.getLogger('detail')

#<results> 
#  <query_info> 
#    <query_time> 0.001</query_time> 
#    <total_results>1</total_results> 
#  </query_info> 
#  <result> 
#    <league_player_id>705519</league_player_id> 
#    <player_alias>masada</player_alias> 
#    <player_name_first>kevin</player_name_first> 
#    <player_name_last>d</player_name_last> 
#    <player_steam_id>0:1:7114301</player_steam_id> 
#    <league_team_id></league_team_id> 
#    <team_game>cs</team_game> 
#    <team_league>cal</team_league> 
#    <team_division>im</team_division> 
#    <team_location>central</team_location> 
#    <team_name>Failsport</team_name> 
#    <team_tag>failsport</team_tag> 
#    <team_irc>#failsport</team_irc> 
#    <team_website>http://failsport.com</team_website> 
#    <server_alias></server_alias> 
#    <league_division_id>CSIM</league_division_id> 
#    <team_record> 
#      <wins>0</wins> 
#      <losses>0</losses> 
#      <ties>0</ties> 
#    </team_record> 
#  </result> 
#</results> 

#------------------------------
class IDLookupPlugin(Plugin):
  """Supported commands: id, idteam"""
  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
    
    command_handler.event.connect(get_dispatcher(self))
  
  #==============================
  @command('id', 'idteam')
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
    
    if command == 'id':
      # If they passed params, then get the players by their names
      parsed_commands = shell_parse(params)
      if parsed_commands:
        players = rcon_client.get_players(names=parsed_commands)
      else: # Otherwise, just use all the players
        players = rcon_client.get_players()
    elif command == 'idteam' and params:
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
      reactor.callInThread(self.display_players, players)
    
    # Keep processing other plugins.
    return True
  
  #==============================
  def on_rcon_event(self, event, data, **kwargs):
    if event == 'user_entered':
      if 'uniqueid' in data:
        reactor.callInThread(self.display_id, data['uniqueid'])
  
  #==============================
  def display_players(self, players):
    slist = []
    for player in players:
      player = players[player]
      info = self.lookup_id(player['uniqueid'])
      log.debug(player)
      info['ingame_name'] = player['name']
      info['ingame_team'] = player['team']
      slist.append(info)
      
    if slist:
      def player_sort(x, y):
        if 'team_name' not in x or 'team_name' not in y:
          return cmp(x['ingame_team'], y['ingame_team'])
        return cmp(x['team_name'], y['team_name'])
      slist.sort(player_sort)
      
      for entry in slist:
        self.display_info(entry)
  
  #==============================
  def display_id(self, uniqueid):
    """Retrieves and displays a single user's league status."""
    
    info = self.lookup_id(uniqueid)
    info['ingame_name'] = rcon_client.players[uniqueid]['name']
    self.display_info(info)
      
  #==============================
  def display_info(self, info):
    """A function to display information about a player's league status in game."""
    
    if 'team_name' in info:
      league = '%(team_game)s-%(team_league)s-%(team_division)s' % info
      record = '%(wins)s-%(losses)s-%(ties)s' % info['team_record']
      rcon_client.hsay('', '%s in %s(%s, %s) | %s' % (info['player_alias'], info['team_name'], league, record, info['ingame_name']))
    else:
      rcon_client.hsay('', '%s is not in any leagues' % info['ingame_name'])
  
  #==============================
  def lookup_id(self, uniqueid):
    """Looks up the id of a person and returns a dictionary of their league information.
    If no league is found, it returns an empty dictionary."""
    
    # Strip off STEAM_ in the uniqueid since the steamid lookup doesn't want it.
    uniqueid = uniqueid.replace('STEAM_', '')
    dom = etree.parse(urllib.urlopen(URL % uniqueid))
    data = self.simple_xml_parse(dom.getroot())
    
    if data and data['query_info']['total_results'] != '0':
      return data['result']
    else:
      return {}
    
  #==============================
  def simple_xml_parse(self, dom):
    """Takes a lxml Element and returns a dictionary of itself
    and all of its children and text nodes."""
    
    d = {}
    for child in dom.getchildren():
      if child.getchildren():
        d[child.tag] = self.simple_xml_parse(child)
      else:
        d[child.tag] = child.text    
    return d
