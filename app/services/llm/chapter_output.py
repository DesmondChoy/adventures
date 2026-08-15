"""Typed output contracts for generated adventure chapters."""

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CHOICE_MARKUP = re.compile(r"</?\s*choices\s*>", re.IGNORECASE)
_NARRATIVE_CHOICE_LINE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:(?:choice|option)\s*)?"
    r"(?:[abc]|[1-3])\s*[:.)-]\s+\S",
    re.IGNORECASE | re.MULTILINE,
)
_CHOICE_LABEL = re.compile(
    r"^\s*(?:(?:choice|option)\s*)?(?:[abc]|[1-3])\s*[:.)-]\s*",
    re.IGNORECASE,
)
_BRACKETED_TEXT = re.compile(r"\[[^\]\r\n]+\]")
_BRACKETED_LINE = re.compile(r"^\s*\[[^\]\r\n]+\]\s*$", re.MULTILINE)
_PLACEHOLDER_CHOICE = re.compile(
    r"\b(?:tbd|todo|placeholder|choice\s+text(?:\s+here)?|"
    r"option\s+(?:text|placeholder)|"
    r"(?:first|second|third)\s+(?:(?:meaningful|story-driven)\s+)?"
    r"(?:option|choice))\b",
    re.IGNORECASE,
)


def _validate_narrative(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Chapter narrative cannot be empty")
    if (
        _CHOICE_MARKUP.search(cleaned)
        or _NARRATIVE_CHOICE_LINE.search(cleaned)
        or _BRACKETED_LINE.search(cleaned)
    ):
        raise ValueError("Choice formatting leaked into chapter narrative")
    return cleaned


class NarrativeChapterResponse(BaseModel):
    """Structured output for lesson and conclusion chapters."""

    model_config = ConfigDict(extra="forbid")

    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _validate_narrative(value)


class StoryChapterResponse(NarrativeChapterResponse):
    """Structured output for story and reflect chapters."""

    choices: list[str] = Field(min_length=3, max_length=3)

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            choice = value.strip()
            if not choice:
                raise ValueError("Story choices cannot be empty")
            if (
                _CHOICE_MARKUP.search(choice)
                or _CHOICE_LABEL.search(choice)
                or _BRACKETED_TEXT.search(choice)
                or _PLACEHOLDER_CHOICE.search(choice)
            ):
                raise ValueError("Choice contains generation markup or placeholder text")
            cleaned.append(choice)

        normalized = {choice.casefold() for choice in cleaned}
        if len(normalized) != len(cleaned):
            raise ValueError("Story choices must be distinct")
        return cleaned


@dataclass(frozen=True)
class GeneratedChapter:
    """Provider-neutral chapter result after structured parsing and validation."""

    content: str
    choices: tuple[str, ...] = ()
