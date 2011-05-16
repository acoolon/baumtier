# License: WTFPL (http://sam.zoy.org/wtfpl/)

import os
import time
import logging

__version__ = '0.2'

DATA_PATH = 'data'
LOG_PATH = os.path.join(DATA_PATH, 'logs')
NICKLIST_PATH = os.path.join(DATA_PATH, 'nicklists')

LOGFILE = os.path.join(LOG_PATH, '{}.log'.format(time.strftime('%m_%d_%H')))
NICKFILE = os.path.join(NICKLIST_PATH, '{}.list')
BOOKMARKFILE = os.path.join(DATA_PATH, 'bookmarks')

LOGGING_FORMAT = '%(asctime)s %(name)s %(levelname)s:%(message)s'
LOGGING_DATEFTM = '%d-%m %H:%M:%S'
LOGGING_LEVEL = logging.DEBUG

IRC_DEFAULT_HOST = 'irc.freenode.net'
IRC_DEFAULT_PORT = 6667
IRC_TIMEOUT = 360

### create dirs
for d in (DATA_PATH, LOG_PATH, NICKLIST_PATH):
    if not os.path.exist(d): os.makedirs(d)
