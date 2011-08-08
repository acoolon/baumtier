# License: WTFPL (http://sam.zoy.org/wtfpl/)

from baumi import utils
from baumi import config
from baumi import asynsocket

import socket

logger = utils.logger.getLogger(__name__)

class IRCClient(asynsocket.asynchat):
    def __init__(self, nick, user, *channels,
                 host=config.IRC_DEFAULT_HOST, port=config.IRC_DEFAULT_PORT):
        super().__init__()
        (self.host, self.port) = (host, port)
        self.protocol = ircprotocol.IRCProtocol(self, nick, user)
        self.channels = channels
        self.terminator = '\r\n'
        self.commands = dict()
        self.start()

    def start(self):
        logger.info('IRC client started.')
        self.protocol.clear_channels()
        self.timeout_event = utils.sched.enter(config.IRC_TIMEOUT, 1,
                                              self.start, tuple())
        try:
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect((self.host, self.port))
        except socket.gaierror:
            string = 'Name resolution error. Restarting in {} minutes'
            logger.critical(string.format(config.IRC_TIMEOUT//60))
        except socket.error as err:
            if err.errno == 110:
                string = 'Connection timeout while starting. Restarting in {} minutes'
                logger.critical(string.format(config.IRC_TIMEOUT//60))
            else: self.handle_error()

    def handle_connect(self):
        self.protocol.send_nick()
        self.protocol.send_user()
        self.protocol.send_join(*self.channels)

    def disconnect(self):
        utils.sched.cancel(self.timeout_event)
        self.protocol.send_part(*self.channels)
        self.protocol.send_quit()

    def handle_close(self):
        logger.info('IRC client stopped.')
        self.close()

    def handle_error(self):
        logger.exception('Exception in IRCClient')

    def is_authorized(self, channel, nick):
        if channel == nick: return False
        channel = self.protocol.channels[channel]
        return channel.has_op(nick) or channel.has_voice(nick)

    def send_message(self, message, channel):
        if message:
            if '\n' in message:
                logger.error('Return in >{}<'.format(repr(message)))
                message = message.replace('\n', ' - ')
            logger.info('Sending {} to {}'.format(message, channel))
            self.protocol.send_message(message, channel)

    def send_action(self, message, channel):
        if message: self.protocol.send_action(message, channel)

    def found_terminator(self, message):
        if self.timeout_event in utils.sched.queue:
            utils.sched.cancel(self.timeout_event)
            self.timeout_event = utils.sched.enter(config.IRC_TIMEOUT, 1,
                                                  self.start, tuple())
        self.protocol.handle_message(message)

    def process(self, nick, channel, message):
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
        logger.warning(msg.format(nick, command, channel, message))

    def error_callback(self, command, nick, channel, message):
        msg = 'Error: {} called command {} in {}: {}'
        logger.info(msg.format(nick, command, channel, message))

    def use_brain(self, nick, channel, message):
        pass

    def on_nicklist_changed(self, channel):
        logger.info('Nicklist for {} changed.'.format(channel))
