# License: WTFPL (http://sam.zoy.org/wtfpl/)

from baumi import asynsocket

import socket
import logging
logger = logging.getLogger(__name__)

class IRCMessage:
    def __init__(self, message=''):
        self.nick = self.user = self.command = ''
        self.params = list()
        if message: self._split(message)

    def __str__(self):
        message = self.command
        if self.params:
            if len(self.params) > 1:
                message += ' ' + ' '.join(self.params[:-1])
            message += ' :' + self.params[-1]
        return message

    def _split(self, message):
        if message.startswith(':'):
            (prefix, message) = message[1:].split(' ', 1)
            if '!' in prefix:
                (self.nick, user_hostname) = prefix.split('!', 1)
                (self.user, hostname) = user_hostname.split('@', 1)
            else: self.user = prefix
        (self.command, *params) = message.split(' ')
        while params:
            param = params.pop(0)
            if param.startswith(':'):
                param = param[1:] + ' ' + ' '.join(params)
                params = False
            self.params.append(param.strip())

    def set_command(self, command): self.command = str(command).upper()
    def add_params(self, *params): self.params.extend(params)


class IRCClient(asynsocket.asynchat):
    def __init__(self, sched, nick, user, channel, host='irc.freenode.net', port=6667):
        super().__init__()
        (self.nick, self.user, self.channel) = (nick, user, channel)
        (self.host, self.port) = (host, port)
        self.sched = sched
        self.terminator = '\r\n'
        self.commands = dict()
        self.nick_list = set()
        self.start()

    def start(self):
        logger.info('IRC client started.')
        self.timeout_event = self.sched.enter(360, 1, self.restart, tuple())
        try:
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect((self.host, self.port))
        except socket.gaierror:
            logger.critical('Name resolution error. Restarting in 6 minutes')
        except: self.handle_error()
        self.nick_list = set()

    def disconnect(self):
        self.send_to_irc('PART', self.channel)
        self.send_to_irc('QUIT')
        self.handle_close()

    def restart(self):
        self.disconnect()
        self.start()

    def handle_connect(self):
        self.send_to_irc('NICK', self.nick)
        self.send_to_irc('USER', self.user, '8', '*', self.user)
        self.send_to_irc('JOIN', self.channel)

    def handle_close(self):
        logger.info('IRC client stopped.')
        self.close()

    def handle_error(self):
        logger.exception('Exception in IRCClient')

    def send_message(self, message, channel):
        if message:
            if '\n' in message:
                logger.error('Return in >{}<'.format(repr(message)))
                message = message.replace('\n', ' - ')
            logger.info('Sending {} to {}'.format(message, channel))
            self.send_to_irc('PRIVMSG', channel, message)

    def send_action(self, message, channel):
        if message:
            message = '{}ACTION {} {}'.format(chr(1), message, chr(1))
            self.send_message(message, channel)

    def send_to_irc(self, command, *params):
        msg = IRCMessage()
        msg.set_command(command)
        msg.add_params(*params)
        message = str(msg)
        self.send_line(message)

    def found_terminator(self, message):
        self.sched.cancel(self.timeout_event)
        self.timeout_event = self.sched.enter(360, 1, self.restart, tuple())

        msg = IRCMessage(message)
        if msg.command == 'PING':
            self.send_to_irc('PONG', *msg.params)
        elif msg.command == 'PRIVMSG':
            self.process(msg.nick, *msg.params)
        elif msg.command == '353':
            nicks = [nick.strip('@+ ') for nick in msg.params[-1].split()]
            self.nick_list = set(nicks)
            self.on_nicklist_changed()
        elif msg.command == 'JOIN':
            if msg.nick == self.nick:
                logger.info('Joined channel {}'.format(*msg.params))
            else:
                self.nick_list.add(msg.nick)
                self.on_nicklist_changed()
        elif msg.command in ('QUIT', 'PART'):
            self.nick_list.remove(msg.nick)
            self.on_nicklist_changed()
        elif msg.command == 'KICK':
            if msg.params[1] == self.nick:
                message = 'Was kicked from {}. Try rejoin in 60 sek.'
                logger.error(message.format(msg.params[0]))
                self.sched.enter(60, 1, self.send_to_irc, ('JOIN', self.channel))
            else:
                self.nick_list.remove(msg.params[1])
                self.on_nicklist_changed()
        elif msg.command == 'NICK':
            self.nick_list.remove(msg.nick)
            self.nick_list.add(*msg.params)
            self.on_nicklist_changed()
        elif msg.command in ('372', '375', '376'): pass # motd
        else: logger.debug(' - '.join((msg.nick, msg.user, msg.command, str(msg.params))))

    def process(self, nick, channel, message):
        if channel == self.nick: channel = nick
        if message.startswith('!') and len(message) > 1:
            (command, *message) = message[1:].split(' ', 1)
            if message: message = message[0]
            else: message = ''
            if command in self.commands:
                callback = self.commands[command]
                try: callback(nick, channel, message)
                except ValueError:
                    self.error_callback(command, nick, channel, message)
                else:
                    msg = '{} called command {} in {}: {}'
                    logger.info(msg.format(nick, command, channel, message))
            else: self.fallback_callback(command, nick, channel, message)
        else: self.use_brain(nick, channel, message)

    def fallback_callback(self, command, nick, channel, message):
        msg = '{} called unimplemented command {} in {}: {}'
        logger.info(msg.format(nick, command, channel, message))

    def error_callback(self, command, nick, channel, message):
        msg = 'Error: {} called command {} in {}: {}'
        logger.info(msg.format(nick, command, channel, message))

    def use_brain(self, nick, channel, message): pass

    def on_nicklist_changed(self):
        logger.info('Nicklist changed: {}'.format(sorted(self.nick_list)))
