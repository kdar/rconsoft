# Read LICENSE for licensing details.

from rconsoft.plugins import Plugin
from rconsoft import rcon_client, command_handler
from rconsoft.config import cget, has_access
from rconsoft.command import get_dispatcher, command, shell_parse

#------------------------------
class CorePlugin(Plugin):
  """Supported commands: r, rr, map, changelevel, say, hsay, pass, password
      k, kick, rkick, rk, b, ban, kb, rban, rb, rkb"""
  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
    
    command_handler.event.connect(get_dispatcher(self))
  
  #==============================
  @command('r', 'rr', 'map', 'changelevel', 'say', 'hsay', 'pass', 'password')
  def on_command(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Restart round
    if command == 'r' or command == 'rr':
      wait = params if params else '1'
      rcon_client.cvar('sv_restart', wait)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Map
    elif command == 'map' or command == 'changelevel':
      rcon_client.changelevel(params)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Say
    elif command == 'say':
      rcon_client.say(params)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Hostname say
    elif command == 'hsay':
      p = params.split(' ', 1)
      if len(p) > 1:
        rcon_client.hsay(p[0], ' '.join(p[1:]))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Password
    elif command == 'pass' or command == 'password':
      if params:
        rcon_client.cvar('sv_password', params)
        if not silent:
          rcon_client.hsay('', 'Set password to: %s' % params)
      else:
        #==============================
        def got_password(value):
          rcon_client.hsay('', 'Password is set to: %s' % value)
        rcon_client.cvar('sv_password').addCallback(got_password)
        
    
    # Keep processing other plugins.
    return True
  
  #==============================
  @command('k', 'kick', 'rkick', 'rk', 'b', 'ban', 'kb', 'rban', 'rb', 'rkb')
  def on_control(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    if not has_access(uniqueid, 'admin'):
      return True
    
    parsed_params = shell_parse(params)
    
    # Test if there is a --force parameter. If so then ignore any exceptions.
    # Otherwise, build a list of exceptions based on the admin users.
    uniqueid_exceptions = []
    if parsed_params and parsed_params[0] == '--force':
      parsed_params = parsed_params[1:]
    else:
      # If there was no force param, then add all people who are admins or higher
      # onto the list of exceptions.
      for user in cget('users', default=[]):
        entry = cget('users', user, default={'uniqueid': None})
        if has_access(entry['uniqueid'], 'user'):
          uniqueid_exceptions.append(entry['uniqueid'])
     
    action = ''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Kick
    if command == 'k' or command == 'kick':
      action = 'kick'
      rcon_client.kick_ex(names=parsed_params, uniqueid_exceptions=uniqueid_exceptions)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reverse kick
    elif command == 'rkick' or command == 'rk':
      action = 'rkick'
      rcon_client.rkick_ex(names=parsed_params, uniqueid_exceptions=uniqueid_exceptions)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Ban
    elif command == 'b' or command == 'ban' or command == 'kb':
      action = 'ban'
      rcon_client.ban_ex(names=parsed_params, uniqueid_exceptions=uniqueid_exceptions)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reverse ban
    elif command == 'rban' or command == 'rb' or command == 'rkb':
      action = 'rban'
      rcon_client.rban_ex(names=parsed_params, uniqueid_exceptions=uniqueid_exceptions)
      
    #if action:
    #  if not silent:
    #    rcon_client.hsay('', '[%s]: %s' % (action, params))
        
      # This will print out a warning as to why the action was not performed on
      # the list of players.
      #if 'exceptions' in ret and ret['exceptions']:
        #names = [rcon_client.cache['players'][uniqueid]['name'] for uniqueid in ret['exceptions']]
        #rcon_client.say('[%s]: Use --force to %s exceptions.' % (action, action))
        
    return True
      