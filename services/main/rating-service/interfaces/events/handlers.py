import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker):
    logger.info("Rating service has no incoming event consumers")
