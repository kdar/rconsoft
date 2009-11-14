#!/usr/bin/env python
# Read LICENSE for licensing details.
"""The main application which runs RconSoft."""

import sys
import logging
import logging.handlers
import datetime
from optparse import OptionParser

from twisted.internet import reactor

import rconsoft
from rconsoft.util import reloadhelper
from rconsoft.config import config
import rconsoft.plugins
from rconsoft.plugins import Plugin
from rconsoft.controller import Controller

# Set up logging. One log is a general log of general things. The other
# one isa detailed logs that spews out a bunch of different information.

log = logging.getLogger('general')
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
log.addHandler(sh)

log_detail = logging.getLogger('detail')
log_detail.setLevel(logging.DEBUG)
fh = logging.handlers.RotatingFileHandler('%s.log' % __name__, maxBytes=1*1024*1024, backupCount=5)
#fh = logging.FileHandler('%s.log' % __name__, 'a')
fh.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
log_detail.addHandler(fh)

#------------------------------
class RconSoft(object):       
  #==============================
  def run(self):
    log.debug('Starting %s %s' % (rconsoft.__name__, rconsoft.__version__))
    
    self._init_plugins()
    self.controller = Controller()
    self.controller.setup()
    
    reactor.run()
  
  #==============================
  def _init_plugins(self):
    # Load all the plugins
    rconsoft.plugins.load_all()
    # Instantiate all the plugins.
    Plugin.plugins = rconsoft.plugins.PluginList([p() for p in Plugin.plugins])
  
#==============================
def main_func():
  parser = OptionParser()
  parser.add_option('-r', '--reload',
    action='store_true', dest='reload', default=False,
    help='reloads the program automatically on code change')
  
  (options, args) = parser.parse_args()
  
  log_detail.debug('App started: %s' % datetime.datetime.now())

  # If install returns 1, it means that a keyboard interrupt was issued. So we do
  # not want to run rconsoft in that case.
  if options.reload and reloadhelper.install() == 1:
    return
    
  rconsoft = RconSoft()
  rconsoft.run()

#==============================
if __name__ == "__main__":
  print 'Please install the application before running.'
  
  