# Read LICENSE for licensing details.
"""A plugin module for RconSoft. Concepts borrowed from
Marty Alchin <http://martyalchin.com/2008/jan/10/simple-plugin-framework/>"""

import logging
import imp
import os
import sys
from warnings import warn

from rconsoft.config import cget, INSTALLDIR

log = logging.getLogger('general')

#__all__ = ['CommandProvider', 'load_all']

#------------------------------
class PluginList(list):
  #==============================
  def find(self, class_name):
    """Allows you to find a plugin by its class name."""
    
    for c in self:
      if c.__name__ == class_name:
        return c
    return None
  
#------------------------------
class PluginMeta(type):
  """Plugin meta provides a means of registering and accessing plugins.
  This class should be metaclassed and not used directly."""
  
  #==============================
  def __init__(cls, name, bases, attrs):
    if not hasattr(cls, 'plugins'):
      # This branch only executes when processing the mount point itself.      
      cls.plugins = PluginList()
      cls.__plugin_names__ = [] # Used so we can prevent the same plugin being registered multiple times.
    else:
      # This must be a plugin implementation, which should be registered.
      if cls.__name__ not in cls.__plugin_names__: # Don't register the same plugin multiple times
        cls.plugins.append(cls)
        cls.__plugin_names__.append(cls.__name__)
      else:
        log.debug('Plugin already registered: %s' % cls.__name__)

#------------------------------
class Plugin(object):
  """
  Mount point for plugins which provide functionality for the application.

  Plugins implementing this reference should provide the following attributes:

  ========  ========================================================
  FIXME: documentation of what plugins should provide goes here
  ========  ========================================================
  """
  __metaclass__ = PluginMeta

#------------------------------
#class Plugin(object):
#  """
#  FIXME: Documentation needed
#  """
#  __metaclass__ = PluginMeta
#  
#  #==============================
#  def __new__(cls, *args, **kwargs):
#    self = object.__new__(cls)
#    
#    if self._commands:
#      command_plugins.append(self)
#    
#    return self
#  
#  #==============================
#  @classmethod
#  def commands(cls, list):
#    import sys
#
#    frame = sys._getframe(1)
#    locals_ = frame.f_locals
#    
#    # Some sanity checks
#    assert locals_ is not frame.f_globals and '__module__' in locals_, \
#      'commands() can only be used in a class definition'
#    
#    locals_.setdefault('_commands', []).extend(list)

#------------------------------
#class PluginManager(object):
#  #==============================
#  def __init__(self):
#    self.plugins = []
#
#  #==============================
#  def __contains__(self, cls):
#    return cls in self.plugins
#
#  #==============================
#  def __getitem__(self, cls):
#    plugin = self.plugins.get(cls)
#    if not plugin:
#      if cls not in PluginMeta._plugin:
#        raise TracError('Component "%s" not registered' % cls.__name__)
#      try:
#        plugin = cls(self)
#      except TypeError, e:
#        raise Exception('Unable to instantiate component %r (%s)' % (cls, e))
#    return plugin

#==============================
def load_all():
  """Loads all the plugins from the directories specified by the config."""
  
  plugins = cget('global', 'plugins', default=[])
  paths = cget('global', 'directories', 'plugins', default=[os.path.join(INSTALLDIR, 'plugins')])
  
  for plugin in plugins:    
    try:
      moduleInfo = imp.find_module(plugin, paths)
      log.debug('Found plugin "%s", attempting to load...' % plugin)
      module = imp.load_module(plugin, *moduleInfo)
    except ImportError:
      sys.modules.pop(plugin, None)
      log.debug('Could not import plugin: %s. Is the configuration correct?' % plugin)
      raise
    except:
      sys.modules.pop(plugin, None)
      raise
    log.debug('Plugin loaded: %s' % module)
    
    if module.__name__ in sys.modules:
      sys.modules[module.__name__] = module
    #full_module_name = '%s.%s' % (__name__, module.__name__)
    #if full_module_name not in sys.modules:
    #  sys.modules[full_module_name] = module
 
# Old function to load all plugins in a certain directory
#==============================
#def load_all():  
#  paths = config['directories']['plugins']
#  
#  for path in paths:
#    names = os.listdir(path)
#    for name in names:
#      if name.startswith('_'):
#        continue
#      moduleInfo = imp.find_module(name, [path])
#      try:
#        log.debug("Found plugin \"%s\", attempting to load..." % name)
#        module = imp.load_module(name, *moduleInfo)
#      except:
#        sys.modules.pop(name, None)
#        raise
#      log.debug("Plugin loaded: %s" % module)
#      
#      if module.__name__ in sys.modules:
#        sys.modules[module.__name__] = module

#==============================
# Loads python eggs. Not implemented.
# http://base-art.net/Articles/64/
#def loadall(entry_points):
#  loaded = {}
#  for entry_point in entry_points:
#    print entry_point
#    for ep in iter_entry_points(entry_point):
#      print ep
#      loaded[ep.name] = True
#      log.debug('%s load plugin %s', __name__, ep)
#      try:
#        plugcls = ep.load()
#      except KeyboardInterrupt:
#        raise
#      except Exception, e:
#        # never want a plugin load to kill the test run
#        # but we can't log here because the logger is not yet
#        # configured
#        warn("Unable to load plugin %s: %s" % (ep, e), RuntimeWarning)
#        continue
