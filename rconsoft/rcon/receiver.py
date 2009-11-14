# Read LICENSE for licensing details.
"""The Rcon receiver."""

import re
import logging

from twisted.internet.protocol import DatagramProtocol

from rconsoft.dispatch.dispatcher import Signal
from rconsoft.config import config

log = logging.getLogger('general')
log_detail = logging.getLogger('detail')

#------------------------------
class EventError(Exception):
  """Is thrown when something involving events errors."""
  pass

#------------------------------
class RconReceiver(DatagramProtocol):
  #==============================
  def __init__(self):
    self._init_signals()
    
    self.events = {
      'user_connected': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" connected, address "(?P<ip>.*?):(?P<port>.*?)"')
      },
      'user_disconnected': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" disconnected') 
      },
      'user_validated': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" STEAM USERID validated')
      },
      'user_entered': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" entered the game')
      },
      'user_joined_team': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><.*?>" joined team "(?P<team>.*?)"')
      },
      'user_say': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" say(_(?P<to>.*?))? "(?P<message>.*)"( \((?P<status>.*?)\))?')
      },
      'user_changed_name': {
        'regex': re.compile(r'^"(?P<old_name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><.*?>" changed name to "(?P<name>.*?)"')
      },
      'user_triggered': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" triggered "(?P<event>.*?)"')
      },
      'world_triggered': {
        'regex': re.compile(r'^World triggered "(?P<event>.*?)"( \(CT "(?P<ct_score>\d+)"\) \(T "(?P<t_score>\d+)"\))?')
      },
      'server_say': {
        'regex': re.compile(r'^Server say "(?P<message>.*?)"')
      },
      'server_cvar': {
        'regex': re.compile(r'^Server cvar "(?P<cvar>.*?)" = "(?P<value>.*?)"')
      },
      'team_scored': {
        'regex': re.compile(r'^Team "(?P<team>.*?)" scored "(?P<score>.*?)" with "(?P<players>.*?)" players')
      },
      'team_triggered': {
        'regex': re.compile(r'^Team "(?P<team>.*?)" triggered "(?P<event>.*?)"( \(CT "(?P<ct_score>\d+)"\) \(T "(?P<t_score>\d+)"\))?')
      },
      'rcon_command': {
        'regex': re.compile(r'^Rcon: \"rcon (?P<challenge>\d+) \"(?P<password>.*?)\" (?P<command>.*?)\" from \"(?P<ip>.*?):(?P<port>.*?)\"')
      }
    }
    
  #==============================
  def _init_signals(self):
    self.data = Signal()
    self.event = Signal()
    self.unhandled_event = Signal()
  
  #==============================
  def add_event(self, name, regex):
    if name in self.events:
      raise EventError('Event already exists')
      
    if isinstance(regex, str):
      regex = re.compile(str)
    
    self.events[name] = {
      'regex': regex
    }
  
  #==============================
  # Twisted event
  def datagramReceived(self, data, (host, port)):
    self.data.send(sender=self.__class__, data=data)
    #print data
    #log L date - time: response
    null, null, date, null, time, response = data[4:-2].split(' ', 5)

    #log.debug(response)
    found_event = False
    for event in self.events:
      m = self.events[event]['regex'].match(response)
      if m:
        log_detail.debug('[%s] event [%s]: %s' % (self.__class__.__name__, event, m.groupdict()))
        self.event.send(sender=self.__class__, event=event, data=m.groupdict())
        found_event = True
        break
    
    # If the event wasn't found, then fire the unhandled_event in case some plugin wants to handle it.
    # Though, you could just use add_event instead.
    if not found_event:
      self.unhandled_event.send(sender=self.__class__, data=response)

