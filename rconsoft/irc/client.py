# Read LICENSE for licensing details.

import sys
import traceback

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from rconsoft.dispatch.dispatcher import Signal

#------------------------------
class IrcClientProtocol(irc.IRCClient):
  """The protocol that IrcClient will use. It does some minor things
  to aid in using irc. Most of the logic should be implemented via the
  user."""
  
  #==============================
  def __init__(self, network):
    """Network is a dictionary containing:
    alias - alias of the network (e.g. gamesurge)
    nick - nick of the client
    username - username of the client
    realname - real name of the client
    authname - authentication name of the client. Only used on certain servers.
    password - authentication password of the client.
    channels - the channels the client should join on connect.
    modes - the user modes to set when connected. e.g. iwx"""
    
    self.network = network
  
  #==============================
  def set_network(self, network):
    self.network = network
    
    self.nickname = self.network['nickname']
    self.password = self.network['password']
    self.realname = self.network['realname']
    self.username = self.network['username']

  #==============================
  # Twisted event
  def signedOn(self):
    """Called when bot has succesfully signed on to server."""
    
    if self.network.get('alias', '') == 'gamesurge':
      self.sendLine('authserv auth %s %s' % (self.network.get('authname', ''), self.network.get('password', '')))
    
    # Set user modes
    modes = self.network.get('modes', '')
    if modes:
      self.sendLine('MODE %s +%s' % (self.network['nickname'], modes))
    
    for channel in self.network.setdefault('channels', []):
      self.join(channel)

  #==============================
  # Twisted event
  def nickChanged(self, nick):
    """Called when my nick has been changed."""
    
    self.nickname = nick
    self.network['nickname'] = nick
  
  #==============================
  # Twisted event 
  def lineReceived(self, line):
    irc.IRCClient.lineReceived(self, line)
    
    print line
    
    prefix, command, params = irc.parsemsg(line)
    
    if command == 'ERROR':
      if params and params[0].find('too fast') != -1:
        print 'Client trying to reconnect too fast.'
   
  #==============================
  # Twisted event  
  def handleCommand(self, command, prefix, params):
    """An override to provide a means of calling a generic
    error handler function.
    
    Determine the function to call for the given command and call
    it with the given arguments.
    """
    method = getattr(self, 'irc_%s' % command, None)
    is_error = command.startswith('ERR_')
    try:
      if method is not None:
        method(prefix, params)
      
      if is_error:
        self.irc_error(prefix, command, params)
      elif method is None:
        self.irc_unknown(prefix, command, params)
    except:
      irc.log.deferr()
  
  #==============================
  def irc_error(self, prefix, command, params):
    """A placeholder for irc errors."""
    pass
  
  #def sendLine(self, line):
  #  irc.IRCClient.sendLine(self, line)
  #  print line
    
#------------------------------
class IrcClient(object):
  """This class represents an irc client. It will only connect to
  a single server, but it will reconnect if it has lost its connection.
  This class was created because I do not like how the twisted irc client
  is programmed. The class provides signals that users can connect to and some
  helper functions."""
  
  factory_class = protocol.ReconnectingClientFactory
  protocol_class = IrcClientProtocol
  
  # List of functions of the protocol_class to attach
  # signals to.
  # The list is a tuple where the first item is the real function
  # that we will hook, and the second item is the function name we
  # will use to create our signals.
  # After __init__ is called, this object will contain a dictionary (self.events) 
  # of signals that will contain pre_<function name> and post_<function name> signals.
  # E.g. pre_signed_on and post_signed_on
  protocol_hooks = [
    # Things this client is involved in
    ('signedOn', 'signed_on'),     # ()
    ('joined', 'joined'),          # (channel)
    ('left', 'left'),              # (channel)
    ('privmsg', 'privmsg'),        # (user, channel, message)
    ('kickedFrom', 'kicked_from'), # (channel, kicker, message)
    
    # Things the client observes other people doing in a channel.
    ('userJoined', 'user_joined'),  # (user, channel)
    ('userLeft', 'user_left'),      # (user, channel)
    ('userQuit', 'user_quit'),      # (user, quitMessage)
    ('userKicked', 'user_kicked'),  # (kickee, channel, kicker, message)
    ('userRenamed', 'user_renamed') # (oldname, newname)
  ]
  
  # List of functions of the protocol_class to mirror
  # to this class.
  # The list is a tuple where the first item is the real function
  # that we will mirror, and the second item is the function name
  # you will use to call the actual function in this object.
  protocol_mirror = [
    ('join', 'join'),
    ('leave', 'leave'),
    ('kick', 'kick'),
    ('topic', 'topic'),
    ('mode', 'mode'),
    ('say', 'say'),
    ('msg', 'msg'),
    ('notice', 'notice'),
    ('away', 'away'),
    ('back', 'back'),
    ('whois', 'whois'),
    ('setNick', 'set_nick'),
    ('quit', 'quit')
  ]
   
  #==============================
  def __init__(self, network=None):
    self.set_network(network)
    self.factory = self.factory_class()
    self.factory.irc_client = self
    self.factory.buildProtocol = self.build_protocol
    
    # Set up all of the signals we will be using for our protocol
    # hooks.
    self.events = {}
    for (hook, name) in self.protocol_hooks:
      self.events['pre_%s' % name] = Signal()
      self.events['post_%s' % name] = Signal()
      
    # This basically will mirror all functions listed in protocol_mirror
    # from the protocol class. This just makes it easier so people can
    # type irc_client.msg("crenix", "Hey guy!") instead of
    # irc_client.protocol.msg("crenix", "Hey guy!")
    for (real_name, name) in self.protocol_mirror:
      def _generate(n):
        def _fn(*args, **kwargs):
          getattr(self.protocol, n)(*args, **kwargs)
        return _fn
      setattr(self, name, _generate(real_name))

  #==============================
  def set_network(self, network):
    self.network = network
    
  #==============================
  def build_protocol(self, addr):
    p = self.protocol_class(self.network)
    p.factory = self.factory
    p.set_network(self.network)
    self.protocol = p
    
    self._do_hooks(p)
    
    return p
  
  #==============================
  def _do_hooks(self, protocol):
    """Hooks into certain functions of our protocol. Provides
    a means of connecting to signals before and after the function
    is called.
    
    Note: Let's say you're going to catch a signal of the function: privmsg.
    Its definition looks like:
      def privmsg(self, user, channel, message):
        ...
    
    You would do something like:
      irc_client.events['post_privmsg'].connect(my_privmsg)
      
    Now here's the catch. Your my_privmsg must look like:
      def my_privmsg(self, user, channel, message):
       ...
       
    You cannot name the parameters any way you choose. This function is called
    with **named where named is a dictionary of the parameters. So your function
    definition receiving the signal, must match exactly to the one defined in
    the protocol.
    
    E.g. of something that would fail:
      def my_privmsg(self, user, channel, msg):
        ...
    """
    
    #==============================
    def wrap(fn, name):
      # Get the argument names of the function so we know what
      # to send when we fire the signal.
      argnames = fn.func_code.co_varnames[1:]
      #==============================
      def _wrap(*args, **kwargs):
        _kwargs = {} # The args we will send via the signal
        # Update the _kwargs with the kwargs sent to our function
        _kwargs.update(kwargs)
        # Go through each argument name and update the _kwargs with
        # the arguments passed to our function.
        for i,k in enumerate(argnames):
          if i < len(args):
            _kwargs[k] = args[i]
        
        try:
          self.events['pre_%s' % name].send(sender=self, **_kwargs)
          _kwargs['return_'] = fn(*args, **kwargs)
          self.events['post_%s' % name].send(sender=self, **_kwargs)
        except TypeError, e:
          traceback.print_exc()
          traceback._print(sys.stderr, e.message)
          traceback._print(sys.stderr, 'Ensure that the function that is '
                           'catching the signal has the same exact signature '
                           '(meaning, same names of parameters) as the '
                           'function sending the signal')
          
        return _kwargs['return_']
      return _wrap
    
    for (hook, name) in self.protocol_hooks:
      setattr(protocol, hook, wrap(getattr(protocol, hook), name))
  