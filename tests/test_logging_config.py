import json
import logging

from app.utils.logging_config import JsonLogFormatter


def test_json_log_formatter_preserves_structured_llm_fields() -> None:
    record = logging.LogRecord(
        name="story_app",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="OpenAI structured chapter request",
        args=(),
        exc_info=None,
    )
    record.llm_call_id = "call-123"
    record.llm_prompt = {"system": "system", "user": "user"}
    record.chapter_number = 5

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["message"] == "OpenAI structured chapter request"
    assert payload["llm_call_id"] == "call-123"
    assert payload["llm_prompt"] == {"system": "system", "user": "user"}
    assert payload["chapter_number"] == 5
    assert payload["llm_bodies_included"] is True


def test_json_log_formatter_omits_llm_bodies_in_production_mode() -> None:
    record = logging.LogRecord(
        name="story_app",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="OpenAI text response",
        args=(),
        exc_info=None,
    )
    record.llm_call_id = "call-123"
    record.llm_response = "private generated content"
    record.llm_response_chars = 25
    record.adventure_id = "adventure-123"

    payload = json.loads(
        JsonLogFormatter(include_llm_bodies=False).format(record)
    )

    assert "llm_response" not in payload
    assert payload["llm_bodies_included"] is False
    assert payload["llm_response_chars"] == 25
    assert payload["llm_call_id"] == "call-123"
    assert payload["adventure_id"] == "adventure-123"
