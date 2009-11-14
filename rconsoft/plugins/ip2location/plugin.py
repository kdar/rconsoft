# Read LICENSE for licensing details.

import re
import os

import mechanize
from twisted.internet import reactor

from rconsoft.plugins import Plugin
from rconsoft.dispatch.dispatcher import Signal
from rconsoft import rcon_client, command_handler
from rconsoft.config import cget, has_access
from rconsoft.command import get_dispatcher, command

#------------------------------
class Ip2LocationPlugin(Plugin):
  """Supported commands: ip2l"""
  
  #==============================
  def __init__(self, *args, **kwargs):
    Plugin.__init__(self, *args, **kwargs)
    
    command_handler.event.connect(get_dispatcher(self))
    
    self.parse_re = None

  #==============================
  @command('ip2l')
  def on_command(self, command, params, silent, **kwargs):
    extra = kwargs.get('extra', {})
    uniqueid = extra.get('uniqueid', '')
    
    # We don't have access. Return.
    if not has_access(uniqueid, 'admin'):
      # Keep processing other plugins.
      return True

    if command == 'ip2l' and params:
      reactor.callInThread(self.display_name, params)

    # Keep processing other plugins.
    return True
  
  #==============================
  def display_name(self, name):
    if not name:
      return
    
    # Just get a single player based on the name. In the future I may
    # make this thing get multiple player's location info.
    players = rcon_client.get_players(names=[name])
    print players
    if players:
      player = players.values()[0]
    else:
      return
    
    # They don't have location information. Go grab it.
    if 'country' not in player:
      if 'ip' not in player:
        print 'Error: Player has no ip.'
        return
      
      data = self.lookup_ip(player['ip'])
      
      # Save the information for later
      player.update(data)
      
    rcon_client.hsay(player['name'], '%s, %s, %s (%s)' % (player['city'], player['region'], player['country'], player['area_code']))
    
  #==============================
  def lookup_ip(self, ip):
    if not ip:
      return    
    
    # Grab the location of our cookies
    path = cget('plugins', 'ip2location', 'cookies_path', default=os.path.join(os.path.dirname(__file__), 'cookies'))
    cookie_path = os.path.join(path, 'cookies.txt')
    
    # Use the mozilla cookie jar. Just because.
    cj = mechanize.MozillaCookieJar()
    cj.filename = cookie_path

    # Attempt to load the cookie file at this point
    if os.path.exists(cookie_path):
      cj.load()
    
    # Create our browser and set the cookiejar
    br = mechanize.Browser()
    br.set_cookiejar(cj)
    
    # If the cookie jar contains no cookies, get them.
    if not cj._cookies:
      self.get_cookie(br)
    
    response = br.open('http://www.ip2location.com/%s' % ip)    
    data = response.read()
    
    return self.parse_html(data)
    
  #==============================
  def parse_html(self, data):
    # Clean up the html before processing it.
    data = data.replace('\n', '')
    # I would use a python (x)html parsing library but I don't feel comfortable
    # using any of them right now because they're either in a state of turmoil
    # (meaning they may not be upgraded to python 3.0 and beyond) or they can't
    # parse malformed (x)html properly.
    if not self.parse_re:
      self.parse_re = re.compile(
        r'.+<span id="dgLookup__ctl2_lblICountry">(?P<country>.*?)</span>'
        r'.+<span id="dgLookup__ctl2_lblIRegion">(?P<region>.*?)</span>'
        r'.+<span id="dgLookup__ctl2_lblICity">(?P<city>.*?)</span>'
        r'.+<span id="dgLookup__ctl2_lblIISP">(?P<isp>.*?)</span>'
        r'.+<span id="dgLookup__ctl2_lblIAreaCode">(?P<area_code>.*?)</span>',
        re.IGNORECASE)
    m = self.parse_re.match(data)
    if m:
      return m.groupdict()
    return {}
  
  #==============================
  def get_cookie(self, browser):
    browser.open('http://www.ip2location.com/login.aspx')
  
    browser.select_form('Form1')
    browser['txtEmailAddress'] = cget('plugins', 'ip2location', 'login')
    browser['txtPassword'] = cget('plugins', 'ip2location', 'password')
    browser['chkRememberMe'] = ['on']
    
    browser.submit()
    
    # Kind of an ugly hack but it allows me to not have to pass in the
    # cookiejar as well.
    browser._ua_handlers['_cookies'].cookiejar.save()
