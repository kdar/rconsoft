"""The Rcon processor."""

import re
import logging

from rconsoft.dispatch.dispatcher import Signal
from rconsoft.util.signalsocket import SignalSocket
from rconsoft.config import config

log = logging.getLogger(__name__)

#------------------------------
class EventError(Exception):
  """Is thrown when something involving events errors."""
  pass

#------------------------------
class RconProcessor(object):
  #==============================
  def __init__(self):
    self._init_signals()
    
    self.events = {
      'user_connected': {
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><(?P<team>.*?)>" connected, address "(?P<ip>.*?):(?P<port>.*?)"')
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
        'regex': re.compile(r'^"(?P<name>.*?)<(?P<userid>\d+)><(?P<uniqueid>.*?)><.*?>" changed name to "(?P<new_name>.*?)"')
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
      }
    }
    
  #==============================
  def _init_signals(self):
    self.data = Signal()
    self.ready = Signal()
    self.event = Signal()
    self.unhandled_event = Signal()
  
  #==============================
  def run(self):    
    self.sock = SignalSocket(config['rcon']['local']['host'], int(config['rcon']['local']['port']), 'udp')
    self.sock.post_receive.connect(self._on_sock_receive)
    self.sock.ready.connect(self._on_sock_ready)
    self.sock.server()
  
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
  def _on_sock_ready(self, **kwargs):
    self.ready.send(sender=self.__class__)
  
  #==============================
  def _on_sock_receive(self, data, **kwargs):
    self.data.send(sender=self.__class__, data=data)
    
    #log L date - time: response
    null, null, date, null, time, response = data[4:-2].split(' ', 5)
    
    #log.debug(response)
    found_event = False
    for event in self.events:
      m = self.events[event]['regex'].match(response)
      if m:
        self.event.send(sender=self.__class__, event=event, data=m.groupdict())
        found_event = True
        break
    
    # If the event wasn't found, then fire the unhandled_event in case some plugin wants to handle it.
    # Though, you could just use add_event instead.
    if not found_event:
      self.unhandled_event.send(sender=self.__class__, data=response)

