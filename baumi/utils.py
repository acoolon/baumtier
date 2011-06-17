# License: WTFPL (http://sam.zoy.org/wtfpl/)
# baumtier by Thob

from baumi import config
from baumi import asynsocket

import logging
logging.basicConfig(format=config.LOGGING_FORMAT, filename=config.LOGFILE,
                    datefmt=config.LOGGING_DATEFTM, level=config.LOGGING_LEVEL)

logger = logging
sched = asynsocket.asynschedcore()
