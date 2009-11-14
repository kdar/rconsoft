#!/usr/bin/env python
# Read LICENSE for licensing details.

import sys
import textwrap
import glob
import shutil
import os

app_name = 'rconsoft'

#-----------------------------
# Do some checks

if sys.version_info < (2, 4, 0):
  sys.stderr.write(app_name+' requires Python 2.4 or newer.\n')
  sys.exit(-1)
  
try:
  from setuptools import setup, find_packages
except ImportError:
  from ez_setup import use_setuptools
  use_setuptools()
  from setuptools import setup, find_packages

#-----------------------------
# Get all of our packages
#plugin_names = find_packages('plugins')
#plugins = [app_name+'.plugins.'+p for p in plugin_names]
#packages = find_packages(exclude=['ez_setup', 'tests', 'tests.*', 'plugins', 'plugins.*'])+[app_name+'.plugins']+plugins
#package_dir = {app_name+'.plugins': 'plugins'}
#for name in plugin_names:
#  package_dir[app_name+'.plugins.' + name] = 'plugins/' + name

packages = find_packages(exclude=['ez_setup', 'tests', 'tests.*'])
package_dir = {}

version = '0.1'
setup(
  # Metadata
  name=app_name,
  version=version,
  author='Kevin Darlington',
  url='',
  author_email='no@binds.net',
  download_url='',
  description='A program to interact with HL servers.',
  
  install_requires=[
    'configobj', 'twisted', 'mechanize'
  ],
  
  #install_requires=[
  #      "Routes>=1.10.1", "WebHelpers>=0.6.3", "Beaker>=1.1.3",
  #      "Paste>=1.7.2", "PasteDeploy>=1.3.2", "PasteScript>=1.7.3",
  #      "FormEncode>=1.2.1", "simplejson>=2.0.6", "decorator>=2.3.2",
  #      "nose>=0.10.4", "Mako>=0.2.4", "WebOb>=0.9.5", "WebError>=0.10.1",
  #      "WebTest>=1.1", "Tempita>=0.2",
  #  ],
  #  dependency_links=[
  #      "http://www.pylonshq.com/download/0.9.7"
  #  ],
  #  classifiers=[
  #      "Development Status :: 5 - Production/Stable",
  #      "Intended Audience :: Developers",
  #      "License :: OSI Approved :: BSD License",
  #      "Framework :: Pylons",
  #      "Programming Language :: Python",
  #      "Topic :: Internet :: WWW/HTTP",
  #      "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
  #      "Topic :: Internet :: WWW/HTTP :: WSGI",
  #      "Topic :: Software Development :: Libraries :: Python Modules",
  #          ],
  #  extras_require = {
  #      'cheetah': ["Cheetah>=1.0", "TurboCheetah>=0.9.5"],
  #      'myghty': ["Myghty>=1.1"],
  #      'kid': ["kid>=0.9", "TurboKid>=0.9.1"],
  #      'genshi': ["Genshi>=0.4.4"],
  #      'jinja2': ['Jinja2'],
  #      'full': [
  #          "docutils>=0.4", "elementtree>=1.2.6",
  #          "Pygments>=0.7", "Cheetah>=1.0",
  #          "TurboCheetah>=0.9.5", "kid>=0.9", "TurboKid>=0.9.1",
  #          'Genshi>=0.4.4',
  #      ],
  #  },
  
  # Installation data
  packages=packages,
  package_dir=package_dir,
  include_package_data=True,
  #scripts=['scripts/'+app_name],
  entry_points = {
    'console_scripts': [
      '%s = %s.app:main_func' % (app_name, app_name)
    ]
  }
)

