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
import json
import time
import signal
import argparse
import requests
import asyncore
from bs4 import BeautifulSoup

from ircutils import bot, format, protocol

############################## EVENTS ###############################

# event handling seems to be broken

def callback_shutdown( signal, frame ):
        import sys
        print( "\nShutting down...\n" )
        sys.exit(0)

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
        """ {0}!X!- Send text to the shoutbox
                {0} <TEXT>!X!- Say <TEXT> in the shoutbox"""

        self.session.post(self.base + "/taigachat/post.json", params=dict(self.params, message=' '.join(params), color='EEEEEE'))

def cmd_mutesb( self, command, params, event, received="channel" ):
        """ {0}!X!- Toggle the shoutbox echo for this channel
                {0} <CHANNEL> !X!- Toggle the shoutbox echo for <CHANNEL> (/msg only)"""

        chan = event.target
        if len(params) > 0:
                chan = params[0]

        if chan not in self.channels:
                self.send_message( event.target, "'{}' is not a valid channel".format(chan) )
                return

        self.muted[chan] = (chan not in self.muted) or (not self.muted[chan])
        text = "ON"
        if self.muted[chan]:
                text = "OFF"
        self.send_message( chan, "Shoutbox echoing is now toggled {}".format(format.color(text, format.RED)) )

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

        colors = [ format.GREEN, format.RED, format.AQUA ]
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
        tell = {}
        commands = {}
        channelusers = {}
        access = dict( ( ([ '', '+', '%', '@', '&', '~' ])[num] , num ) for num in range( 6 ) )

        def run( self, username, password, base, log_threads=True ):
                regex = re.compile(r'name="_xfToken" value="([^"]+)"')

                self.session = requests.session()
                res = self.session.post(base + "/login/login", params={"login": username, "password": password})
                res = self.session.get (base + "/forums")

                token = regex.findall(res.text)[0]

                self.base = base
                self.params = {
                    "sidebar": 0,
                    "lastrefresh": 0,
                    "fake": 0,
                    "room": 2,
                    "_xfRequestUri": "/board/forums/",
                    "_xfNoRedirect": 1,
                    "_xfToken": token,
                    "_xfResponseType": "json"
                }

                i = 0
                old_threads = []
                self.muted = {}

                res = self.session.get(base + "/forums")
                soup = BeautifulSoup(res.text)
                for thread in soup.find_all("li", class_="discussionListItem"):
                        url = thread.find(class_="PreviewTooltip")["href"]
                        user = thread.find(class_="username").text
                        title = thread.find(class_="PreviewTooltip").text
                        posts = thread.find("dl", class_="major").find("dd").text

                        if posts == "0" and not url in old_threads:
                                old_threads.append(url)

                while True:
                        i += 1
                        res = self.session.post(base + "/taigachat/list.json", params=self.params)
                        result = json.loads(res.text)
                        self.params["lastrefresh"] = result["lastrefresh"]
                        soup = BeautifulSoup( result["templateHtml"] )

                        for li in soup.find_all('li'):
                                if not "taigachat_message" in (li.get('id') or []):
                                        continue
                                name = li.find(class_="username").text
                                message = li.find(class_="taigachat_messagetext").text
                                if self.is_connected() and "a new thread was posted by" not in message:
                                        for chan in self.channels:
                                                if (chan not in self.muted) or (not self.muted[chan]):
                                                        self.send_ctcp(chan, "ACTION", ["{}: {}".format(format.color(name, format.RED), message)])
                        if log_threads:
                                res = self.session.get(base + "/forums")
                                soup = BeautifulSoup(res.text)
                                for thread in soup.find_all("li", class_="discussionListItem"):
                                        url = thread.find(class_="PreviewTooltip")["href"]
                                        user = thread.find(class_="username").text
                                        title = thread.find(class_="PreviewTooltip").text
                                        posts = thread.find("dl", class_="major").find("dd").text

                                        if posts == "0" and not url in old_threads:
                                                old_threads.append(url)
                                                shoutytext = "a new thread was posted by {}: [URL={}/{}]{}[/URL]".format(user, base, url, title)
                                                self.session.post(base + "/taigachat/post.json", params=dict(self.params, message=shoutytext, color='EEEEEE'))
                                                for chan in self.channels:
                                                        self.send_ctcp(chan, "ACTION", ["{} opened a new thread: [{}/{}]".format(user, base, url)])
                                                        self.send_ctcp(chan, "ACTION", ["   " + format.color(title, format.GREEN)])

                        t = time.time()
                        while time.time() < t+1:
                                asyncore.loop(timeout=1, count=1)
                        if i > 4:
                                for chan in self.channels:
                                        self.execute("NAMES", chan) # update permissions

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

                if event.source in self.tell and self.tell[event.source] != False:
                        for m in self.tell[event.source]:
                                self.send_message( m[1], "[{}] {}".format(time.strftime("%H:%M", (m[0])), m[2]) )

                self.tell[event.source] = False # False = online but known

        def on_quit( self, event ):
                self.tell[event.source] = []

        def on_part( self, event ):
                self.tell[event.source] = []

        tellre = re.compile("^@ ?([a-zA-Z0-9-_]*) ?: ")
        def on_channel_message( self, event ):
                message = event.message.split()
                command = message[0]
                params  = message[1:]

                if event.source not in self.tell:
                        self.tell[event.source] = False

                if command[0] == "!": # only handle commands directed to us...
                        if len( command ) == 1: # skip single !'s and stuff
                                return

                        command =  command[1:].lower()
                        if command in self.commands: # ... that exist
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
                elif self.tellre.match(event.message):
                        nick = self.tellre.match(event.message).groups()[0]

                        if nick in self.tell and self.tell[nick] != False: # known but nont online
                                self.tell[nick].append((time.gmtime(), event.target, "{}: {}".format(event.source, format.color(event.message, format.GREEN))))
                                self.send_message(event.target, "I'll pass that on to {}".format(nick))

        def on_private_message( self, event ):
                message = event.message.split()
                command = message[0].upper()
                params  = message[1:]

                if event.source not in self.tell:
                        self.tell[event.source] = False

                if command.lower() in self.commands:
                        ( level, func ) = self.commands[ command.lower() ]

                        for name in self.channelusers[next(iter(self.channels))]: # FIXME: random channel
                                if protocol.strip_name_symbol( name ) == event.source: break # name is now event.target's name

                        ulevel = 0
                        if name[0] in self.access: # do not handle 'empty' users
                                ulevel = self.access[ name[0] ]

                        if ulevel < self.access[ level ]:
                                self.send_message( event.source, format.color( "ERROR:", format.RED ) + " You are not allowed to use the " + format.bold( command ) + " Command" )
                                return
                        func( self, command, params, event, received="private" ) # tell the function this was a private message and call it

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
        parser = argparse.ArgumentParser()
        parser.add_argument(
                "-n", "--nick", default="Charitum",
                help="IRC nickname"
        )
        parser.add_argument(
                "-s", "--server", default="irc.p2p-network.net",
                help="IRC server to connect to"
        )
        parser.add_argument(
                "-u", "--user",
                help="user account name for taigachat bindings"
        )
        parser.add_argument(
                "-p", "--pass", metavar="PASS", dest="passw",
                help="user password for taigachat bindings"
        )
        parser.add_argument(
                "--board-url", default="https://hightechlowlife.eu/board",
                help="the Board's root URL (only used with -u and -p)"
        )
        parser.add_argument(
                "--no-threads", action="store_false", dest="log_threads",
                help="do not check for new threads"
        )
        parser.add_argument(
                "channel", nargs="+",
                help="channels to join"
        )
        args = parser.parse_args()

        charitum = Charitum( args.nick )
        charitum.connect( "irc.p2p-network.net", channel=args.channel )
        # charitum.add_command( "execute", "~", cmd_exec, "exec" )
        charitum.add_command( "shout", "@", cmd_shout, "!!" )
        charitum.add_command( "kick", "@", cmd_kick )
        charitum.add_command( "op", "@", cmd_op )
        charitum.add_command( "banner", "", cmd_banner )
        charitum.add_command( "update", "", cmd_update, "upd" )
        charitum.add_command( "help", "", cmd_help )
        if args.user and args.passw:
            charitum.add_command( "mutesb", "", cmd_mutesb )
            charitum.add_command( "say", "@", cmd_say, "!" )

        signal.signal( signal.SIGINT,  callback_shutdown ) # register graceful shutdown here

        if args.user and args.passw:
            print("Starting with taigachat bridge enabled")
            charitum.run(args.user, args.passw, args.board_url.rstrip("/"), log_threads=args.log_threads)
        else:
            charitum.start()
