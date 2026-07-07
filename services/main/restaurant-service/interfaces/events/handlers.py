import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker):
    logger.info("Restaurant service has no external event consumers to register")
