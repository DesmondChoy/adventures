import logging
import json
import sys
import os
from typing import Any, Dict
from datetime import datetime


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

        # Print to console in a readable format
        print(f"[{log_data['timestamp']}] {log_data['level']} - {log_data['message']}")
        if "llm_prompt" in log_data:
            print(f"Prompt: {log_data['llm_prompt']}")
        if "llm_response" in log_data:
            print(f"Response: {log_data['llm_response']}")

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


def setup_logging():
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    logging.setLoggerClass(StructuredLogger)
    logger = logging.getLogger("story_app")
    logger.setLevel(logging.DEBUG)  # Keep logger level at DEBUG to capture all logs

    try:
        # Console handler - show DEBUG and above in console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)  # <----- CHANGE THIS LINE TO DEBUG
        logger.addHandler(console_handler)

        # File handler for persistent logs - keep all logs
        file_handler = logging.FileHandler("logs/app.log")
        file_handler.setLevel(
            logging.INFO
        )  # Keep file handler at INFO or DEBUG, depending on your needs. INFO is fine to reduce file size.
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup logging handlers: {str(e)}")
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.DEBUG
        )  # Fallback to DEBUG in case of setup failure
        logger = logging.getLogger("story_app")
        logger.error(f"Logging setup failed: {str(e)}")

    return logger
