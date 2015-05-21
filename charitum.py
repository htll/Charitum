#!/usr/bin/env python
"""Charitum.py: an extensible IRC bot"""

# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# <s0lll0s@blinkenshell.org> wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. S0lll0s
# ----------------------------------------------------------------------------

__author__ = "S0lll0s"
__copyright__ = "S0lll0s aka Sol Bekic"
__license__ = "BEER-Ware license"
__version__ = "1.4.4"


import re
import sys
import json
import time
import signal
import requests
import asyncore
from bs4 import BeautifulSoup

from ircutils import bot, format, protocol

############################## EVENTS ###############################

# event handling seems to be broken

def callback_shutdown( signal, frame ):
        # put stuff for gracefull stop here
        print( "\nShutting down...\n" )
        sys.exit( 0 )

############################# UTILS #################################

def format_command( command, received ):
        """ Returns the fitting 'command' based on 'received'.
                received is either channel or private"""
        if received == "channel":
                return "!" + command.lower()
        return command.upper()

############################# COMMANDS ##############################

def cmd_exec( self, command, params, event, received="channel" ):
        """ {0}!X!- Execute an IRC command
                {0} <COMMAND> <[PARAMS]>!X!- Execute the IRC command <COMMAND> with parameters <PARAMS>"""

        self.execute( params[0].upper(), ' '.join( params[1:] ).strip() )
        if received == "private":
                self.send_message( event.source, "Executed" + format.bold( params[0].upper() + ' '.join( params[1:] ) ) )

def cmd_say( self, command, params, event, received="channel" ):
        """ {0}!X!- Say a Text
                {0} <TEXT>!X!- Say <TEXT> in current channel
                {0} <CHANNEL> <TEXT>!X!- Say <TEXT> in channel <CHANNEL> (/msg only)"""

        res = self.session.post("https://hightechlowlife.eu/board/taigachat/post.json", params=dict(self.params, message=' '.join(params), color='EEEEEE')) # substitute other color

def cmd_update( self, command, params, event, received="channel" ):
        """ {0}!X!- Update the Voice/HOP/OP info manually
                {0}!X!- Update the Voice/HOP/OP info manually"""

        self.execute( "NAMES", event.target )

def cmd_help( self, command, params, event, received="channel" ):
        """ {0}!X!- Help for commands
                {0}!X!- List commands
                {0} <COMMAND>!X!- Help for <COMMAND>"""

        if len( params ) < 1:
                self.send_message( event.source, "List of commands:" )
                for cmd in self.commands:
                        self.send_message( event.source, format.color( "## ", format.LIME_GREEN ) + '{:<20} {}'.format( *self.commands[ cmd ][1].__doc__.format( format.bold( format_command( cmd, received ) ) ).splitlines()[0].strip().split( "!X!", 1 ) ) ) # split and justify
                return
        if params[0].lower() in self.commands:
                self.send_message( event.source, "Usage info for command {0}:".format( format.bold( params[0] ) ) )
                for line in self.commands[ params[0].lower() ][1].__doc__.format( *[ format.bold( format_command( c, received ) ) for c in params ] ).splitlines():
                        self.send_message( event.source, format.color( "## ", format.LIME_GREEN ) + '{:<35} {}'.format( *line.strip().split( "!X!", 1 ) ) ) # split and justify
        else:
                self.send_message( event.source, "Unkown Command {0}.".format( format.bold( params[0] ) ) )

def cmd_shout( self, command, params, event, received="channel" ):
        """ {0}!X!- Shout a Text
                {0} <TEXT>!X!- Shout <TEXT> in current channel
                {0} <CHANNEL> <TEXT>!X!- Shout <TEXT> in channel <CHANNEL> (/msg only)"""

        colors = [ format.GREEN, format.RED, format.AQUA, format.PINK, format.LIGHT_GRAY ]
        if received == "private":
                for color, bg in [(x,y) for x in colors for y in colors if not x == y]:
                        self.send_message( params[0], format.color( ' '.join( params[1:] ).strip(), color, bg ) )
                        time.sleep( 0.5 )
        else:
                for color, bg in [(x,y) for x in colors for y in colors]:
                        self.send_message( event.target, format.color( ' '.join( params ).strip() , color, bg ) )
                        time.sleep( 0.5 )

def cmd_op( self, command, params, event, received="channel" ):
        """{0}!X!- Make an user OP
                {0}!X!- Get OP yourself
                {0} <USER>!X!- Make <USER> OP
                {0} <CHANNEL>!X!- Get OP yourself (/msg)
                {0} <CHANNEL> <USER>!X!- Make <USER> OP (/msg)"""

        user = event.source
        if received == "private":
                if len( params ) > 1:
                        user = params[1]
                self.execute( "MODE", params[0], "+o:", user )
        else:
                if len( params ) > 0:
                        user = params[0]
                self.execute( "MODE", event.target, "+o:", user )

def cmd_kick( self, command, params, event, received="channel" ):
        """{0}!X!- Kick an user
                {0} <USER>!X!- Kick <USER>
                {0} <USER> <CHANNEL>!X!- Kick <USER> from <CHANNEL> (/msg)"""

        if len( params ) < 1 or params[0] == "Charitum":
                return

        channel = event.target
        if len( params ) > 1:
                channel = params[1]
        self.execute( "KICK", channel, " ", params[0] )


def cmd_banner( self, command, params, event, received="channel" ):
        """{0}!X!- Print an ASCII Banner
                {0} <BANNER>!X!- Print <BANNER>
                {0} <BANNER> <CHANNEL>!X!- Print <BANNER> in <CHANNEL>"""

        rec = event.target
        if received == "private":
                rec = event.source
        if len( params ) > 1:
                rec = params[1]

        banner = None
        if params[0] == "text":
                banner = (format.BLUE, requests.get( "https://artii.herokuapp.com/make", params={"text": " ".join(params[2:])}).text.splitlines())
        elif params[0] == "graffiti":
                banner = (format.BLUE, requests.get( "https://artii.herokuapp.com/make", params={"text": " ".join(params[2:]), "font": "graffiti"}).text.splitlines() )
        elif params[0] in banners:
                banner = banners[params[0]]
        else:
                self.send_message( rec, format.color( "ERROR:", format.RED ) + " Banner not found" )
                return

        for line in banner[1]:
                self.send_message( rec, format.color( format.bold( line ), banner[0], format.BLACK ) )
                time.sleep( 0.5 )

############################### BOT #################################

class Charitum( bot.SimpleBot ):
        commands = {}
        channelusers = {}
        access = dict( ( ([ '', '+', '%', '@', '&', '~' ])[num] , num ) for num in range( 6 ) )

        def setup_shouty( self, username, password ):
            regex = re.compile(r'name="_xfToken" value="([^"]+)"')

            self.session = requests.session()
            res = self.session.post("https://hightechlowlife.eu/board/login/login", params={"login": username, "password": password})
            res = self.session.get ("https://hightechlowlife.eu/board/forums")

            token = regex.findall(res.text)[0]

            self.params = {
                "sidebar": 0,
                "lastrefresh": 0,
                "fake": 0,
                "room": 1,
                "_xfRequestUri": "/board/forums/",
                "_xfNoRedirect": 1,
                "_xfToken": token,
                "_xfResponseType": "json"
            }

        def run( self ):
            while True:
                res = self.session.post("https://hightechlowlife.eu/board/taigachat/list.json", params=self.params)
                result = json.loads(res.text)
                self.params["lastrefresh"] = result["lastrefresh"]
                soup = BeautifulSoup( result["templateHtml"] )

                for li in soup.find_all('li'):
                    if not "taigachat_message" in (li.get('id') or []):
                        continue
                    name = li.find(class_="username").string
                    message = li.find(class_="taigachat_messagetext").string
                    charitum.shoutbox(name, message)

                t = time.time()
                while time.time() < t+1:
                    asyncore.loop(timeout=1, count=1)

        def add_command( self, command, level, func, short=None ):
                """ Adds a new command. command and short are names for
                        the command, used as ![command/short] and [COMMAND/SHORT].
                        level is a numeric user level and func a function pointer.

                        The docstring of func will be used by the help command, the
                        first line shows up in the list, the rest only when
                        specifically targetting the command. Format your docstring
                        like this: '{0}!X!- Update the Voice/HOP/OP info manually'
                        You can use {0}-{9} for the parameters passed to help ( {0}
                        is the command itself ) and !X! for the point where the text
                        is left-justified."""
                self.commands[ command.lower() ] = ( level, func )
                if short is not None:
                        self.commands[ short.lower() ] = ( level, func )
                print( "Added commmand " + command + ", level " + level + ", func " + func.__name__ )

        def on_welcome( self, event ):
                self.identify( "topSecretChariPass" ) # authenticate with nickserv

        def on_reply( self, event ):
                if event.command == "RPL_NAMREPLY": # NAMES' reply. used for updating permissions
                        self.channelusers[ event.params[1] ] = event.params[2].split()

        def on_join( self, event ):
                if event.source != self.nickname: # don't welcome yourself
                        self.send_message( event.target, "Welcome to " + format.color( format.bold( ' LTFU :' ), format.BLACK, format.LIGHT_GRAY ) + format.color( ': hangout ', format.WHITE, format.GREEN ) + ", " +  format.bold( event.source ) )

        def on_channel_message( self, event ):
                message = event.message.split()
                command = message[0]
                params  = message[1:]

                if len( command ) == 1: # skip single !'s and stuff
                        return

                if command[0] == "!": # only handle commands directed to us...
                        command =  command[1:].lower()
                        if command in self.commands: # ... that exist
                                self.execute( "NAMES", event.target ) # update permissions
                                ( level, func ) = self.commands[ command ]

                                for name in self.channelusers[ event.target ]:
                                        if protocol.strip_name_symbol( name ) == event.source: break # name is now event.target's name

                                ulevel = 0
                                if name[0] in self.access: # do not handle 'empty' users
                                        ulevel = self.access[ name[0] ]

                                if  ulevel < self.access[ level ]:
                                        self.send_message( event.target, format.color( "ERROR:", format.RED ) + " You are not allowed to use the " + format.bold( command ) + " Command" )
                                        return
                                func( self, command, params, event )

        def on_private_message( self, event ):
                message = event.message.split()
                command = message[0].upper()
                params  = message[1:]

                if command.lower() in self.commands:
                        self.execute( "NAMES", "#ltfu" ) # update permissions
                        ( level, func ) = self.commands[ command.lower() ]

                        for name in self.channelusers[ "#ltfu" ]:
                                if protocol.strip_name_symbol( name ) == event.source: break # name is now event.target's name

                        ulevel = 0
                        if name[0] in self.access: # do not handle 'empty' users
                                ulevel = self.access[ name[0] ]

                        if ulevel < self.access[ level ]:
                                self.send_message( event.source, format.color( "ERROR:", format.RED ) + " You are not allowed to use the " + format.bold( command ) + " Command" )
                                return
                        func( self, command, params, event, received="private" ) # tell the function this was a private message and call it
        def shoutbox(self, name, message):
            if self.is_connected():
                self.send_message( "#ltfu", "{}: {}".format(format.color(name, format.RED), message) )


banners = {
"blame_end": ( format.RED, [
        "                                                                       ",
        "   __________.__                          ___________           .___   ",
        "   \______   \  | _____    _____   ____   \_   _____/ ____    __| _/   ",
        "    |    |  _/  | \__  \  /     \_/ __ \   |    __)_ /    \  / __ |    ",
        "    |    |   \  |__/ __ \|  Y Y  \  ___/   |        \   |  \/ /_/ |    ",
        "    |______  /____(____  /__|_|  /\___  > /_______  /___|  /\____ |    ",
        "           \/          \/      \/     \/          \/     \/      \/    ",
        "                                                                       ",
        "                                              (seriously, blame end)   "
        ]),
"ltfu": ( format.GREEN, [
        " .____           __  .__                       _____.__            .___                  ",
        " |    |    _____/  |_|  |__   ____   _____   _/ ____\__| ____    __| _/    __ __  ______ ",
        " |    |  _/ __ \   __\  |  \_/ __ \ /     \  \   __\|  |/    \  / __ |    |  |  \/  ___/ ",
        " |    |__\  ___/|  | |   Y  \  ___/|  Y Y  \  |  |  |  |   |  \/ /_/ |    |  |  /\___ \  ",
        " |_______ \___  >__| |___|  /\___  >__|_|  /  |__|  |__|___|  /\____ | /\ |____//____  > ",
        "         \/   \/          \/     \/      \/                 \/      \/ \/            \/  ",
        "                                                                           lethemfind.us "
        ])
}

############################### RUN #################################

if __name__ == "__main__":
        charitum = Charitum( "Charitum" )
        charitum.setup_shouty( sys.argv[1], sys.argv[2] )
        charitum.connect( "irc.p2p-network.net", channel=["#ltfu"] )

        charitum.add_command( "execute", "~", cmd_exec, "exec" )
        charitum.add_command( "say", "@", cmd_say, "!" )
        charitum.add_command( "shout", "@", cmd_shout, "!!" )
        charitum.add_command( "kick", "@", cmd_kick )
        charitum.add_command( "op", "@", cmd_op )
        charitum.add_command( "banner", "", cmd_banner )
        charitum.add_command( "update", "", cmd_update, "upd" )
        charitum.add_command( "help", "", cmd_help )

        signal.signal( signal.SIGINT,  callback_shutdown ) # register graceful shutdown here

        charitum.run()
