#!/usr/bin/env pyhon
# License: WTFPL (http://sam.zoy.org/wtfpl/)
__version__ = '0.2'

from baumi import utils
from baumi import asynsocket

import time
import random
import socket

logger = utils.logger.getLogger(__name__)

GENERIC = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00'
QUESTION = GENERIC + b'\x01\x05\x00\x00\x00\x00\x00\x03'


class Ping: pass


class Pinger(asynsocket.dispatcher):
    def __init__(self):
        super().__init__()
        self.next_poke = list()
        self.pings = dict()
        self.done = False
        logger.info('Serverpinger started')
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', random.randint(1025, 8000)))

    def handle_close(self):
        logger.info('Serverpinger closed')
        for host in self.pings:
            ping = self.pings[host]
            utils.sched.cancel(ping.event)
        self.close()

    def handle_error(self):
        logger.exception('Exception in serverpinger')

    def writable(self):
        return bool(self.next_poke)

    def handle_write(self):
        ping = self.next_poke.pop(0)
        ping.ping_send = time.time()
        ping.event = utils.sched.enter(2, 1, self.handle_timeout, (ping.host,))
        self.pings[ping.host] = ping
        self.sendto(QUESTION, (ping.host, ping.port))

    def handle_read(self):
        (data, (host, port)) = self.recvfrom(1400)
        if len(data) == 23 and data[15] == 1:  # Is ping packet?
            if data[-1] == 6: state = 'online'
            elif data[-1] == 8: state = 'voll'
            elif data[-1] == 4: state = 'online, aber geschlossen'
            else: state = 'am rebooten'
            try: ping = self.pings.pop(host)
            except KeyError: pass
            else:
                delay = round((time.time() - ping.ping_send) * 1000, 2)
                utils.sched.cancel(ping.event)
                ping.callback(host, state, delay)
        self.close_maybe()

    def handle_timeout(self, host):
        try: ping = self.pings.pop(host)
        except KeyError: pass
        else: ping.callback(host, 'offline', 9999)
        self.close_maybe()

    def close_maybe(self):
        if self.done and len(self.pings) == 0:
            self.handle_close()

    def poke(self, host, port, callback):
        try: host = socket.gethostbyname(host)
        except socket.gaierror: return False
        else:
            ping = Ping()
            ping.callback = callback
            ping.host = host
            ping.port = port
            self.next_poke.append(ping)
            return True
