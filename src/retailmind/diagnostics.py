"""Server-side exception traces without request data, exception values or secrets."""
from __future__ import annotations
import logging
import traceback


def log_failure(logger: logging.Logger, exc: Exception, *, code: str,
                correlation_id: str, level: int = logging.ERROR) -> None:
    # Exception messages may contain URLs, credentials or document content. Keep
    # actual exception types and traceback locations, without values or locals.
    traces = []
    current = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        traces.append(type(current).__name__)
        traces.extend(f'  {frame.filename}:{frame.lineno} in {frame.name}'
                      for frame in traceback.extract_tb(current.__traceback__))
        current = current.__cause__ or current.__context__
    logger.log(level, '%s correlation_id=%s\n%s', code, correlation_id, '\n'.join(traces))
