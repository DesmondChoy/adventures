import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Dict

_STANDARD_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__)


class JsonLogFormatter(logging.Formatter):
    """Serialize messages and structured ``extra`` fields as valid JSON lines."""

    def __init__(self, *, include_llm_bodies: bool = True) -> None:
        super().__init__()
        self.include_llm_bodies = include_llm_bodies

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        llm_body_present = False
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS and not key.startswith("_"):
                if key in {"llm_prompt", "llm_response"}:
                    llm_body_present = True
                    if not self.include_llm_bodies:
                        continue
                payload[key] = value
        if llm_body_present:
            payload["llm_bodies_included"] = self.include_llm_bodies
        if record.exc_info:
            if self.include_llm_bodies or not getattr(
                record, "llm_call_id", None
            ):
                payload["exception"] = self.formatException(record.exc_info)
            else:
                payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str)


class StructuredLogger(logging.Logger):
    def _log_structured(
        self,
        level: int,
        msg: str,
        args: tuple,
        exc_info: Any = None,
        extra: Dict = None,
        **kwargs,
    ):
        if extra is None:
            extra = {}

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": logging.getLevelName(level),
            "message": msg % args if args else msg,
            "session_id": extra.get("session_id", "no_session"),
            "request_id": extra.get("request_id", "no_request"),
            "path": extra.get("path", ""),
            "method": extra.get("method", ""),
        }

        # Add any LLM-related data if present
        if "llm_prompt" in extra:
            log_data["llm_prompt"] = extra["llm_prompt"]
        if "llm_response" in extra:
            log_data["llm_response"] = extra["llm_response"]

        # Add any additional extra fields
        for key, value in (extra or {}).items():
            if key not in [
                "session_id",
                "request_id",
                "path",
                "method",
                "llm_prompt",
                "llm_response",
            ]:
                log_data[key] = value

        # Safely serialize to JSON
        try:
            log_string = json.dumps(log_data)
        except Exception as e:
            # Handle serialization errors
            log_data["serialization_error"] = str(e)
            # Remove potentially problematic fields
            for k in ["llm_prompt", "llm_response"]:
                if k in log_data:
                    log_data[k] = "<serialization failed>"
            log_string = json.dumps(log_data)

        # Log structured JSON
        self.log(level, log_string)

    def info(self, msg: str, *args, **kwargs):
        self._log_structured(logging.INFO, msg, args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._log_structured(logging.ERROR, msg, args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._log_structured(logging.WARNING, msg, args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self._log_structured(logging.DEBUG, msg, args, **kwargs)


def _is_production_environment() -> bool:
    app_environment = os.getenv("APP_ENVIRONMENT", "").strip().lower()
    if app_environment in {"production", "prod"}:
        return True
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_ENVIRONMENT_NAME")
    )


def setup_logging():
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger("story_app")
    logger.setLevel(logging.DEBUG)  # Keep logger level at DEBUG to capture all logs
    is_production = _is_production_environment()

    try:
        # Console handler - show INFO and above in console to reduce verbosity
        # Change to INFO to reduce debug logging in the console
        # Wrap stdout to handle potential encoding issues on Windows console
        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        console_handler = logging.StreamHandler(utf8_stdout)
        console_handler.setLevel(logging.INFO if is_production else logging.DEBUG)
        # Use a basic formatter for the console to avoid double printing from StructuredLogger
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for persistent logs - keep all logs
        # Ensure file handler also uses UTF-8
        file_handler = RotatingFileHandler(
            "logs/fastapi_server.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(
            logging.INFO
        )  # Keep file handler at INFO or DEBUG, depending on your needs. INFO is fine to reduce file size.
        file_handler.setFormatter(
            JsonLogFormatter(include_llm_bodies=not is_production)
        )
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup logging handlers: {str(e)}")
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO
        )  # Fallback to INFO in case of setup failure
        logger = logging.getLogger("story_app")
        logger.error(f"Logging setup failed: {str(e)}")

    return logger
