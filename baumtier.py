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


class Baumi(ircclient.IRCClient):
    def __init__(self, *channels, nick='Baumtierchen', user='baumi'):
        super().__init__(nick, user, *channels)

    def is_authorized(self, channel, nick):
        if '#psde-staff' in self.protocol.channels:
            return super().is_authorized('#psde-staff', nick)
        else: return super().is_authorized(channel, nick)

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

def main():
#    Baumi('#baumi-test', nick='Baumi')
    Baumi('#psde', '#psde-staff')
    utils.sched.run()

if __name__ == '__main__':
    main()
