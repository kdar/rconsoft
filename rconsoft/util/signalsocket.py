import socket
import time
import select
import logging
from threading import Thread

from rconsoft.dispatch.dispatcher import Signal

log = logging.getLogger(__name__)

# I would have used python's SocketServer, but they don't have a corresponding
# SocketClient. I find this to be a shame. I could have programmed my own SocketClient
# but I rather just create my own simple socket class.

#------------------------------
class SignalSocket(Thread):
  """A threaded socket class based on signals. It can become a client or a server.
  Hook into the signals in order to do useful things with the class."""
  
  #==============================
  def __init__(self, host, port, protocol="tcp"):
    self.daemon = True
    Thread.__init__(self)
    
    self._init_signals()
    
    self.host = socket.gethostbyname(host)
    self.port = port
    self.protocol = protocol
    self._close = False
    self.max_packet_size = 8192
    
    self.sock = False
    self.clientsock = False
    # The socket we are communicating with. It will either
    # be self.sock or self.clientsock depending on our socket
    # configuration (protocol+mode)
    self.commsock = False
    
  #============================== 
  def _init_signals(self):
    self.pre_connect = Signal()
    self.post_connect = Signal()
    
    self.pre_receive = Signal()
    self.post_receive = Signal()
    
    self.pre_send = Signal()
    self.post_send = Signal()
    
    self.post_accept = Signal()
    
    self.ready = Signal()
  
  #============================== 
  def send(self, data):
    self.pre_send.send(sender=self.__class__)
    self.commsock.send(data)
    self.post_send.send(sender=self.__class__, data=data)
    
  #============================== 
  def recv(self):    
    self.pre_receive.send(sender=self.__class__)
    data = self.commsock.recv(self.max_packet_size)
    self.post_receive.send(sender=self.__class__, data=data)
    return data
    
  #============================== 
  def close(self):
    self._close = True
    if self.sock:
      self.sock.close()
      self.sock = False
    if self.clientsock:
      self.clientsock.close()
      self.clientsock = False
    self.commsock = False
  
  #============================== 
  def set_protocol(self, protocol=None):
    self.close()
    if not protocol:
      protocol = self.protocol
    self.protocol = protocol
    
    if protocol == "tcp":
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    elif protocol == "udp":
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      
  #============================== 
  def client(self):
    while self.isAlive():
      self.close()
      time.sleep(0.05)
      
    self.set_protocol()
      
    self.mode = "client"
    self.pre_connect.send(sender=self.__class__)
    self.sock.connect((self.host, self.port))
    self.post_connect.send(sender=self.__class__)
    self.start()
  
  #============================== 
  def server(self):
    while self.isAlive():
      self.close()
      time.sleep(0.05)
      
    self.set_protocol()
      
    self.mode = "server"
    self.sock.bind((self.host, self.port))
    if self.protocol == "tcp":
      self.sock.listen(5)
    self.start()
      
  #============================== 
  def run(self):
    self._close = False
    data = False    
    self.commsock = self.sock
    if self.mode == "server" and self.protocol == "tcp":
      # this mode and protocol is ready at this point
      self.ready.send(sender=self.__class__)
      
      self.clientsock, addr = self.sock.accept()      
      self.commsock = self.clientsock      
      self.post_accept.send(sender=self.__class__)
    else: # all other modes and protocols are ready at this point
      self.ready.send(sender=self.__class__)
    
    while not self._close:      
      data = self.recv()
      if not data:
        self.close()
        