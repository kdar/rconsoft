# Read LICENSE for licensing details.

import re

from rconsoft import rcon_client, rcon_receiver

#------------------------------
class RconTracker(object):
  #==============================
  def __init__(self):
    self.rcon_password_regex = re.compile(r'rcon_password "?(?P<password>[^"]*)"? *$')
    
  #==============================
  def setup(self):
    rcon_receiver.event.connect(self.on_rcon_event)
    
    # Retrieve all the information we can from the server before
    # we start to track changes.
    
    #==============================
    # This gets called once the users command succeeds.
    def got_users(players):       
      #==============================
      # This gets called once the user command succeeds.
      def got_user(player):
        # Try to determine the person's team based on their model.
        # CAVEAT: If the person is in spectator, then their model will
        # be the last model they used. So you can't really tell if they're
        # spectating or on a team.
        # Teams and their corresponding models:
        #   CT      TERRORIST
        #  urban     terror
        #  gsg9      leet
        #  sas       arctic
        #  gign      guerilla
        m = player['model']
        if m == 'urban' or m == 'gsg9' or m == 'sas' or m == 'gign':
          player['team'] = 'CT'
        else:
          player['team'] = 'TERRORIST'
      
      for uniqueid in players:
        player = players[uniqueid]
        rcon_client.user(player['uniqueid']).addCallback(got_user)
      
    rcon_client.users().addCallback(got_users)
  
  #==============================
  def on_rcon_event(self, event, data, **kwargs):
    if event == 'user_connected' or event == 'user_joined_team' or event == 'user_changed_name':
      rcon_client.players.setdefault(data['uniqueid'], {}).update(data)
     
      # Get some extra info about this user.
      rcon_client.user(data['uniqueid'])
      
    if event == 'user_disconnected':
      del rcon_client.players[data['uniqueid']]
      
    elif event == 'server_cvar':
      pass
      
    elif event == 'rcon_command':
      m = self.rcon_password_regex.match(data['command'])
      if m:
        print 'Warning. Someone changed the password: %s' % m.groupdict()['password']
