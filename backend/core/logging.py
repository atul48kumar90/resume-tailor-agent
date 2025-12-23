# core/logging.py
import logging
import sys
from contextvars import ContextVar

# Request ID context
request_id_ctx: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Always guarantee attribute existence
        record.request_id = request_id_ctx.get() or "-"
        return True


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] "
        "[request_id=%(request_id)s] "
        "%(name)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # 🔒 CRITICAL FIX: attach filter to HANDLER
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid duplicate handlers on reload (uvicorn --reload)
    root.handlers.clear()
    root.addHandler(handler)
