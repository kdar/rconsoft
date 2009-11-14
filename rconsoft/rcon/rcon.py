import socket
import struct
import re
import time

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
    # throw an exception if it wasn't.
    self.command("say")
  
  #==============================
  def send_packet(self, data):
    """Sends a packet to the server and returns a RconResponse object."""
    
    self.sock.send("\xFF\xFF\xFF\xFF%s\x00" % data)
    response = RconResponse(self.sock.recv(4096))
    
    if str(response) == "Bad rcon_password.\n\x00\x00":
      raise PasswordError('Invalid rcon password')
      
    return response
   
  #============================== 
  def command(self, *args, **kwargs):
    """Sends an rcon command to the server. It takes a variable amount of
    parameters which it separates by spaces before sending to the server."""
    
    command = "rcon %s \"%s\"" % (self.challenge_id, self.password)
    for arg in args:
      command = "%s %s" % (command, str(arg))
    return self.send_packet(command)

#------------------------------
class Rcon(object):
  """A class that has knowledge of rcon commands and allows the user
  to send rcon commands to the server."""
  
  #============================== 
  def __init__(self, network):
    self.cache = {
      'status': {},
      'players': {}
    }
    
    self.network = network
  
  #==============================
  def command(self, *args, **kwargs):
    """This is just a passthrough method for the Network class"""
    
    return self.network.command(*args, **kwargs)
    
  #==============================
  def get_players(self, names=[], reverse=False):
    """Returns a list of players for a given list of names. The names
    are treated as regular expressions. If reverse is passed, then players
    who don't match are returned."""
    
    players = []
    
    if names:
      # Get an up-to-date list of users
      self.users()
      
      for name in names:
          regexp = re.compile(name, re.IGNORECASE)      
          for userid in self.cache["players"]:
            player = self.cache["players"][userid]
            if regexp.search(player['name']):
              players.append(player)
      
      # Might not be a terribly efficient way of doing this.
      if reverse:
        revplayers = []
        for userid in self.cache["players"]:
          player = self.cache["players"][userid]
          if player not in players:
            revplayers.append(player)
        players = revplayers
        
    return players
  
  #==============================
  def kick(self, steamid):
    """Kick a user based on their steamid."""
    self.command("kick", "#%s" % steamid)
  
  #============================== 
  def kickx(self, steamids=[], names=[]):
    """Kicks users from the server. You can pass both a list of steamids
    or a list of names. The names will be treated as regular expressions."""
      
    players = self.get_players(names=names)
    steamids.extend([player["uniqueid"] for player in players])
    
    for steamid in set(steamids):
      self.kick(steamid)
  
  #==============================  
  def rkickx(self, names=[]):
    """Reverse kicks a list of names treated as regular expressions. Meaning, anyone
    who doesn't match these expressions are kicked."""
    
    players = self.get_players(names=names, reverse=True)
    for player in players:
      self.kick(player["uniqueid"])
    
  #==============================
  def ban(self, steamid, duration=0):
    """Bans a user from the server. Be sure to call writeid to write the bans to the config."""
    
    self.command("banid", duration, "#%s" % steamid, "kick")
    
  #============================== 
  def banx(self, steamids=[], names=[], duration=0):
    """Bans users from the server. You can pass both a list of steamids
    or a list of names. The names will be treated as regular expressions."""
      
    players = self.get_players(names=names)
    steamids.extend([player["uniqueid"] for player in players])
    
    for steamid in set(steamids):
      self.ban(steamid=steamid, duration=duration)
    self.writeid()
    
  #==============================  
  def rbanx(self, names=[]):
    """Reverse bans a list of names treated as regular expressions. Meaning, anyone
    who doesn't match these expressions are banned."""
    
    players = self.get_players(names=names, reverse=True)
    for player in players:
      self.ban(player["uniqueid"])
    self.writeid()
  
  #==============================
  def unban(self, steamid, writeid=False):
    """Unbans users from the server. Be sure to call writeid to undo the ban from the config."""
    
    self.command("removeid", "#%s" % steamid) 

  #==============================
  def say(self, text):
    """Makes the server say something."""
    
    self.command("say", text)
  
  #==============================
  def hnsay(self, hostname, text):
    """Makes the server say something with a particular hostname prefix. E.g. <hostname> HI!"""
    
    old_hostname = self.cvar("hostname")
    self.hostname(hostname)
    self.say(text)
    self.hostname(old_hostname)
  
  #==============================
  def hostname(self, hostname):
    """Sets the hostname of the server."""
    
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
    
    cvar_response = self.command("%s" % cvar)
    m = re.match('^"(.*?)" (is|=) "(.*?)"', str(cvar_response))
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
      self.cache['players'][player_dict['userid']] = player_dict
    
    return self.cache['players']

if __name__ == "__main__":
  rcon = Rcon(HL1Network("69.65.58.49", 27015, "fscfz"))
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
  