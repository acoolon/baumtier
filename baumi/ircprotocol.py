# License: WTFPL (http://sam.zoy.org/wtfpl/)

import textwrap

from baumi import utils

logger = utils.logger.getLogger(__name__)


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


class IRCChannel:
    def __init__(self, name):
        self.name = name
        self.users = set()
        self.modes = dict()

    def __str__(self): return self.name
    def __len__(self): return len(self.users)
    def __iter__(self): return iter(self.users)

    def add(self, user):
        if ' ' in user:
            logger.debug('on add {}'.format(repr(user)))
            user = user.strip()
        self.users.add(user.strip('@+'))
        if user.startswith('@'): self.set_mode(user.strip('@'), '+o')
        elif user.startswith('+'): self.set_mode(user.strip('+'), '+v')

    def remove(self, user):
        if ' ' in user:
            logger.debug('on remove {}'.format(repr(user)))
            user = user.strip()
        try: self.users.remove(user)
        except KeyError: logger.debug('Cant remove user {}'.format(user))
        if user in self.modes: del self.modes[user]

    def rename(self, user, new_name):
        if ' ' in user:
            logger.debug('on rename (user) {}'.format(repr(user)))
            user = user.strip()
        if ' ' in new_name:
            logger.debug('on rename (new_name) {}'.format(repr(user)))
            new_name = new_name.strip()
        if user in self.modes: self.modes[new_name] = self.modes.pop(user)
        self.remove(user)
        self.add(new_name)

    def set_mode(self, user, mode):
        (change, new_mode) = mode
        if user in self.modes:
            user_mode = self.modes[user]
            if change == '+': user_mode += new_mode
            elif change == '-': user_mode = user_mode.replace(new_mode, '')
        elif change == '+': self.modes[user] = new_mode

    def has_op(self, user): return 'o' in self.modes.get(user, '')
    def has_voice(self, user): return 'v' in self.modes.get(user, '')


class IRCProtocol:
    def __init__(self, client, nick, user):
        self.client = client
        (self.nick, self.user) = (nick, user)
        self.channels = dict()

    def clear_channels(self): self.channels = dict()

    def send_to_irc(self, command, *params):
        msg = IRCMessage()
        msg.set_command(command)
        msg.add_params(*params)
        message = str(msg)
        self.client.send_line(message)

    def send_nick(self, nick=''): self.send_to_irc('NICK', nick or self.nick)
    def send_user(self): self.send_to_irc('USER', self.user, '8', '*', self.user)
    def send_join(self, *channels): self.send_to_irc('JOIN', ','.join(channels))
    def send_part(self, *channels): self.send_to_irc('PART', ','.join(channels))
    def send_quit(self, *reason): self.send_to_irc('QUIT', *reason)
    def send_pong(self, payload): self.send_to_irc('PONG', payload)

    def send_message(self, message, channel):
        for line in textwrap.wrap(message, 442):
            self.send_to_irc('PRIVMSG', channel, line)

    def send_action(self, message, channel):
        message = '{}ACTION {} {}'.format(chr(1), message, chr(1))
        self.send_message(message, channel)

    def handle_message(self, message):
        msg = IRCMessage(message)
        if msg.command == 'PING': self.handle_ping(msg)
        elif msg.command == 'PRIVMSG': self.handle_privmsg(msg)
        elif msg.command == '353': self.handle_nicklist(msg)
        elif msg.command == 'JOIN': self.handle_join(msg)
        elif msg.command == 'NICK': self.handle_nick(msg)
        elif msg.command == 'MODE': self.handle_mode(msg)
        elif msg.command == 'PART': self.handle_part(msg)
        elif msg.command == 'QUIT': self.handle_quit(msg)
        elif msg.command == 'KICK': self.handle_kick(msg)
        elif msg.command == '433': logger.critical(msg.params[-1])
        elif msg.command == 'NOTICE': logger.info(msg.params[-1])
        elif msg.command in ('372', '375', '376'): pass  # motd
        elif msg.command in ('001', '002', '003', '004', '005'): pass
        elif msg.command in ('251', '252', '253', '254', '255'): pass
        elif msg.command in ('265', '266', '250', '366'): pass
        elif msg.command in ('332', '333', '328'): pass
        else:
            logger.warning(' - '.join((msg.nick, msg.user, msg.command, str(msg.params))))

    def handle_ping(self, msg): self.send_pong(*msg.params)
    def handle_privmsg(self, msg):
        (channel, message) = msg.params
        if channel == self.nick:
            channel = msg.nick
            logger.info('{} told me >{}<'.format(channel, message))
        self.client.process(msg.nick, channel, message)

    def handle_nicklist(self, msg):
        (*crap, channel_name, nicks) = msg.params
        channel = self.channels[channel_name]
        for nick in nicks.split(): channel.add(nick)
        self.client.on_nicklist_changed(channel_name)

    def handle_join(self, msg):
        channel_names = msg.params[0].split(',')
        if msg.nick == self.nick:
            for channel_name in channel_names:
                self.channels[channel_name] = IRCChannel(channel_name)
                logger.info('Joined channel {}'.format(channel_name))
        else:
            logger.debug('{} joined {}'.format(msg.nick, channel_names))
            for channel_name in channel_names:
                self.channels[channel_name].add(msg.nick)
                self.client.on_nicklist_changed(channel_name)

    def handle_nick(self, msg):
        for channel in self.channels.values():
            if msg.nick in channel:
                m = '{} renamed to {} in channel {}'
                logger.debug(m.format(msg.nick, msg.params[0], str(channel)))
                channel.rename(msg.nick, *msg.params)
                self.client.on_nicklist_changed(str(channel))

    def handle_mode(self, msg):
        (*channel_name, mode, nick) = msg.params
        if channel_name:
            channel = self.channels[channel_name[0]]
            channel.set_mode(nick, mode)
        else:
            for channel in self.channels:
                if nick in channel:
                    channel.set_mode(nick, mode)

    def handle_part(self, msg):
        channel_names = msg.params[0].split(',')
        if msg.nick == self.nick:
            for channel_name in channel_names:
                logger.info('Left channel {}'.format(channel_name))
                del self.channels[channel_name]
                self.client.on_nicklist_changed(channel_name)
        else:
            logger.debug('{} parted {}'.format(msg.nick, *msg.params))
            for channel_name in channel_names:
                self.channels[channel_name].remove(msg.nick)
                self.client.on_nicklist_changed(channel_name)

    def handle_quit(self, msg):
        for channel in self.channels.values():
            if msg.nick in channel:
                m = '{} quit in channel {}'
                logger.debug(m.format(msg.nick, str(channel)))
                channel.remove(msg.nick)
                self.client.on_nicklist_changed(str(channel))

    def handle_kick(self, msg):
        (channel_name, nick, reason) = msg.params
        logger.debug('{} was kicked from {}'.format(nick, channel_name))
        self.channels[channel_name].remove(nick)
        if nick == self.nick:
            message = 'Was kicked from {} with reason {}. Rejoin in 60 sek.'
            logger.error(message.format(channel_name, repr(reason)))
            utils.sched.enter(60, 1, self.send_join, (channel_name,))
            del self.channels[channel_name]
        self.client.on_nicklist_changed(channel_name)
