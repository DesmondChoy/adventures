"""
Legacy module for backwards compatibility.
All functionality has been moved to the websocket package.
"""

from app.services.websocket import (
    process_choice,
    stream_and_send_chapter,
    send_story_complete,
    generate_chapter,
    generate_summary_content,
)

__all__ = [
    "process_choice",
    "stream_and_send_chapter",
    "send_story_complete",
    "generate_chapter",
    "generate_summary_content",
]