http://outroot.com/blog/2009/12/02/rconsoft-hl1-chat-command-rcon-tool/

What is it?
===========

It's a python program that allows you to type chat commands on your private HL1 server. For example, once you set this up you can hit 'y' in game and type '.lo3'. It will then do the live on three sequence for you. There are also .id, .kick, .kb, .ban, .r (restart), and other commands you can do. All these commands are implemented via plugins. Check out the rconsoft/plugins directory for the plugins.

Prerequisites
=============

python 2.5.x - 2.6.x

All other dependencies are in setup.py.

Installation
============

python setup.py develop

If you use 'install' instead, I'm not sure if it would work because it won't be able to find the configuration file.

Configuration
=============

The configuration file is located in rconsoft/rconsoft.conf.

The main configuration options you have to worry about are located under [ "rcon" ]. Set the "host" to the HL1 server you will be playing on, along with the port and the rcon password of the server.

Under [[ "remote" ]], you must put the IP or host of the computer that is running rconsoft. The port must be accessible to the outside world, particularly the HL1 server.

After you configure those few items, the program should run and you should be able to type commands inside the video game.

Running
=======

$ rconsoft

Development status
==================

I am no longer actively developing this application since I no longer play counter-strike. I may be of some help if someone needs it, but I can't do full time bug fixing and development.