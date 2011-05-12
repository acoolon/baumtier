#!/usr/bin/env python
# License: WTFPL (http://sam.zoy.org/wtfpl/)
# baumtier by Thob
# Usage: run it (python 333

__version__ = '0.1'

from baumi import ircclient
from baumi import asynsocket
from baumi import serverpinger

import logging
logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s',
    filename='baumi_log', datefmt='%m-%d %H:%M', level=logging.DEBUG)
logger = logging.getLogger('baumi')

### commands ###

class SpassCommands:
    def __init__(self):
        self.commands['sage'] = self.say
        self.commands['gib'] = self.gib
        self.commands['bring'] = self.bring
        self.commands['rothaus'] = self.rothaus

    def say(self, nick, channel, message):
        if channel == nick:
            (new_channel, msg) = message.split(' ', 1)
            self.send_message(msg, new_channel)

    def gib(self, nick, channel, message):
        '<Empfänger> <Objekt>'
        (to, what) = message.split(' ', 1)
        if to == 'mir': to = nick
        if to in (self.nick, 'dir'):
            self.send_message('Yay, {} für mich.'.format(what), channel)
        else:
            self.send_action('gibt {} {}'.format(to, what), channel)

    def bring(self, nick, channel, message):
        '<Empfänger> <Objekt>'
        (to, what) = message.split(' ', 1)
        if to == 'mir': to = nick
        if to in (self.nick, 'dir'):
            self.send_message('Yay, {} für mich.'.format(what), channel)
        else:
            self.send_action('bringt {} {}'.format(to, what), channel)

    def rothaus(self, nick, channel, message):
        ':ein Bier für Haraun'
        if 'araun' in nick: self.send_action('gibt Haraun Rothaus!', channel)
        else: self.send_message('Rothaus gibt es nur für Haraun.', channel)


class ServerCommands:
    def __init__(self):
        self.server_monitor = dict()
        self.commands['ping'] = self.ping
        self.commands['laanx'] = self.ping_laanx
        self.commands['monitor'] = self.monitor

    def ping(self, nick, channel, message):
        '''zeroping|ezpcusa|host:port
        Pingt den Server an und berechnet die Packetumlaufzeit.
        Falls der Server sich nicht innerhalb von zwei Sekunden meldet
        nehmen wir an, dass er offline ist.
        '''
        def response(host, state, delay):
            if host == '62.173.168.9': host = 'ZeroPing'
            elif host == '70.167.49.20': host = 'Ezpcusa'
            msg = '{}, {} ist {} ({}ms).'.format(nick, host, state, delay)
            self.send_message(msg, channel)

        if channel == self.nick: channel = nick
        if ':' in message:
            (host, port) = message.split(':')
            port = int(port)
        elif 'zero' in message: (host, port) = ('62.173.168.9', 7777)
        elif 'laanx' in message: (host, port) = ('62.173.168.9', 7777)
        elif 'ez' in message: (host, port) = ('70.167.49.20', 7777)
        else: raise ValueError
        self.serverpinger.poke(host, port, response)

    def ping_laanx(self, nick, channel, message):
        ':alias für !ping zeroping'
        self.ping(nick, channel, 'zeroping')

    def monitor(self, nick, channel, message):
        'zeroping|ezpcusa|host:port ein|aus'
        def handle_monitor(host, state=None, delay=None):
            ping = self.server_monitor[host]
            if state and delay:
                if ping.state != state:
                    if host == '62.173.168.9': host = 'ZeroPing'
                    elif host == '70.167.49.20': host = 'Ezpcusa'
                    self.send_message('{} is nun {}'.format(host, state), channel)
                    ping.state = state
            else:
                self.serverpinger.poke(ping.host, ping.port, handle_monitor)
                ping.event = self.sched.enter(30, 1, handle_monitor, (host, ))

        (adress, cmd) = message.split()
        if ':' in adress:
            (host, port) = adress.split(':')
            port = int(port)
        elif 'zero' in adress: (host, port) = ('62.173.168.9', 7777)
        elif 'laanx' in adress: (host, port) = ('62.173.168.9', 7777)
        elif 'ez' in adress: (host, port) = ('70.167.49.20', 7777)
        else: raise ValueError

        if cmd == 'ein':
            ping = serverpinger.Ping()
            ping.host = host
            ping.port = port
            ping.state = None
            self.server_monitor[ping.host] = ping
            handle_monitor(host)
        elif cmd == 'aus':
            try: ping = self.server_monitor.pop(host)
            except KeyError: self.send_message('Wie auch immer.', channel)
            else:
                self.sched.cancel(ping.event)
                self.send_message('Gestoppt', channel)



class UtilityCommands:
    def __init__(self):
        self.commands['bookmark'] = self.bookmark
        self.commands['link'] = self.link

    def bookmark(self, nick, channel, message):
        '''befehl [name] [link]
        Verbinde Links mit einem Namen.
        add name link: Füge den Link der Liste hinzu
        del name: Lösche alle Links die mit Name verbunden wurden
        list [name]: Liste alle Links die mit Name verbunden wurden
        '''
        (command, *name_link) = message.split(' ', 2)
        if command == 'add': self.bookmark_add(nick, channel, *name_link)
        elif command == 'del': self.bookmark_del(nick, channel, *name_link)
        elif command == 'list': self.bookmark_list(nick, channel, *name_link)
        else: raise ValueError('Bookmarks falsch aufgerufen')

    def read_bookmarks(self):
        try: f_book = open('baumi_bookmarks')
        except EnvironmentError: return False
        else:
            lines = f_book.read().split('\n')
            f_book.close()
            return [line.split(' ', 1) for line in lines if line]

    def bookmark_add(self, nick, channel, *args):
        (name, link) = args
        with open('baumi_bookmarks', 'a') as f_book:
            f_book.write('{} {}\n'.format(name, link))
            self.send_message('Ok, erledigt.', channel)

    def bookmark_del(self, nick, channel, *args):
        (name, *crap) = args
        lines = self.read_bookmarks()
        if lines:
            new_lines = list()
            deleted_lines = list()
            for (new_name, link) in lines:
                if new_name == name: deleted_lines.append(link)
                else: new_lines.append('{} {}\n'.format(new_name, link))
            with open('baumi_bookmarks', 'w') as f_book:
                f_book.write(''.join(new_lines))
            if deleted_lines:
                self.send_message('{} gelöscht.'.format(' | '.join(deleted_lines)), channel)
            else: self.send_message('Es gibt nichts zu löschen', channel)
        else: self.send_message('Es gibt noch keine Bookmarks', channel)

    def bookmark_list(self, nick, channel, *args):
        lines = self.read_bookmarks()
        if lines:
            if args:
                name = args[0]
                links = list()
                for (new_name, link) in lines:
                    if name == new_name: links.append(link)
                if links: self.send_message(' | '.join(links), channel)
                else:
                    self.send_message('Keine Links für diesen Namen gespeichert', channel)
            else:
                names = set([name for (name, link) in lines])
                self.send_message('Alle Namen: {}'.format(' | '.join(names)), channel)
        else: self.send_message('Es gibt noch keine Bookmarks', channel)

    def link(self, nick, channel, *args):
        ': alias für !bookmark list'
        if args == ('',): args = tuple()
        self.bookmark_list(nick, channel, *args)

###   ###

class Baumi(ircclient.IRCClient, SpassCommands, ServerCommands, UtilityCommands):
    def __init__(self, sched, nick='Baumtierchen', user='baumi', channel='#psde'):
        super().__init__(sched, nick, user, channel)
        self.serverpinger = serverpinger.Pinger(self.sched)
        self.commands = {'hilfe': self.help, 'help': self.help}
        SpassCommands.__init__(self)
        ServerCommands.__init__(self)
        UtilityCommands.__init__(self)

    def error_callback(self, command, nick, channel, message):
        cmd = self.commands[command]
        if cmd.__doc__:
            msg = 'So geht es richtig: !{} {}'
            msg = msg.format(command, cmd.__doc__.split('\n')[0])
            self.send_message(msg, nick)

    def on_nicklist_changed(self):
        logger.debug('Nicklist changed.')
        with open('baumi_nicklist', 'w') as f_nicklist:
            f_nicklist.write('\n'.join(sorted(self.nick_list)))
            f_nicklist.close()

    def help(self, nick, channel, message):
        '''[command] :ein kurzer Hilfetext
        Ohne Parameter wird eine Liste aller Kommandos ausgegeben.
        Mit einem Kommando als Parameter gibt es die ausführliche
        (wenn vorhanden) Hilfe.
        '''
        if message:
            try: cmd = self.commands[message]
            except KeyError: self.send_message('Kenn ich nicht.', nick)
            else:
                if cmd.__doc__:
                    self.send_message('Hilfe für !{}:'.format(message), nick)
                    for line in cmd.__doc__.split('\n'): self.send_message(line.strip(), nick)
                else:  self.send_message('Kenn ich nicht.', nick)
        else:
            self.send_message('Hilfe für Baumtier version {}'.format(__version__), nick)
            self.send_message('Kommandos sind:', nick)
            for cmd_name in self.commands:
                cmd = self.commands[cmd_name]
                if cmd.__doc__:
                    (short_help, *long_help) = cmd.__doc__.split('\n')
                    msg = '!{} {}'.format(cmd_name, short_help)
                    self.send_message(msg, nick)
            self.send_message('!hilfe [command] für mehr Informationen', nick)


def main():
    sched = asynsocket.asynschedcore()
#    Baumi(sched, nick='Baumi', channel='#baumi-test')
    Baumi(sched)
    sched.run()

if __name__ == '__main__': main()
