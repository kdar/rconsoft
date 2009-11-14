# Read LICENSE for licensing details.

import struct
import re
import logging

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import defer
from twisted.internet import reactor

from rconsoft.dispatch.dispatcher import Signal

log = logging.getLogger('general')
log_detail = logging.getLogger('detail')

#------------------------------
class PasswordError(Exception):
  """Thrown when the rcon password is incorrect."""
  pass

#------------------------------
class RconError(Exception):
  """Thrown when something bad happens in the rcon library."""
  pass

#------------------------------
class NetworkData(object):
  """This object encapsulates network data. It enables you to
  easily grab bits and pieces of the message."""
  
  #==============================
  def __init__(self, data):
    self.data = data
    
  #==============================
  def get_byte(self):
    ret = ord(self.data[0])
    self.data = self.data[1:]
    return ret

  #==============================
  def get_char(self):
    ret = str(self.data[0])
    self.data = self.data[1:]
    return ret
  
  #==============================
  def get_string(self):
    loc = self.data.find('\x00')
    ret = self.data[0:loc]
    self.data = self.data[loc+1:]
    return ret
  
  #==============================
  def get_int(self):
    ret = struct.unpack('i', self.data[0:4])[0]
    self.data = self.data[4:]
    return ret
  
  #==============================
  def get_float(self):
    ret = struct.unpack('f', self.data[0:4])[0]
    self.data = self.data[4:]
    return ret
  
  #==============================
  def __str__(self):
    return self.data.__str__()
  
  #==============================
  def __repr__(self):
    return self.data.__repr__()
 
#------------------------------
class HL1Network(DatagramProtocol):
  """A class to handle networking for HL1 servers. It contains methods to do
  rcon authentication and to send rcon commands."""
  
  #==============================
  def __init__(self, host, port, password):   
    self.host = host
    self.port = port
    self.password = password
    
    self.ready = Signal()
    
    self.deferreds = []
  
  #==============================
  # Twisted event
  def startProtocol(self):
    #==============================
    def _start_protocol(ip):
      """This is called once the host is resolved."""
      
      self.host = ip
      self.transport.connect(self.host, self.port)
      self.authenticate()
    
    reactor.resolve(self.host).addCallback(_start_protocol)
  
  #==============================
  # Twisted event
  # Note: There could be a potiential problem with this function and using deferreds.
  # In udp, we are not guaranteed the order of the packets we receive. So it could be
  # the case that you call rcon_client.command("mp_startmoney") and
  # rcon_client.command("mp_friendlyfire"), and have the mp_friendlyfire response return
  # first and have the callback of the first command called. This has yet to happen
  # so I have yet to worry about it.
  def datagramReceived(self, data, (host, port)):
    if data.startswith('\xFF\xFF\xFF\xFFchallenge rcon'):
      self.challenge_id = data.split(' ')[2].strip(' \n\x00')
      # This is just to test to see if our password worked. It will
      # throw an exception if it wasn't the right password.
      #self.command('say')
      # Send the ready signal since we've received our challenge.
      self.ready.send(sender=self.__class__)
    elif data.startswith("\xFF\xFF\xFF\xFFlBad rcon_password."):
      raise PasswordError('Invalid rcon password')
    elif data.startswith("\xFF\xFF\xFF\xFFlBad challenge."):
      raise Exception("BAD CHALLENGE???? WHY???")
    elif self.deferreds and data.startswith('\xFF\xFF\xFF', 1):
      # All this code reassembles packets if they're fragmented by the hlds.
      # It's a little tricky since we have to do this asynchronously, and save
      # our state between receives.
      if data and data[0] == '\xFE':
        packet_count = ord(data[8]) & 15
        self.deferreds[0]['packet_count'] = packet_count
        self.deferreds[0]['packets'] = [' ' for i in range(packet_count)]        
      packet_count = getattr(self.deferreds[0], 'packet_count', None)
      if packet_count is not None:
        if packet_count > 0:
          index = ord(data[8]) >> 4
          self.deferreds[0]['packets'][index] = data[9:]
          packet_count -= 1
          self.deferreds[0]['packet_count'] = packet_count
        
          if packet_count == 0:
            data = ''
            for packet in self.deferreds[0]['packets']:
              data = data + packet
      # --End reassemble packet code
      
      # This executees if packet_count is either None or 0 (important!)
      if not packet_count:
        data = data[5:].strip(' \n\x00')
        self.deferreds[0]['deferred'].callback(data)
        self.deferreds = self.deferreds[1:]

  #==============================
  # Twisted event
  def connectionRefused(self):
    #print "No one listening"
    pass
   
  #============================== 
  def authenticate(self, password=None):
    """Authenticates to the server. If the password is not passed, it uses
    self.password instead."""
    
    if password:
      self.password = password
    
    data = self.send("challenge rcon")
  
  #==============================
  def send(self, data):
    """Sends a packet to the server."""
    
    self.transport.write("\xFF\xFF\xFF\xFF%s\x00" % data)
    
  #============================== 
  def command(self, *args, **kwargs):
    """Sends an rcon command to the server. It takes a variable amount of
    parameters which it separates by spaces. You can pass deferred=False to
    not create a deferred for this command."""
    
    d = None
    if kwargs.get('deferred', True):
      d = defer.Deferred()
      self.deferreds.append({'deferred': d})   
      #print "Added callback for: %s" % ' '.join(args)
    
    command = "rcon %s \"%s\" %s" % (self.challenge_id, self.password, ' '.join(args))
    self.send(command)
    
    return d
  
  #============================== 
  def is_player(self, player):
    """Returns whether the player passed is a player or not."""
    
    return player['uniqueid'].startswith('STEAM_')

#------------------------------
class RconClient(object):
  """A class that has knowledge of rcon commands and allows the user
  to send rcon commands to the server."""
  
  #============================== 
  def __init__(self, network=None):
    self.players = {} # Indexed by uniqueid    
    self.network = network
    self.default_hostname = None
  
  #============================== 
  def set_network(self, network):
    """Sets the network for this object."""
    
    if self.network:
      self.network.close()
    self.network = network
  
  #============================== 
  def set_default_hostname(self, hostname):
    """Sets a default hostname for the game server. This is here so that
    you can call hsay without changing the hostname."""
    
    self.default_hostname = hostname
  
  #==============================
  def command(self, *args, **kwargs):
    """This is just a passthrough method for the network object."""
    
    return self.network.command(*args, **kwargs)
  
  #==============================
  """A helper function to compile a regular expression. If the compile fails,
  it will escape the regular expression passed before compiling it."""
  
  def _regex_compile(self, regex):
    regexp = None
    try:
      regexp = re.compile(regex, re.IGNORECASE)
    except Exception:
      regexp = re.compile(re.escape(regex), re.IGNORECASE)
      
    return regexp
    
  #==============================
  def get_players(self, names=None, reverse=False):
    """Returns a dictionary of players indexed by their uniqueid
    for a given list of names. The names are treated as regular expressions.
    If reverse is passed, then players who don't match are returned. If no
    parameters are passed, all players are returned."""
     
    players = {}
    
    if names:      
      for name in names:
        regexp = self._regex_compile(name)      
        for uniqueid in self.players:
          player = self.players[uniqueid]
          if self.network.is_player(player) and regexp.search(player['name']):
            players[uniqueid] = player
      
      # Might not be a terribly efficient way of doing this.
      if reverse:
        revplayers = {}
        for uniqueid in self.players:
          player = self.players[uniqueid]
          if self.network.is_player(player) and uniqueid not in players:
            revplayers[uniqueid] = player
        players = revplayers
    
    # No names were passed, so get everyone that is a player.
    if names is None:
      for uniqueid in self.players:
        player = self.players[uniqueid]
        if self.network.is_player(player):
          players[uniqueid] = player
    
    log_detail.debug('[%s] get_players: %s' % (self.__class__.__name__, players))
    
    return players
  
  #==============================
  def find_players(self, property, value):
    """Returns a list of players if the player has a particular property
    which equals the value passed."""
    
    players = {}
    
    for uniqueid in self.players:
      player = self.players[uniqueid]
      if self.network.is_player(player) and property in player and player[property] == value:
        players[uniqueid] = player
        
    log_detail.debug('[%s] find_players: %s' % (self.__class__.__name__, players))
    
    return players
   
  #==============================
  def _set_difference_intersection(self, a, b):
    a = set(a)
    return (a.difference(b), a.intersection(b))
  
  #==============================
  def kick(self, uniqueid, reason=''):
    """Kick a user based on their uniqueid."""
    self.command("kick", "#%s" % uniqueid, reason)
    
    log_detail.debug('[%s] kick: %s' % (self.__class__.__name__, uniqueid))
  
  #============================== 
  def kick_ex(self, names=None, uniqueids=None, reason='', uniqueid_exceptions=None):
    """Kicks users from the server. You can pass both a list of uniqueids
    or a list of names. The names will be treated as regular expressions.
    You can also provide a list of unqueid exceptions that will not be kicked. 
    Returns a dictionary:
      uniqueids: set of uniqueids kicked,
      exceptions: set of uniqueids not kicked
    """
    if not names:
      names = []
    if not uniqueids:
      uniqueids = []
    if not uniqueid_exceptions:
      uniqueid_exceptions = []
    
    players = self.get_players(names=names)
    uniqueids.extend([players[index]["uniqueid"] for index in players])
    
    uniqueids, exceptions = self._set_difference_intersection(uniqueids, uniqueid_exceptions)
    
    for uniqueid in uniqueids:
      self.kick(uniqueid, reason=reason)
      
    ret = {
      'uniqueids': uniqueids,
      'exceptions': exceptions
    }
    
    return ret
  
  #==============================  
  def rkick_ex(self, names=None, reason='', uniqueid_exceptions=None):
    """Reverse kicks a list of names treated as regular expressions. Meaning, anyone
    who doesn't match these expressions are kicked.
    You can also provide a list of unqueid exceptions that will not be kicked. 
    Returns a dictionary:
      uniqueids: set of uniqueids kicked,
      exceptions: set of uniqueids not kicked
    """
    if not names:
      names = []
    if not uniqueid_exceptions:
      uniqueid_exceptions = []
      
    players = self.get_players(names=names, reverse=True)
    uniqueids = [players[index]["uniqueid"] for index in players]
    return self.kick_ex(uniqueids=uniqueids, reason=reason, uniqueid_exceptions=uniqueid_exceptions)
    
  #==============================
  def ban(self, uniqueid, duration=0, kick=True):
    """Bans a user from the server. Be sure to call writeid to write the bans to the config."""
    
    if kick:
      self.command("banid", str(duration), "%s" % uniqueid, "kick")
    else:
      self.command("banid", str(duration), "%s" % uniqueid)
    
  #============================== 
  def ban_ex(self, names=None, uniqueids=None, duration=0, uniqueid_exceptions=None):
    """Bans users from the server. You can pass both a list of uniqueids
    or a list of names. The names will be treated as regular expressions.
    You can also provide a list of unqueid exceptions that will not be kicked. 
    Returns a dictionary:
      uniqueids: set of uniqueids banned,
      exceptions: set of uniqueids not banned
    """
    if not names:
      names = []
    if not uniqueids:
      uniqueids = []
    if not uniqueid_exceptions:
      uniqueid_exceptions = []
      
    players = self.get_players(names=names)
    uniqueids.extend([players[index]["uniqueid"] for index in players])
    
    uniqueids, exceptions = self._set_difference_intersection(uniqueids, uniqueid_exceptions)
    
    for uniqueid in uniqueids:
      self.ban(uniqueid=uniqueid, duration=duration)
    self.writeid()
    
    ret = {
      'uniqueids': uniqueids,
      'exceptions': exceptions
    }
    
    return ret
    
  #==============================  
  def rban_ex(self, names=None, uniqueid_exceptions=None):
    """Reverse bans a list of names treated as regular expressions. Meaning, anyone
    who doesn't match these expressions are banned.
    You can also provide a list of unqueid exceptions that will not be kicked. 
    Returns a dictionary:
      uniqueids: set of uniqueids banned,
      exceptions: set of uniqueids not banned
    """
    if not names:
      names = []
    if not uniqueid_exceptions:
      uniqueid_exceptions = []
      
    players = self.get_players(names=names, reverse=True)
    uniqueids = [players[index]["uniqueid"] for index in players]
    
    return self.ban_ex(uniqueids=uniqueids, uniqueid_exceptions=uniqueid_exceptions)
  
  #==============================
  def unban(self, uniqueid):
    """Unbans users from the server. Be sure to call
    writeid to undo the ban from the config.
    """    
    self.command("removeid", "%s" % uniqueid) 

  #==============================
  def say(self, text):
    """Makes the server say something."""
    
    self.command("say", text)
  
  #==============================
  def hsay(self, hostname, text):
    """Makes the server say something with a particular
    hostname prefix. E.g. <hostname> HI!
    
    It will set the hostname back to the default hostname
    if it is set. Use set_default_hostname to set the default
    hostname.
    """    
    #old_hostname = self.cvar("hostname")
    self.hostname(hostname)
    self.say(text)
    
    if self.default_hostname:
      self.hostname(self.default_hostname)
    #self.hostname(old_hostname)
  
  #==============================
  def hostname(self, hostname):
    """Sets the hostname of the server."""
      
    self.command('hostname', '"%s"' % (hostname if hostname else ''))
    
  #============================== 
  def changelevel(self, map):
    """Changes the map of the server."""
    
    self.command("changelevel", map)

  #==============================
  def restart(self):
    """Restarts the server."""
    
    self.command("_restart")
    
  #==============================
  def quit(self):
    """Quits the server."""
    
    self.command("quit")
    
  #==============================
  def cvar(self, cvar, value=None):
    """Gets or sets a server cvar."""
    
    d = defer.Deferred()
    
    #==============================
    def got_cvar(response):
      ret = None
      m = re.match('^"(.*?)" (is|=) "(.*?)"', response)
      if m:
        ret = m.group(3)
      
      if value:
        self.command(cvar, value)
        
      d.callback(ret)
      
    self.command('%s' % cvar).addCallback(got_cvar)
    
    return d
  
  #==============================
  def toggle_cvar(self, cvar):
    """Toggles a cvar on or off if it is toggable."""
    
    #==============================
    def got_cvar(value):
      if value == "1":
        value = "0"
      else:
        value = "1"
      self.cvar(cvar, value)
    
    self.cvar(cvar).addCallback(got_cvar)

  
  #==============================
  def exec_(self, config):
    """Sends a exec command to load a config."""
    
    self.command("exec", config)
  
  #==============================
  def writeid(self):
    """Updates the banned.cfg with the current bans."""
    
    self.command("writeid")
  
  #==============================
  def users(self):
    """Gets a list of users from the server and returns it. It also saves
    the data in self.players."""
    
    d = defer.Deferred()
    
    #==============================
    def process_users(data):
      # Clear the cache
      #self.players = {}
    
      lines = data.split('\n')
      
      header = lines[0]
      # Gets rid of unecessary crap
      lines = lines[2:-1]
      
      keys = header.split(' : ')
      for line in lines:      
        values = line.split(' : ')
        player_dict = {}
        for i in enumerate(values):
          player_dict[keys[i[0]]] = i[1].strip()
        self.players.setdefault(player_dict['uniqueid'], {}).update(player_dict)
        
      d.callback(self.players)
    
    self.command('users').addCallback(process_users)
    return d
  
  #==============================
  def user(self, uniqueid):
    """Sends a 'user' command for a particular user and returns the information. It
    also updates their information in the players dict."""
    
    d = defer.Deferred()
    
    player = self.players[uniqueid]
    
    #==============================
    def got_user(data):
      lines = data.split('\n')
      for line in lines:
        m = re.match(r'(.*?)\s+(.*)', line)
        player[m.group(1)] = m.group(2)
      
      d.callback(player)
      
    self.command('user', player['userid']).addCallback(got_user)
    return d  

  #==============================
  # FIXME: Not done
  #def status(self):
  #  #status_response = self.command('status')
  #  a = open('tests/status_data', 'r')
  #  status_response = RconResponse(''.join(a.readlines()))
  #  a.close()
  #  
  #  lines = str(status_response).split('\n')
  #  index = 0
  #  for line in lines:
  #    index += 1
  #    if line == '' or line and line[0] == '#':
  #      break
  #    key,value = re.split('\s*:\s*', line, 1)
  #    self.cache.status[key] = value      
  #  
  #  # Retrieve the header's keys
  #  keys = re.split('\s+', lines[index])
  #  keys.pop(0)
  #  index += 1
  #  
  #  for line in lines[index:]:
  #    line = line[4:]
  #    
  #    #print re.split('\s', line)

if __name__ == "__main__":
  rcon = RconClient(HL1Network("192.168.0.1", 27015, "****"))
  #rcon.status()
  #print rcon.users()
  #print rcon.cvar('mp_startmoney')
  #rcon.rkickx(names=["^C"])
  #rcon.say("HEY THERE")
  #rcon.changelevel("de_nuke")
  #rcon.command("sv_restart", "10") 
  #rcon.cvar("mp_startmoney", 16000)
  #rcon.command("sv_restart", 1)
  #rcon.hnsay("kevinrules", "caca")
  #rcon.ban('STEAM_0:1:7114301')
  #rcon.unban('STEAM_0:1:7114301')
  #rcon.writeid()
  