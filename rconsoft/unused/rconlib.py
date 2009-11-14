# Read LICENSE for licensing details.

import socket
import select
import struct
import re
import time
import logging

log = logging.getLogger('general')

#------------------------------
class PasswordError(Exception):
  """Thrown when the rcon password is incorrect."""
  pass

#------------------------------
class RconError(Exception):
  """Thrown when something bad happens in the rcon library."""
  pass

#------------------------------
class RconResponse(object):
  """This object encapsulates an rcon response. It enables you to
  easily grab bits and pieces of the message."""
  
  #==============================
  def __init__(self, data):
    self.data = data[5:]
    
  #==============================
  def get_byte(self):
    ret = ord(self.data[0])
    self.data = self.data[1:]
    return ret

  #==============================
  def get_char(self):
    ret = str(data[0])
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
class HL1Network(object):
  """A class to handle networking for HL1 servers. It contains methods to do
  rcon authentication and to send rcon commands."""
  
  #==============================
  def __init__(self, host, port, password):
    self.ip, self.port, self.password, = socket.gethostbyname(host), port, password
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #self.sock.bind(('192.168.0.2', 97778))
    self.sock.connect((self.ip, self.port))
    
    if password:
      self.authenticate()
   
  #============================== 
  def authenticate(self, password=None):
    """Authenticates to the server. If the password is not passed, it uses
    self.password instead."""
    
    if password:
      self.password = password
    
    data = self.send_packet("challenge rcon")
    self.challenge_id = data.get_string().split(' ')[2].strip()
    # This is just to test to see if our password worked. It will
    # throw an exception if it wasn't the right password.
    self.command("say")
  
  #==============================
  def send_packet(self, data):
    """Sends a packet to the server and returns a RconResponse object."""
    
    self.sock.send("\xFF\xFF\xFF\xFF%s\x00" % data)
    #log.debug("Sending: %s" % data)
    response = RconResponse(self.receive_packets())
  
    if str(response) == "Bad rcon_password.\n\x00\x00":
      raise PasswordError('Invalid rcon password')
    if str(response) == "Bad challenge.\n\x00\x00":
      raise Exception("BAD CHALLENGE???? WHY???")
    return response
  
  #==============================
  def receive_packets(self):
    """Receives packets of data."""
    
    data = self.sock.recv(4096)
    #log.debug("Receiving: %s" % data)
    return data
    #if data[0] == '\xFE':
    #  num_packets = ord(data[8]) & 15
    #  packets = [' ' for i in range(num_packets)]
    #  for i in range(num_packets):
    #    if i != 0:
    #      data = self.sock.recv(4096)
    #    index = ord(data[8]) >> 4
    #    packets[index] = data[9:]
    #  data = ''
    #  for i, packet in enumerate(packets):
    #    data = data + packet
    #return data
   
  #============================== 
  def command(self, *args, **kwargs):
    """Sends an rcon command to the server. It takes a variable amount of
    parameters which it separates by spaces before sending to the server."""
    
    command = "rcon %s \"%s\" %s" % (self.challenge_id, self.password, ' '.join(args))
    return self.send_packet(command)
  
  #============================== 
  def close(self):
    """Closes down this network connection."""
    
    self.sock.close()

#------------------------------
class RconClient(object):
  """A class that has knowledge of rcon commands and allows the user
  to send rcon commands to the server."""
  
  #============================== 
  def __init__(self, network=None):
    self.cache = {
      'status': {},
      'players': {} # Indexed by uniqueid
    }
    
    self.network = network
  
  #============================== 
  def set_network(self, network):
    """Sets the network for this Rcon object."""
    
    if self.network:
      self.network.close()
    self.network = network
  
  #==============================
  def command(self, *args, **kwargs):
    """This is just a passthrough method for the Network class"""
    
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
    If reverse is passed, then players who don't match are returned."""
     
    players = {}
    
    if names:
      # Get an up-to-date list of users
      self.users()
      
      for name in names:
          regexp = self._regex_compile(name)      
          for uniqueid in self.cache["players"]:
            player = self.cache["players"][uniqueid]
            if regexp.search(player['name']):
              players[player['uniqueid']] = player
      
      # Might not be a terribly efficient way of doing this.
      if reverse:
        revplayers = {}
        for uniqueid in self.cache["players"]:
          player = self.cache["players"][uniqueid]
          if uniqueid not in players:
            revplayers[player['uniqueid']] = player
        players = revplayers
        
    return players
  
  #==============================
  def _set_difference_intersection(self, a, b):
    a = set(a)
    return (a.difference(b), a.intersection(b))
  
  #==============================
  def kick(self, uniqueid, reason=''):
    """Kick a user based on their uniqueid."""
    self.command("kick", "#%s" % uniqueid, reason)
  
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
      self.command("banid", duration, "%s" % uniqueid, "kick")
    else:
      self.command("banid", duration, "%s" % uniqueid)
    
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
  def unban(self, uniqueid, writeid=False):
    """Unbans users from the server. Be sure to call writeid to undo the ban from the config."""
    
    self.command("removeid", "%s" % uniqueid) 

  #==============================
  def say(self, text):
    """Makes the server say something."""
    
    self.command("say", text)
  
  #==============================
  def hsay(self, hostname, text):
    """Makes the server say something with a particular hostname prefix. E.g. <hostname> HI!"""
    
    #old_hostname = self.cvar("hostname")
    self.hostname(hostname)
    self.say(text)
    #self.hostname(old_hostname)
  
  #==============================
  def hostname(self, hostname):
    """Sets the hostname of the server."""
    
    if not hostname:
      hostname = '""' # In case we want the empty string as our hostname
      
    self.command("hostname", hostname)
    
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
    
    ret = None
    cvar_response = self.command("%s" % cvar)
    m = re.match('^"(.*?)" (is|=) "(.*?)"', str(cvar_response))
    if m:
      ret = m.group(3)
    
    if value:
      self.command(cvar, value)
    return ret
  
  #==============================
  def toggle_cvar(self, cvar):
    """Toggles a cvar on or off if it is toggable."""
    
    value = self.cvar(cvar)
    if value == "1":
      value = "0"
    else:
      value = "1"
    self.cvar(cvar, value)
  
  #==============================
  def exec_(self, config):
    """Sends a exec command to load a config."""
    
    self.command("exec", config)
  
  #==============================
  def writeid(self):
    """Updates the banned.cfg with the current bans."""
    
    self.command("writeid")
  
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
  #  # Retrieve the header's keys (I know it's not really csv)
  #  keys = re.split('\s+', lines[index])
  #  keys.pop(0)
  #  index += 1
  #  
  #  for line in lines[index:]:
  #    line = line[4:]
  #    
  #    #print re.split('\s', line)
  
  #==============================
  def users(self):
    """Gets a list of users from the server and returns it. It also saves
    the data in self.cache['players']."""
    
    # Clear the cache
    self.cache['players'] = {}
    
    response = self.command('users')
    lines = str(response).split('\n')
    
    header = lines[0]
    # Gets rid of unecessary crap
    lines = lines[2:-2]
    
    keys = header.split(' : ')
    for line in lines:      
      values = line.split(' : ')
      player_dict = {}
      for i in enumerate(values):
        player_dict[keys[i[0]]] = i[1].strip()
      self.cache['players'][player_dict['uniqueid']] = player_dict
    
    return self.cache['players']

if __name__ == "__main__":
  rcon = RconClient(HL1Network("69.65.58.49", 27015, "fscfz"))
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
  
  #rcon.command('logaddress_add %s %s' % ('nobinds.ath.cx', 27129))  
  #sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  #sock.bind(('', 27129))
  ##
  #data = ' '
  #while data:
  #  data = sock.recv(9096)
  #  print data
  
  #from twisted.internet.protocol import DatagramProtocol
  #from twisted.internet import reactor
  #
  #class Echo(DatagramProtocol):      
  #  def datagramReceived(self, data, (host, port)):
  #    print "received %r from %s:%d" % (data, host, port)
  #    self.transport.write(data, (host, port))
  #
  #reactor.listenUDP(27129, Echo())
  #reactor.run()
  