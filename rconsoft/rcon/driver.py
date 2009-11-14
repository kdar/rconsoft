"""The Rcon driver."""

from rconsoft.dispatch.dispatcher import Signal
from rconsoft.util.signalsocket import SignalSocket
from rconsoft.config import config

#------------------------------
class RconDriver(object):
  #==============================
  def __init__(self):
    self._init_signals()
    
  #==============================
  def _init_signals(self):
    pass
  
  #==============================
  def run(self):    
    self.sock = SignalSocket(config['rcon']['local']['host'], int(config['rcon']['local']['port']), 'udp')
    self.sock.post_receive.connect(self.on_receive)
    self.sock.server()
  
  #==============================
  def on_receive(self, **kwargs):
    print kwargs.get('data')