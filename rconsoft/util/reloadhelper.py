# Most of the code taken from Paste/PasteScript/PasteDeploy
# Modified for the uses of RconSoft.

# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

import os
import sys
import subprocess
import logging

jython = sys.platform.startswith('java')
_reloader_environ_key = '_RCONSOFT_PYTHON_RELOADER_SHOULD_RUN'
_monitor_environ_key = '_RCONSOFT_MONITOR_SHOULD_RUN'

log = logging.getLogger('general')

#==============================
def install():
  jython_monitor = False
  if jython:
    # JythonMonitor raises the special SystemRestart
    # exception that'll cause the Jython interpreter to
    # reload in the existing Java process (avoiding
    # subprocess startup time)
    try:
      from rconsoft.util.reloader import JythonMonitor
    except ImportError:
      pass
    else:
      jython_monitor = JythonMonitor()
  
  if not jython_monitor:
    if os.environ.get(_reloader_environ_key):
      from rconsoft.util import reloader
      reloader.install()
    else:
      return restart_with_reloader()

#==============================
def _turn_sigterm_into_systemexit():
  """
  Attempts to turn a SIGTERM exception into a SystemExit exception.
  """
  try:
    import signal
  except ImportError:
    return
  def handle_term(signo, frame):
    raise SystemExit
  signal.signal(signal.SIGTERM, handle_term)

#==============================
def quote_first_command_arg(arg):
  """
  There's a bug in Windows when running an executable that's
  located inside a path with a space in it.  This method handles
  that case, or on non-Windows systems or an executable with no
  spaces, it just leaves well enough alone.
  """
  if (sys.platform != 'win32' or ' ' not in arg):
    # Problem does not apply:
    return arg
  try:
    import win32api
  except ImportError:
    raise ValueError(
      "The executable %r contains a space, and in order to "
      "handle this issue you must have the win32api module "
      "installed" % arg)
  arg = win32api.GetShortPathName(arg)
  return arg

#==============================
def restart_with_reloader():
  return restart_with_monitor(reloader=True)

#==============================
def restart_with_monitor(reloader=False):
  if reloader:
    log.info('Starting subprocess with file monitor')
  else:
    log.info('Starting subprocess with monitor parent')
  while 1:
    args = [quote_first_command_arg(sys.executable)] + sys.argv
    new_environ = os.environ.copy()
    if reloader:
      new_environ[_reloader_environ_key] = 'true'
    else:
      new_environ[_monitor_environ_key] = 'true'
    proc = None
    try:
      try:
        _turn_sigterm_into_systemexit()
        proc = subprocess.Popen(args, env=new_environ)
        exit_code = proc.wait()
        proc = None
      except KeyboardInterrupt:
        print '^C caught in monitor process'
        return 1
    finally:
      if (proc is not None and hasattr(os, 'kill')):
        import signal
        try:
          os.kill(proc.pid, signal.SIGTERM)
        except (OSError, IOError):
          pass
        
    if reloader:
      # Reloader always exits with code 3; but if we are
      # a monitor, any exit code will restart
      if exit_code != 3:
        return exit_code