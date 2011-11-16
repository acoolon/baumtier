# License: WTFPL (http://sam.zoy.org/wtfpl/)

from baumi import utils
from baumi import config
from baumi import asynsocket
from baumi import serverpinger

import json
import random
import socket
import urllib.parse as urllib

logger = utils.logger.getLogger(__name__)

class CommandHandler:
    def __init__(self):
        self.commands = self.command_handler = None

    def handle_start(self):
        self.commands = dict()
        self.command_handler = list()
        for Handler in COMMANDS:
            handler = Handler(self)
            self.command_handler.append(handler)
        self.register('help', self.help)
        self.register('hilfe', self.help)

    def handle_close(self):
        for handler in self.command_handler:
            try: handler.close()
            except AttributeError: pass
        self.commands = self.command_handler = None

    def call_cmd(self, name, ircclient, nick, channel, message):
        if name in self.commands:
            command = self.commands[name]
            try: command(ircclient, nick, channel, message)
            except ValueError: return None
        else: return False
        msg = '{} called command {} in {}: {}'
        logger.info(msg.format(nick, name, channel, message))
        return True

    def register(self, name, command):
        self.commands[name] = command

#    def use_brain(self, nick, channel, message):
#        if message.startswith(self.protocol.nick):  # somehow important
#            logger.info('Brain on: {}-{}-{}'.format(nick, channel, message))
#            if 'line' in message:  # online/offline
#                if 'ero' in message or 'aanx' in message:
#                    self.ping(nick, channel, 'zero')
#               elif 'ez' in message or 'zpx' in message:
#                    self.ping(nick, channel, 'ez')
#            elif 'ink' in message:  # link/Link
#                (crap, intresting) = message.split('ink ')
#                words = intresting.split(' ')
#                if words[0] == 'für':
#                    next_word = words[1]
#                    if next_word in ('der', 'die', 'das'):
#                        next_word = words[2]
#                    self.link(nick, channel, next_word)

    def help(self, ircclient, nick, channel, message):
        '''[command] :ein kurzer Hilfetext
        Ohne Parameter wird eine Liste aller Kommandos ausgegeben.
        Mit einem Kommando als Parameter gibt es die ausführliche
        (wenn vorhanden) Hilfe.
        '''
        if message:
            try: cmd = self.commands[message.strip('!')]
            except KeyError: ircclient.send_message('Kenn ich nicht.', nick)
            else:
                if cmd.__doc__:
                    ircclient.send_message('Hilfe für !{}:'.format(message), nick)
                    (short_help, *long_help) = cmd.__doc__.split('\n')
                    msg = '!{} {}'.format('!' + message, short_help)
                    ircclient.send_message(msg, nick)
                    for line in long_help:
                        ircclient.send_message(line.strip(), nick)
                else: ircclient.send_message('Kenn ich nicht.', nick)
        else:
            ircclient.send_message('Baumtier v{}'.format(config.__version__), nick)
            ircclient.send_message('Kommandos sind:', nick)
            cmds = list()
            for cmd_name in self.commands:
                cmd = self.commands[cmd_name]
                if cmd.__doc__: cmds.append('!' + cmd_name)
            ircclient.send_message(', '.join(cmds), nick)
            ircclient.send_message('!hilfe [command] für mehr Informationen', nick)


class UtilityCommands:
    def __init__(self, command_handler):
        command_handler.register('bookmark', self.bookmark)
        command_handler.register('link', self.link)
        command_handler.register('join', self.join)
        command_handler.register('part', self.part)
        command_handler.register('quit', self.quit)

    def join(self, ircclient, nick, channel, message):
        ' channel :Betrete channel, separiert durch " "'
        channels = message.split()
        if ircclient.is_authorized(channel, nick):
                ircclient.protocol.send_join(*channels)
        else: ircclient.send_message('Das darfst  du nicht!', nick)

    def part(self, ircclient, nick, channel, message):
        ' channel :Verlasse channel, separiert durch " "'
        channels = message.split()
        if ircclient.is_authorized(channel, nick):
            ircclient.protocol.send_part(*channels)
        else: ircclient.send_message('Das darfst  du nicht!', nick)

    def quit(self, ircclient, nick, channel, message):
        ' :Beende Baumtier'
        if ircclient.is_authorized(channel, nick): ircclient.disconnect()
        else: ircclient.send_message('Das darfst  du nicht!', nick)

    def bookmark(self, ircclient, nick, channel, message):
        '''befehl [name] [link]
        Verbinde Links mit einem Namen.
        add name link: Füge den Link der Liste hinzu
        del name: Lösche alle Links die mit Name verbunden wurden
        list [name]: Liste alle Links die mit Name verbunden wurden
        '''
        (command, *name_link) = message.split(' ', 2)
        if command == 'add': self.bookmark_add(ircclient, nick, channel, *name_link)
        elif command == 'del': self.bookmark_del(ircclient, nick, channel, *name_link)
        elif command == 'list': self.bookmark_list(ircclient, nick, channel, *name_link)
        else: raise ValueError('Bookmarks falsch aufgerufen')

    def read_bookmarks(self):
        try: f_book = open(config.BOOKMARKFILE)
        except EnvironmentError: return False
        else:
            lines = f_book.read().split('\n')
            f_book.close()
            return [line.split(' ', 1) for line in lines if line]

    def bookmark_add(self, ircclient, nick, channel, *args):
        if ircclient.is_authorized(channel, nick):
            (name, link) = args
            with open(config.BOOKMARKFILE, 'a') as f_book:
                f_book.write('{} {}\n'.format(name, link))
                ircclient.send_message('Ok, erledigt.', channel)
        else: ircclient.send_message('Das darfst  du nicht!', channel)

    def bookmark_del(self, ircclient, nick, channel, *args):
        if ircclient.is_authorized(channel, nick):
            (name, *crap) = args
            lines = self.read_bookmarks()
            if lines:
                new_lines = list()
                deleted_lines = list()
                for (new_name, link) in lines:
                    if new_name == name: deleted_lines.append(link)
                    else: new_lines.append('{} {}\n'.format(new_name, link))
                with open(config.BOOKMARKFILE, 'w') as f_book:
                    f_book.write(''.join(new_lines))
                if deleted_lines:
                    msg = '{} gelöscht.'.format(' | '.join(deleted_lines))
                    ircclient.send_message(msg, channel)
                else: ircclient.send_message('Es gibt nichts zu löschen', channel)
            else: ircclient.send_message('Es gibt noch keine Bookmarks', channel)
        else: ircclient.send_message('Das darfst  du nicht!', channel)

    def bookmark_list(self, ircclient, nick, channel, *args):
        lines = self.read_bookmarks()
        if lines:
            if args:
                name = args[0]
                links = list()
                for (new_name, link) in lines:
                    if name == new_name: links.append(link)
                if links: ircclient.send_message(' | '.join(links), channel)
                else:
                    msg = 'Keine Links für diesen Namen gespeichert'
                    ircclient.send_message(msg, channel)
            else:
                names = set([name for (name, link) in lines])
                msg = 'Alle Namen: {}'.format(' | '.join(names))
                ircclient.send_message(msg, channel)
        else: ircclient.send_message('Es gibt noch keine Bookmarks', channel)

    def link(self, ircclient, nick, channel, *args):
        ': alias für !bookmark list'
        if args == ('',): args = tuple()
        self.bookmark_list(ircclient, nick, channel, *args)


class ResearchCommands(asynsocket.asynchat):
    def __init__(self, command_handler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminator = '\r\n\r\n'
        self.last_request = {'hd': '', 'bd': ''}
        command_handler.register('google', self.request_google)
        command_handler.register('wiki', self.request_wiki)

    def found_terminator(self, message):
        req = self.last_request
        if not req['hd']: req['hd'] = message
        elif not req['bd']: req['bd'] = message
        else: print('Crap')
        if req['hd'] and req['bd']:
            self.process(self.last_request)
            self.last_request = {'hd': '', 'bd': ''}
            self.handle_close()

    def request_google(self, ircclient, nick, channel, message):
        '''Anfrage: gibt das erste Google Ergebnis zurück'''
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(('ajax.googleapis.com', 80))
        message = urllib.quote_plus(message)
        request = 'GET /ajax/services/search/web?v=1.0&q={}&hl=de HTTP/1.1'
        request += '\r\nHost: ajax.googleapis.com'
        self.send_line(request.format(message))
        self.last_request['irc'] = ircclient
        self.last_request['nick'] = nick
        self.last_request['channel'] = channel

    def request_wiki(self, ircclient, nick, channel, message):
        '''Anfrage: Sucht per Google in der Wikipedia'''
        self.request_google(ircclient, nick, channel,
                            'site:de.wikipedia.org ' + message)

    def process(self, request):
        body = json.loads(request['bd'].split('\r\n')[1])
        url = body['responseData']['results'][0]['url']
        msg = '{}, {}'.format(request['nick'], url)
        request['irc'].send_message(msg, request['channel'])

class SpassCommands:
    def __init__(self, command_handler):
        command_handler.register('sage', self.say)
        command_handler.register('gib', self.gib)
        command_handler.register('bring', self.bring)
        command_handler.register('matte', self.matte)
        command_handler.register('8ball', self.eightball)
        command_handler.register('roll', self.roll)

    def say(self, ircclient, nick, channel, message):
        if channel == nick:
            (new_channel, msg) = message.split(' ', 1)
            ircclient.send_message(msg, new_channel)

    def gib(self, ircclient, nick, channel, message):
        '<Empfänger> <Objekt>'
        (to, what) = message.split(' ', 1)
        if to == 'dir':
            ircclient.send_message('Yay, {} für mich.'.format(what), channel)
        else:
            if to == 'mir': to = nick
            ircclient.send_action('gibt {} {}'.format(to, what), channel)

    def bring(self, ircclient, nick, channel, message):
        '<Empfänger> <Objekt>'
        (to, what) = message.split(' ', 1)
        if to == 'mir': to = nick
        if to == 'dir':
            ircclient.send_message('Yay, {} für mich.'.format(what), channel)
        else:
            ircclient.send_action('bringt {} {}'.format(to, what), channel)

    def matte(self, ircclient, nick, channel, message):
        'Bereitet dir eine Hängematte vor'
        f_part = ['holt eine Hängematte', 'holt eine Hängematte und einen Ständer']
        l_part = [' und hängt sie für {} auf.',
                  ', hängt sie auf und bittet {} Platz zu nehmen.',
                  ' und wirft sie vor {} auf den Boden.']
        string = random.choice(f_part) + random.choice(l_part)
        ircclient.send_action(string.format(nick), channel)

    def eightball(self, ircclient, nick, channel, message):
        '''<Frage> :lass mich einfach entscheiden
        Nur Fragen, die mit Ja/Nein beantwortet werden können
        '''
        if message:
            pos_ans = ('Ganz klar: Ja!', 'Ich denke schon.', 'Ja!',
                    'Na sicher!', 'Natürlich!', 'Auf jeden Fall!')
            neg_ans = ('Nein!', 'Niemals', 'Eher nicht.',
                'Auf keinen Fall!', 'Ganz klar: Nein!')
            ans_list = random.choice((pos_ans, neg_ans))
            ans = random.choice(ans_list)
            ircclient.send_message('{}: {}'.format(nick, ans), channel)
        else: raise ValueError('eine frage fehlt')

    def roll(self, ircclient, nick, channel, message):
        'number :eine Zahl zwischen 0 und number wählen'
        number = int(message)
        msg = '{}, deine Zahl ist {}.'.format(nick, random.randint(0, number))
        ircclient.send_message(msg, channel)


class PingCommands:
    def __init__(self, command_handler):
        self.server_monitor = dict()
        self.serverpinger = serverpinger.Pinger()
        command_handler.register('ping', self.ping)
        command_handler.register('laanx', self.ping_laanx)
        command_handler.register('monitor', self.monitor)

    def close(self):
        for host in self.server_monitor:
            ping = self.server_monitor[host]
            utils.sched.cancel(ping['event'])
        self.serverpinger.handle_close()

    def ping(self, ircclient, nick, channel, message):
        '''zeroping|ezpcusa|host:port
        Pingt den Server an und berechnet die Packetumlaufzeit.
        Falls der Server sich nicht innerhalb von zwei Sekunden meldet
        nehmen wir an, dass er offline ist.
        '''
        def response(host, state, delay):
            if host == '62.173.168.9': host = 'ZeroPing'
            elif host == '70.167.49.20': host = 'Ezpcusa'
            msg = '{}, {} ist {} ({}ms).'.format(nick, host, state, delay)
            ircclient.send_message(msg, channel)

        if ':' in message:
            (host, port) = message.split(':')
            port = int(port)
        elif 'zero' in message: (host, port) = ('62.173.168.9', 7777)
        elif 'laanx' in message: (host, port) = ('62.173.168.9', 7777)
        elif 'ez' in message: (host, port) = ('70.167.49.20', 7777)
        else: raise ValueError
        self.serverpinger.poke(host, port, response)

    def ping_laanx(self, ircclient, nick, channel, message):
        ':alias für !ping zeroping'
        self.ping(ircclient, nick, channel, 'zeroping')

    def monitor(self, ircclient, nick, channel, message):
        'zeroping|ezpcusa|host:port ein|aus'
        (adress, cmd) = message.split()
        if ':' in adress:
            (host, port) = adress.split(':')
            port = int(port)
        elif 'zero' in adress: (host, port) = ('62.173.168.9', 7777)
        elif 'laanx' in adress: (host, port) = ('62.173.168.9', 7777)
        elif 'ez' in adress: (host, port) = ('70.167.49.20', 7777)
        else: raise ValueError

        if cmd in ('ein', 'an', 'on', 'start'):
            self.enable_monitor(ircclient, channel, host, port)
        elif cmd in ('aus', 'halt', 'stop', 'off'):
            self.disable_monitor(ircclient, channel, host, port)

    def handle_monitor(self, host, state=None, delay=None):
        ping = self.server_monitor[host]
        if state and delay:
            if ping['state'] != state:
                if host == '62.173.168.9': host = 'ZeroPing'
                elif host == '70.167.49.20': host = 'Ezpcusa'
                msg = '{} ist {} ({}ms).'.format(host, state, delay)
                for ch in ping['channels']: ping['ircclient'].send_message(msg, ch)
                ping['state'] = state
        else:
            self.serverpinger.poke(host, ping['port'], self.handle_monitor)
            ping['event'] = utils.sched.enter(15, 1, self.handle_monitor, (host,))

    def enable_monitor(self, ircclient, channel, host, port):
        if not host in self.server_monitor:
            logger.info('Startet observing {}.'.format(host))
            ping = {'port': port, 'state': None, 'channels': [],
                    'event': None, 'ircclient': ircclient}
            self.server_monitor[host] = ping
            self.handle_monitor(host)

        ping = self.server_monitor[host]
        if channel in ping['channels']:
                msg = 'Ich überwache {} bereits für {}.'
                ircclient.send_message(msg.format(host, channel), channel)
        else:
            ping['channels'].append(channel)
            ircclient.send_message('Überwachung gestartet.', channel)

    def disable_monitor(self, ircclient, channel, host, port):
        if host in self.server_monitor:
            ping = self.server_monitor[host]
            if channel in ping['channels']:
                    ircclient.send_message('Überwachung gestoppt', channel)
                    ping['channels'].remove(channel)
            if not ping['channels']:
                    logger.info('Stopped observing {}.'.format(host))
                    utils.sched.cancel(ping['event'])
                    del self.server_monitor[host]
        else: ircclient.send_message('Wie auch immer.', channel)


COMMANDS = [
            UtilityCommands,
            ResearchCommands,
            SpassCommands,
            PingCommands,
           ]
