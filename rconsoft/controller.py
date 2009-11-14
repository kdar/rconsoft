# Read LICENSE for licensing details.

"""The main controller which orchestrates everything."""

import logging

from twisted.internet import reactor

from rconsoft.rcon.client import HL1Network
from rconsoft.rcon.tracker import RconTracker
from rconsoft.config import cget
from rconsoft import command_handler, rcon_client, rcon_receiver

log = logging.getLogger('general')
log_detail = logging.getLogger('detail')

#------------------------------
class Controller(object):
  #==============================
  def __init__(self):
    self.rcon_tracker = None
  
  #==============================
  def setup(self):
    rcon_receiver.event.connect(self.on_rcon_event)
    reactor.listenUDP(interface=cget('rcon', 'local', 'host'), port=int(cget('rcon', 'local', 'port')), protocol=rcon_receiver)
    
    network = HL1Network(cget('rcon', 'host'), int(cget('rcon', 'port')), cget('rcon', 'password'))
    network.ready.connect(self.on_rcon_client_ready)
    rcon_client.set_network(network)
    rcon_client.set_default_hostname(cget('game', 'hostname'))
    reactor.listenUDP(0, network)
  
  #==============================
  def on_rcon_client_ready(self, **kwargs):
    #rcon_client.command('logaddress_del %s %s' % (config['rcon']['remote']['host'], config['rcon']['remote']['port']))
    rcon_client.command('logaddress_add %s %s' % (cget('rcon', 'remote', 'host'), cget('rcon', 'remote', 'port')))
    
    if not self.rcon_tracker:
      self.rcon_tracker = RconTracker()
      self.rcon_tracker.setup()
    
  #============================== 
  def on_rcon_event(self, event, data, **kwargs):
    # Process commands
    if event == 'user_say':
      if data['message'].startswith('.'):
        command_handler.process(data['message'][1:], extra=data)
        log_detail.debug('[%s] Typed command: %s' % (data['name'], data['message']))
      elif data['message'].startswith('/'):
        command_handler.process(data['message'][1:], extra=data, silent=True)
        log_detail.debug('[%s] Typed command: %s' % (data['name'], data['message']))
    