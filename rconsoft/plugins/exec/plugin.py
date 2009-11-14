# Read LICENSE for licensing details.

import os

from twisted.internet import reactor

from rconsoft.plugins import CommandProvider
from rconsoft import rcon_client
from rconsoft.config import cget, has_access

#------------------------------
class ExecPlugin(CommandProvider):
  # All the commands this plugin provides.
  commands = [
    'exec',
    {
      'name': 'lo3',
      'fn': 'on_lo3'
    }
  ]
  
  #==============================
  def __init__(self, *args, **kwargs):
    CommandProvider.__init__(self, *args, **kwargs)
    
    self.performing_lo3 = False

  #==============================
  def on_command(self, command, params, parsed_params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True

    if command == 'exec' and parsed_params:
      self.exec_(parsed_params[0])      

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
  def on_lo3(self, command, params, parsed_params, silent, **kwargs):
    # Don't do lo3 if we're already doing lo3.
    if self.performing_lo3:
      return True
    self.performing_lo3 = True
    
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    if not has_access(uniqueid, 'admin'):
      return True
    
    if command == 'lo3':
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
          reactor.callLater(int(delay)+1, do_restarts, index)
        else:
          self.performing_lo3 = False
          rcon_client.hsay('', lo3_live_message)
        
      do_restarts(0)

