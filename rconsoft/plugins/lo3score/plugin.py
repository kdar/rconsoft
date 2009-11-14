# Read LICENSE for licensing details.

import os
import logging

from twisted.internet import reactor

from rconsoft.plugins import Plugin
from rconsoft import rcon_client, rcon_receiver
from rconsoft.config import cget, has_access

log = logging.getLogger('general')

#------------------------------
class Lo3ScorePlugin(Plugin):  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
   
    rcon_receiver.event.connect(self.on_rcon_event)
    
    #CommandProvider.plugins.find('ExePlugin')    
    
    self.t_score = 0
    self.ct_score = 0

  #==============================
  def on_command(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True
    
    

    # Keep processing other plugins.
    return True


  #==============================
  def on_rcon_event(self, event, data, **kwargs):
    if event == 'team_triggered':
      if 't_score' in data and 'ct_score' in data:
        if data['t_score'] != '0' or data['ct_score'] != '0':
          self.t_score = data['t_score']
          self.ct_score = data['ct_score']
