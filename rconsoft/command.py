# Read LICENSE for licensing details.

"""Everything that deals with commands goes here."""

import logging
import traceback
import shlex
import inspect

from rconsoft.dispatch.dispatcher import Signal
from rconsoft.config import config

log = logging.getLogger('general')

ALL_COMMANDS = object()
REMAINING_COMMANDS = object()

#==============================
def command(*args):
  """A simple decorator that stores the commands
  the method handles into the method itself. This method
  will be used by the dispatcher made by get_dispatcher.
  Pass in ALL_COMMANDS in order to catch all commands.
  Pass REMAINING_COMMANDS in order to catch all the remaining
  commands that did not have handlers.
  
  Note: This is not necessary to do command handling. This is
  a helper decorator. You can connect to the command handler
  event directly and handle commands yourself.
  
  E.g.
  @command('kick', 'ban')
  func handler(*args, **kwargs):
     ..."""
  def new(f):
    setattr(f, '__commands__', args)
    return f
  return new

#==============================
def get_dispatcher(self):
  """Creates a dispatcher for a class that can be connected to
  the event signal of CommandHandler. It will call the
  appropriate functions based on what is tagged by the
  'command' decorator.
  
  Note: This is not necessary to do command handling. This is
  a helper dispatcher. You can connect to the command handler
  event directly and handle commands yourself.  
  """
  
  members = inspect.getmembers(self)
  commands = {}
  
  # Finds all the commands supported by the class.
  for x,y in members:
    cmds = getattr(y, '__commands__', [])
    for cmd in cmds:
      commands[cmd] = y
  
  #==============================
  def dispatcher(*args, **kwargs):
    """Grabs the commands from kwargs and sees if we have
    any handlers for it. If we do, we call them."""
    
    command = kwargs.get('command', None)
    if command:
      if command in commands:
        commands[command](*args, **kwargs)
      elif REMAINING_COMMANDS in commands:
        commands[REMAINING_COMMANDS](*args, **kwargs)
          
      if ALL_COMMANDS in commands:
        commands[ALL_COMMANDS](*args, **kwargs)
      
  # We must save this function so in case we only store a weak
  # reference to it, it doesn't get garbage collected.
  self.__dispatcher_function__ = dispatcher
  return dispatcher

#==============================
def shell_parse(params):
  """Tries to parse the params using a shell lexical analyzer.
  If this fails, it will just try to split it by spaces. Returns
  a list of the params."""
  
  parsed_params = None
  try:
    parsed_params = shlex.split(params)
  except ValueError:
    if ' ' in params:
      parsed_params = params.split(' ')
  
  return parsed_params

#------------------------------
class CommandInterrupt(Exception):
  """Raise this exception when you want to stop the command
  from propagating to other plugins."""
  pass

#------------------------------
class CommandHandler(object):  
  #==============================
  def __init__(self):
    self._init_signals()
    
  #==============================
  def _init_signals(self):
    self.event = Signal()

  #==============================
  def process(self, command, extra=None, silent=False, **kwargs):
    command = command.split(' ')
    params = ' '.join(command[1:])
    command = command[0]
    stop = False
        
    try:
      stop = self.event.send(
        sender=self.__class__,
        command=command,
        params=params,
        extra=extra,
        silent=silent,
        **kwargs
      )
    except CommandInterrupt:
      pass
    except:
      raise
    
    ##==============================
    ## A helper function that called a command function with
    ## a set of parameters. This makes the code cleaner/shorter.
    ## This function will also set stop to True if the function
    ## returns False.
    #def call_command_function(function):
    #  try:
    #    stop = function(
    #      sender=self.__class__,
    #      command=command,
    #      params=params,
    #      parsed_params=parsed_params,
    #      extra=extra,
    #      silent=silent,
    #      **kwargs
    #    ) == False
    #  except:
    #    raise
    #
    #if len(command):
    #  # Iterate through the list of CommandProvider plugins, calling
    #  # their on_command function.
    #  for plugin in CommandProvider.plugins:
    #    # Stop propagating the command. Useful for when you want to override
    #    # another plugin's command.
    #    if stop:
    #      break
    #    
    #    # Iterate through all the commands this plugin handles.
    #    for cmd in plugin.commands:
    #      # Call their on_command function if the command matches since this is a string.
    #      if isinstance(cmd, str):
    #        if cmd == command:
    #          call_command_function(plugin.on_command)
    #      # Call the specific function in the config if the command matches since this is a config.
    #      else:
    #        if ('name' in cmd and cmd['name'] == command) or ('names' in cmd and command in cmd['names']):
    #          fn = cmd['fn']
    #          # If the function is a string, then get the function from the object.
    #          if isinstance(fn, str):
    #            fn = getattr(plugin, fn)
    #          call_command_function(fn)
    #        
    #  # Send the event to whomever is concerned. Plugins should
    #  # not latch onto this unless they have a good reason to.
    #  call_command_function(self.event.send)
