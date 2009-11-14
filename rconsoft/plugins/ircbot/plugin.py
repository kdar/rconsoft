# Read LICENSE for licensing details.

import re
import random

from twisted.internet import reactor

from rconsoft.plugins import Plugin
from rconsoft import rcon_client, command_handler
from rconsoft.config import cget, has_access
from rconsoft.command import get_dispatcher, command
from rconsoft.irc.client import IrcClient

irc_client = None
 
#------------------------------
class IrcBotPlugin(Plugin):  
  #==============================
  def __init__(self, *args, **kwargs):
    global irc_client
    
    Plugin.__init__(self, *args, **kwargs)
    
    command_handler.event.connect(get_dispatcher(self))
    
    network = {
      'host': cget('plugins', 'ircbot', 'host'),
      'port': int(cget('plugins', 'ircbot', 'port')),
      'alias': cget('plugins', 'ircbot', 'alias'),
      'nickname': cget('plugins', 'ircbot', 'nickname'),
      'username': cget('plugins', 'ircbot', 'username'),
      'realname': cget('plugins', 'ircbot', 'realname', default=''),
      'authname': cget('plugins', 'ircbot', 'authname'),
      'password': cget('plugins', 'ircbot', 'password'),
      'channels': cget('plugins', 'ircbot', 'channels'),
      'modes': cget('plugins', 'ircbot', 'modes', default='')
    }
    irc_client = IrcClient(network)    
    irc_client.events['post_joined'].connect(self.on_joined)
    irc_client.events['post_left'].connect(self.on_left)
    irc_client.events['post_privmsg'].connect(self.on_privmsg)
    
    reactor.connectTCP(network['host'], network['port'], irc_client.factory)
    
    self.finding = False
    self.ad = ''
    self.ad_delayed_call = None
    self.comment = ''
    self.channels = []
    self.nicks = {}
    
    # Usually means spammers.
    self.bad_message_re = re.compile(r'(#[a-zA-Z])|click|paste|idle')
    
  #==============================
  def on_joined(self, channel, **kwargs):
    """Called when the bot joins a channel."""
    
    self.channels.append(channel)
    
  #==============================
  def on_left(self, channel, **kwargs):
    """Called when the bot leaves a channel."""
    
    self.channels.remove(channel)

  #==============================
  def on_privmsg(self, user, channel, message, **kwargs):
    """Called when the bot receives a privmsg."""
    
    user = user.split('!', 1)[0]
    
    if self.channels and channel == irc_client.network['nickname']:
      if self.finding:      
        self.nicks[user] = user # Probably should fill with info or something.
        
        if not self.bad_message_re.match(message):
          rcon_client.hsay('irc:%s' % user, message)
      else:
        # If the user is in the ignore list, then just return. This could be
        # "Global" telling you something that we shouldn't respond to or we'll
        # enter into an infinite loop.
        user = user.lower()
        for ignore in cget('plugins', 'ircbot', 'ignore_nicks', default=[]):
          if ignore.lower() == user:
            return
          
        irc_client.msg(user, 'Sorry, I\'m no longer looking for a scrim.')
  
  #============================== 
  def find_nick(self, nick, silent=True):
    """A helper function to try to find a nick inside our nick list.
    The nick that you pass is a regular expression."""
    
    regex = re.compile(nick, re.IGNORECASE)
    for key in self.nicks:
      if regex.match(key):
        return self.nicks[key]
    
    if not silent:
      rcon_client.hsay('', 'Did not find nick: %s' % name)
    
    return None
  
  #==============================
  @command('msg', 'privmsg', 'lmsg', 'find', 'stopfind', 'stopfinding', 'findstop', 'ad', 'accept')
  def on_command(self, command, params, silent, **kwargs):    
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True     
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Find
    if command == 'find':      
      # We must decode the string to interpret the escapes (e.g. '\x37' into '7').
      ad = cget('plugins', 'ircbot', 'ad').decode('string-escape')
      self.comment = params if params else cget('plugins', 'ircbot', 'default_comment', default='de_any')
      self.ad = ad.replace('{comment}', self.comment)
      
      # We're not finding, so let's start it.
      if not self.finding:
        if not silent:
          rcon_client.hsay('', 'Finding a scrim.')
        self.finding = True
        
        # Only call do_advertising if the delayed call isn't active.
        # Otherwise we would message the channel immediately and potientially
        # get kicked/banned from it for spamming.
        if not self.ad_delayed_call or not self.ad_delayed_call.active():
          self.do_advertising()
      # If we are finding, just notify the user that we changed the parameters.
      else:
        if not silent:
          rcon_client.hsay('', 'Changed parameters. Still finding.')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Stop finding
    elif command == 'stopfind' or command == 'stopfinding' or command == 'findstop':
      if not silent:
        if self.finding:        
          rcon_client.hsay('', 'No longer finding a scrim.')
        else:
          rcon_client.hsay('', 'Not finding. Nothing to stop.')
      self.finding = False
      self.nicks = {}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Accept
    elif command == 'accept':
      if params:
        nick = self.find_nick(params, silent)
        if nick:
          default_password = cget('game', 'default_password', default='scrim')
          new_password = '%s%d' % (default_password, random.randint(1, 99))
          rcon_client.cvar('sv_password', new_password)
          rcon_client.hsay('', 'Giving "%s" the info. New password: %s' % (nick, new_password))
          rcon_client.hsay('', 'Don\'t forget to .stopfind when they connect.')
          # Too bad python 2.6's string formatting isn't in 2.5
          accept_message = cget('plugins', 'ircbot', 'accept_message', default='connect {host}:{port};password {password}')
          accept_message = accept_message.replace('{host}', cget('rcon', 'host'))
          accept_message = accept_message.replace('{port}', cget('rcon', 'port'))
          accept_message = accept_message.replace('{password}', new_password)
          irc_client.msg(nick, accept_message)    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Ad
    elif command == 'ad':
      rcon_client.hsay('', 'Find ad: %s' % self.comment)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Message
    elif command == 'msg':
      if params:
        params = params.split(' ', 1)
        if len(params) >= 2:
          nick = self.find_nick(params[0], silent)
          if nick:
            irc_client.msg(nick, params[1])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Private message or literal message. We send the message via irc no
    # matter if we have a record of the nick or not.
    elif command == 'privmsg' or command == 'lmsg':
      if params:
        params = params.split(' ', 1)
        if len(params) >= 2:
          irc_client.msg(params[0], params[1])
          
    # Keep processing other plugins.
    return True
  
  #==============================
  def do_advertising(self):
    """A function responsible for advertising. If we are still finding, it
    will continually call itself at a specific interval."""
    
    if not self.finding:
      return
    
    # Send an ad to each of the channels that we're in.
    for channel in self.channels:
      irc_client.msg(channel, self.ad)
      
    self.ad_delayed_call = reactor.callLater(int(cget('plugins', 'ircbot', 'ad_interval', default=45)), self.do_advertising)
    