"""Unit tests for character sheet parse/idempotency and multimodal Gemini contents."""

from __future__ import annotations

import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from app.services.character_sheet import (
    CharacterSheet,
    ReferenceImage,
    build_chapter_prompt_with_sheet,
    build_character_sheet_prompt,
    ensure_character_sheet,
    get_character_sheet,
)
from app.services.image_generation_service import ImageGenerationService


def _tiny_jpeg_b64() -> str:
    buf = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_character_sheet_round_trip_metadata() -> None:
    jpeg_b64 = _tiny_jpeg_b64()
    sheet = CharacterSheet.from_metadata_dict(
        {
            "jpeg_b64": jpeg_b64,
            "mime": "image/jpeg",
            "locked_chapter": 1,
            "agency_name": "Brave Fox",
            "visual_summary": "kid + fox",
        }
    )
    dumped = sheet.to_metadata_dict()
    assert dumped["agency_name"] == "Brave Fox"
    assert dumped["mime"] == "image/jpeg"
    assert dumped["locked_chapter"] == 1
    assert base64.b64decode(dumped["jpeg_b64"]) == sheet.jpeg_bytes
    ref = sheet.to_reference_image()
    assert isinstance(ref, ReferenceImage)
    assert ref.jpeg_bytes == sheet.jpeg_bytes


def test_get_character_sheet_returns_none_when_missing() -> None:
    state = SimpleNamespace(metadata={})
    assert get_character_sheet(state) is None


def test_get_character_sheet_returns_none_when_corrupt() -> None:
    state = SimpleNamespace(metadata={"character_sheet": {"jpeg_b64": "!!!"}})
    assert get_character_sheet(state) is None


@pytest.mark.asyncio
async def test_ensure_character_sheet_is_idempotent() -> None:
    jpeg_b64 = _tiny_jpeg_b64()
    state = SimpleNamespace(
        metadata={
            "agency": {
                "name": "Brave Fox",
                "category": "companions",
                "visual_details": "orange fur",
            },
            "adventure_id": "adv-1",
        },
        protagonist_description="A child in a red coat",
        selected_sensory_details={"visuals": "blue moonlight"},
    )
    image_service = SimpleNamespace(
        generate_image_async=AsyncMock(return_value=jpeg_b64)
    )

    first = await ensure_character_sheet(state, image_service=image_service)
    assert first is not None
    assert "character_sheet" in state.metadata
    assert image_service.generate_image_async.await_count == 1

    second = await ensure_character_sheet(state, image_service=image_service)
    assert second is not None
    assert second.jpeg_bytes == first.jpeg_bytes
    assert image_service.generate_image_async.await_count == 1


@pytest.mark.asyncio
async def test_ensure_character_sheet_fails_soft_on_empty_image() -> None:
    state = SimpleNamespace(
        metadata={"agency": {"name": "Lantern", "category": "items", "visual_details": ""}},
        protagonist_description="A young adventurer",
        selected_sensory_details={},
    )
    image_service = SimpleNamespace(
        generate_image_async=AsyncMock(return_value=None)
    )
    result = await ensure_character_sheet(state, image_service=image_service)
    assert result is None
    assert "character_sheet" not in state.metadata


def test_build_prompts_include_match_reference_cue() -> None:
    sheet_prompt = build_character_sheet_prompt(
        protagonist_description="A child in a red coat",
        agency_name="Brave Fox",
        agency_category="companions",
        agency_visual_details="orange fur, green scarf",
        story_visual_sensory_detail="misty dawn",
    )
    assert "character reference sheet" in sheet_prompt.lower()
    assert "Brave Fox" in sheet_prompt
    assert "plain" in sheet_prompt.lower()

    chapter_prompt = build_chapter_prompt_with_sheet(
        image_scene_description="Crossing a glowing bridge",
        story_visual_sensory_detail="blue moonlight",
    )
    assert "match" in chapter_prompt.lower()
    assert "reference" in chapter_prompt.lower()
    assert "Crossing a glowing bridge" in chapter_prompt


def test_generate_image_multimodal_contents_when_reference_present(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(source, format="PNG")
    inline_data = SimpleNamespace(data=source.getvalue())
    part = SimpleNamespace(inline_data=inline_data)
    content = SimpleNamespace(parts=[part])
    response = SimpleNamespace(candidates=[SimpleNamespace(content=content)])
    generate_content = MagicMock(return_value=response)

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(
        "app.services.image_generation_service.genai.Client",
        MagicMock(return_value=client),
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    service = ImageGenerationService()

    ref_bytes = base64.b64decode(_tiny_jpeg_b64())
    reference = ReferenceImage(jpeg_bytes=ref_bytes)

    with caplog.at_level("INFO", logger="story_app"):
        result = service._generate_image(
            "Match the character in the reference image. Scene: a bridge.",
            retries=0,
            context={"adventure_id": "adv-2", "chapter_number": 3},
            reference_image=reference,
        )

    assert result is not None
    call = generate_content.call_args
    contents = call.kwargs["contents"]
    assert isinstance(contents, list)
    assert contents[0].startswith("Match the character")
    ref_part = contents[1]
    assert getattr(ref_part, "inline_data", None) is not None
    assert ref_part.inline_data.data == ref_bytes
    assert ref_part.inline_data.mime_type == "image/jpeg"

    request_record = next(
        record for record in caplog.records if record.message == "Gemini image request"
    )
    assert request_record.image_gen_has_reference is True
