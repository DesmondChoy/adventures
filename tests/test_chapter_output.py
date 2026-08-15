from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.models.story import AdventureState, ChapterType
from app.services.llm import prompt_engineering
from app.services.llm.chapter_output import GeneratedChapter, StoryChapterResponse
from app.services.llm.prompt_templates import AGENCY_GUIDANCE
from app.services.websocket import content_generator


def test_story_chapter_response_accepts_clean_structured_output() -> None:
    response = StoryChapterResponse(
        content="Mira reached the glowing bridge as the wind began to sing.",
        choices=[
            "Cross the bridge with the lantern held high.",
            "Follow the river beneath the bridge.",
            "Ask the wind where the bridge leads.",
        ],
    )

    assert len(response.choices) == 3


@pytest.mark.parametrize(
    ("content", "choices"),
    [
        (
            "Mira reached the bridge.\n<CHOICES>\nChoice A: Cross it\n</CHOICES>",
            ["Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.\nChoice A: Cross it",
            ["Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["[Cross it]", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["Choice A: Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["First meaningful option", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["1. Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["Option 1: Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["A) Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["Cross it [insert vivid detail]", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["TBD", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.",
            ["Choice text here", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.\n1. Cross it",
            ["Cross it", "Follow the river", "Ask the wind"],
        ),
        (
            "Mira reached the bridge.\n[Cross it]",
            ["Cross it", "Follow the river", "Ask the wind"],
        ),
    ],
)
def test_story_chapter_response_rejects_generation_debris(
    content: str,
    choices: list[str],
) -> None:
    with pytest.raises(ValidationError):
        StoryChapterResponse(content=content, choices=choices)


def test_story_chapter_response_requires_three_distinct_choices() -> None:
    with pytest.raises(ValidationError):
        StoryChapterResponse(
            content="Mira reached the bridge.",
            choices=["Cross the bridge", "Cross the bridge", "Ask the wind"],
        )


def test_build_prompt_appends_validation_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        prompt_engineering,
        "build_system_prompt",
        lambda _state: "system",
    )
    monkeypatch.setattr(
        prompt_engineering,
        "build_user_prompt",
        lambda *_args: "user",
    )

    _, user_prompt = prompt_engineering.build_prompt(
        cast(AdventureState, object()),
        context={"validation_feedback": "Return clean structured choices."},
    )

    assert user_prompt.endswith(
        "# Retry Correction\nReturn clean structured choices."
    )


def test_system_prompt_does_not_duplicate_agency_category() -> None:
    state = SimpleNamespace(
        current_chapter_number=5,
        metadata={
            "agency": {
                "category": "Take on a Profession",
                "name": "Craftsperson",
                "description": "Take on a Profession: Craftsperson - Build things.",
            }
        },
        selected_narrative_elements={"settings": "Aurora Lagoon"},
        selected_theme="Courage",
        selected_moral_teaching="Bravery lights the way",
    )

    prompt = prompt_engineering.build_system_prompt(
        cast(AdventureState, state)
    )

    assert "Take on a Profession: Craftsperson" in prompt
    assert "Take on a Profession: Take on a Profession" not in prompt


def test_reflect_agency_guidance_names_the_selected_agency() -> None:
    guidance = AGENCY_GUIDANCE["correct"].format(
        agency_type="choice",
        agency_name="Craftsperson",
    )

    assert "choice (Craftsperson)" in guidance


class _RetryingStructuredService:
    def __init__(self) -> None:
        self.attempts = 0
        self.contexts: list[object] = []

    async def generate_structured_chapter(self, **kwargs: Any) -> GeneratedChapter:
        self.attempts += 1
        self.contexts.append(kwargs.get("context"))
        if self.attempts == 1:
            raise ValidationError.from_exception_data("StoryChapterResponse", [])
        return GeneratedChapter(
            content="Mira reached the bridge.",
            choices=("Cross it", "Follow the river", "Ask the wind"),
        )


@pytest.mark.asyncio
async def test_chapter_generation_retries_provider_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RetryingStructuredService()
    monkeypatch.setattr(content_generator, "_llm_service", service)

    chapter = await content_generator.generate_chapter_content_with_retries(
        story_config={},
        state=cast(AdventureState, object()),
        chapter_type=ChapterType.STORY,
        question=None,
        current_chapter_number=2,
        max_attempts=2,
    )

    assert service.attempts == 2
    assert service.contexts[0] is None
    assert "previous response failed" in cast(
        dict[str, str], service.contexts[1]
    )["validation_feedback"]
    assert [choice.text for choice in chapter.choices] == [
        "Cross it",
        "Follow the river",
        "Ask the wind",
    ]


@pytest.mark.asyncio
async def test_chapter_generation_does_not_retry_authentication_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAuthenticationError(Exception):
        pass

    class FailingService:
        def __init__(self) -> None:
            self.attempts = 0

        async def generate_structured_chapter(self, **_kwargs: Any) -> GeneratedChapter:
            self.attempts += 1
            raise FakeAuthenticationError("invalid key")

    service = FailingService()
    monkeypatch.setattr(content_generator, "AuthenticationError", FakeAuthenticationError)
    monkeypatch.setattr(content_generator, "_llm_service", service)

    with pytest.raises(FakeAuthenticationError, match="invalid key"):
        await content_generator.generate_chapter_content_with_retries(
            story_config={},
            state=cast(AdventureState, object()),
            chapter_type=ChapterType.STORY,
            question=None,
            current_chapter_number=1,
        )

    assert service.attempts == 1
