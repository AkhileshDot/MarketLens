import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager

logging.basicConfig(level="INFO", format="%(message)s", stream=sys.stdout)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, **fields) -> None:
    """Structured one-line JSON log, e.g. log_event(logger, event='analyze', ticker='INFY.NS')."""
    logger.info(json.dumps(fields, default=str))


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@contextmanager
def timed():
    """Usage: with timed() as t: ... ; after the block, t['latency_ms'] is set."""
    start = time.perf_counter()
    result: dict = {}
    yield result
    result["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
