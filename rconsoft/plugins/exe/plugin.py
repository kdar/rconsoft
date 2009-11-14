# Read LICENSE for licensing details.

import os

from twisted.internet import reactor

from rconsoft.plugins import Plugin
from rconsoft.dispatch.dispatcher import Signal
from rconsoft import rcon_client, command_handler
from rconsoft.config import cget, has_access
from rconsoft.command import get_dispatcher, command

#------------------------------
class ExePlugin(Plugin):
  """Supported commands: exec, execr, lo3"""
  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
    
    command_handler.event.connect(get_dispatcher(self))
    
    self.pre_lo3 = Signal()
    self.post_lo3 = Signal()
    self.performing_lo3 = False

  #==============================
  @command('exec', 'execr')
  def on_command(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True

    if (command == 'exec' or command == 'execr') and params:
      self.exec_(params)
      
      if command == 'execr':
        rcon_client.cvar('sv_restart', '1')

    # Keep processing other plugins.
    return True
  
  #==============================
  def exec_(self, name):
    if not name:
      return
    
    # Grab the location of our scripts
    path = cget('plugins', 'exec', 'scripts_path', default=os.path.join(os.path.dirname(__file__), 'scripts'))
    
    # Iterate through the scripts dir and try to find any file matching name.
    list = os.listdir(path)
    for file in list:
      file_name = os.path.splitext(file)[0]
      if name == file_name:
        fp = open(os.path.join(path, file), 'r')
        for line in fp:
          rcon_client.command(line, deferred=False)
        fp.close()
        break
  
  #==============================
  @command('lo3')
  def on_lo3(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    if not has_access(uniqueid, 'admin'):
      return True
      
    if command == 'lo3':
      # Don't do lo3 if we're already doing lo3.
      if self.performing_lo3:
        return True
      self.performing_lo3 = True
    
      self.pre_lo3.send(sender=self.__class__)
      
      self.exec_(cget('plugins', 'exec', 'exec_on_lo3'))
      
      # Get the configuration options for going lo3.
      default_lo3_messages = ['[ Going live on 3 restarts ]', '[ Two more restarts ]', '[ Last restart ]']
      default_lo3_delays = ['2', '2', '5']
      lo3_messages = cget('plugins', 'exec', 'lo3_messages', default=default_lo3_messages)
      lo3_delays = cget('plugins', 'exec', 'lo3_delays', default=default_lo3_delays)
      lo3_live_message = cget('plugins', 'exec', 'lo3_live_message', default='[* LIVE LIVE LIVE *]')
       
      #==============================
      def do_restarts(index):
        if index < len(lo3_messages):
          message = lo3_messages[index]
          delay = lo3_delays[index]
          rcon_client.hsay('', message)
          rcon_client.command('sv_restart', delay)
          index += 1
          reactor.callLater(int(delay)+0.9, do_restarts, index)
        else:
          self.performing_lo3 = False
          rcon_client.hsay('', lo3_live_message)
          self.post_lo3.send(sender=self.__class__)
        
      do_restarts(0)
