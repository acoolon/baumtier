#!/usr/bin/env python
# License: WTFPL (http://sam.zoy.org/wtfpl/)
# baumtier by Thob
# Usage: run it (python 3)

from baumi import utils
from baumi import config
from baumi import commands
from baumi import ircclient

import os

logger = utils.logger.getLogger('baumi')


class Baumi(ircclient.IRCClient, commands.Commands):
    def __init__(self, *channels, nick='Baumtierchen', user='baumi'):
        super().__init__(nick, user, *channels)

    def start(self):
        super().start()
        self.commands = {'hilfe': self.help, 'help': self.help}
        commands.Commands.__init__(self)

    def handle_close(self):
        commands.Commands.close(self)
        super().handle_close()

    def error_callback(self, command, nick, channel, message):
        cmd = self.commands[command]
        if cmd.__doc__:
            msg = 'So geht es richtig: !{} {}'
            msg = msg.format(command, cmd.__doc__.split('\n')[0])
            self.send_message(msg, nick)

    def is_authorized(self, channel, nick):
        if '#psde-staff' in self.protocol.channels:
            return super().is_authorized('#psde-staff', nick)
        else: return super().is_authorized(channel, nick)

    def use_brain(self, nick, channel, message):
        if message.startswith(self.protocol.nick):  # somehow important
            logger.info('Brain on: {}-{}-{}'.format(nick, channel, message))
            if 'line' in message:  # online/offline
                if 'ero' in message or 'aanx' in message:
                    self.ping(nick, channel, 'zero')
                elif 'ez' in message or 'zpx' in message:
                    self.ping(nick, channel, 'ez')
            elif 'ink' in message:  # link/Link
                (crap, intresting) = message.split('ink ')
                words = intresting.split(' ')
                if words[0] == 'für':
                    next_word = words[1]
                    if next_word in ('der', 'die', 'das'):
                        next_word = words[2]
                    self.link(nick, channel, next_word)

    def on_nicklist_changed(self, channel_name):
        path = config.NICKFILE.format(channel_name)
        if channel_name in self.protocol.channels:
            with open(path, 'w') as f_nicklist:
                channel = self.protocol.channels[channel_name]
                f_nicklist.write('\n'.join(sorted(channel)))
                f_nicklist.close()
        else:
            try: os.remove(path)
            except EnvironmentError: logger.error('Cant delet {}'.format(path))
            else: logger.debug('Deleted {}'.format(path))

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
                    (short_help, *long_help) = cmd.__doc__.split('\n')
                    msg = '!{} {}'.format(cmd.__name__, short_help)
                    self.send_message(msg, nick)
                    for line in long_help:
                        self.send_message(line.strip(), nick)
                else: self.send_message('Kenn ich nicht.', nick)
        else:
            self.send_message('Baumtier v{}'.format(config.__version__), nick)
            self.send_message('Kommandos sind:', nick)
            cmds = list()
            for cmd_name in self.commands:
                cmd = self.commands[cmd_name]
                if cmd.__doc__: cmds.append('!' + cmd_name)
            self.send_message(', '.join(cmds), nick)
            self.send_message('!hilfe [command] für mehr Informationen', nick)


def main():
#    Baumi('#baumi-test', nick='Baumi')
    Baumi('#psde', '#psde-staff')
    utils.sched.run()

if __name__ == '__main__':
    main()
