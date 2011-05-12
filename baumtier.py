#!/usr/bin/env python
# License: WTFPL (http://sam.zoy.org/wtfpl/)
# baumtier by Thob
# Usage: run it (python 333

__version__ = '0.1'

from baumi import asynsocket
from baumi import ircclient
from baumi import commands

import time
import logging
logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s',
    filename='logs/{}.log'.format(time.strftime('%Y_%m_%d_%H_%M')),
    datefmt='%d-%m %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger('baumi')


class Baumi(ircclient.IRCClient, commands.Commands):
    def __init__(self, sched, nick='Baumtierchen', user='baumi', channel='#psde'):
        super().__init__(sched, nick, user, channel)
        self.commands = {'hilfe': self.help, 'help': self.help}
        commands.Commands.__init__(self)

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
