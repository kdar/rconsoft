# Read LICENSE for licensing details.

from rconsoft.plugins import Plugin
from rconsoft import rcon_client, command_handler
from rconsoft.config import cget
from rconsoft.command import get_dispatcher, command, ALL_COMMANDS, REMAINING_COMMANDS

#------------------------------
class ExamplePlugin(Plugin):  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
    
    command_handler.event.connect(get_dispatcher(self))

  #==============================
  @command(ALL_COMMANDS)
  def all_commands(self, command, params, silent, **kwargs):
    """This function will be called when any command is executed. It would be a really
    good idea to check whether you want to handle this command and return immediately
    if you don't."""
    
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True     
    
    rcon_client.say('all_commands was called: %s' % command)
    
    # Keep processing other plugins.
    return True
  
  #==============================
  @command('example1', 'example2')
  def on_example_number(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True     
    
    rcon_client.say('on_example_number was called: %s' % command)
    
    # Keep processing other plugins.
    return True
      
  #==============================
  @command(REMAINING_COMMANDS)
  def remaining_commands(self, command, params, silent, **kwargs):
    """This function will be called when any command except example1 and example2
    is executed. It would be a really good idea to check whether you want to
    handle this command and return immediately if you don't."""
    
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True
    
    rcon_client.say('remaining_commands was called: %s' % command)
    
    # Keep processing other plugins.
    return True