"""Locked protagonist+agency character sheet for chapter image consistency.

Stored in state.metadata["character_sheet"] as JPEG base64 so resume needs no
schema migration. Parsed at this boundary before Gemini sees any bytes.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, TypedDict

logger = logging.getLogger("story_app")

CHARACTER_SHEET_MIME: Literal["image/jpeg"] = "image/jpeg"


class CharacterSheetDict(TypedDict):
    jpeg_b64: str
    mime: Literal["image/jpeg"]
    locked_chapter: int
    agency_name: str
    visual_summary: str


@dataclass(frozen=True)
class ReferenceImage:
    """Bytes Gemini can condition on. No adventure/metadata knowledge."""

    jpeg_bytes: bytes
    mime: Literal["image/jpeg"] = CHARACTER_SHEET_MIME


@dataclass(frozen=True)
class CharacterSheet:
    """Locked protagonist+agency reference for ch>=2 image gen."""

    jpeg_bytes: bytes
    mime: Literal["image/jpeg"]
    locked_chapter: int
    agency_name: str
    visual_summary: str

    def to_reference_image(self) -> ReferenceImage:
        return ReferenceImage(jpeg_bytes=self.jpeg_bytes, mime=self.mime)

    def to_metadata_dict(self) -> CharacterSheetDict:
        return {
            "jpeg_b64": base64.b64encode(self.jpeg_bytes).decode("ascii"),
            "mime": self.mime,
            "locked_chapter": self.locked_chapter,
            "agency_name": self.agency_name,
            "visual_summary": self.visual_summary,
        }

    @classmethod
    def from_metadata_dict(cls, raw: Dict[str, Any]) -> "CharacterSheet":
        if not isinstance(raw, dict):
            raise ValueError("character_sheet metadata must be a dict")
        jpeg_b64 = raw.get("jpeg_b64")
        if not isinstance(jpeg_b64, str) or not jpeg_b64.strip():
            raise ValueError("character_sheet missing jpeg_b64")
        try:
            jpeg_bytes = base64.b64decode(jpeg_b64, validate=True)
        except Exception as exc:
            raise ValueError("character_sheet jpeg_b64 is not valid base64") from exc
        if not jpeg_bytes:
            raise ValueError("character_sheet jpeg_b64 decoded empty")
        mime = raw.get("mime") or CHARACTER_SHEET_MIME
        if mime != CHARACTER_SHEET_MIME:
            raise ValueError(f"unsupported character_sheet mime: {mime}")
        locked_chapter = int(raw.get("locked_chapter") or 1)
        agency_name = str(raw.get("agency_name") or "").strip() or "Unknown Agency"
        visual_summary = str(raw.get("visual_summary") or "").strip()
        return cls(
            jpeg_bytes=jpeg_bytes,
            mime=CHARACTER_SHEET_MIME,
            locked_chapter=locked_chapter,
            agency_name=agency_name,
            visual_summary=visual_summary,
        )


def get_character_sheet(state: Any) -> Optional[CharacterSheet]:
    """Return parsed sheet from state.metadata, or None if missing/invalid."""
    metadata = getattr(state, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("character_sheet")
    if not raw:
        return None
    try:
        return CharacterSheet.from_metadata_dict(raw)
    except ValueError as exc:
        logger.warning("Ignoring corrupt character_sheet metadata: %s", exc)
        return None


def build_character_sheet_prompt(
    *,
    protagonist_description: str,
    agency_name: str,
    agency_category: str,
    agency_visual_details: str,
    story_visual_sensory_detail: str,
) -> str:
    """Neutral-pose character reference sheet prompt (plain background)."""
    protagonist = (protagonist_description or "A young adventurer").strip()
    agency = (agency_name or "their companion").strip()
    category = (agency_category or "").strip()
    visuals = (agency_visual_details or "").strip()
    mood = (story_visual_sensory_detail or "").strip()

    agency_line = agency
    if category:
        agency_line = f"{agency} ({category})"
    if visuals:
        agency_line = f"{agency_line}: {visuals}"

    mood_clause = f" Soft world mood hint: {mood}." if mood else ""

    return (
        "Character reference sheet for a children's storybook, not a story scene. "
        f"Show the protagonist ({protagonist}) together with their agency "
        f"({agency_line}). Neutral standing pose, plain light backdrop, clear face, "
        "outfit, and agency props visible for later consistency. Full or three-quarter "
        f"body, colorful storybook illustration style, square composition.{mood_clause}"
    )


def build_chapter_prompt_with_sheet(
    *,
    image_scene_description: str,
    story_visual_sensory_detail: str = "",
) -> str:
    """Scene prompt when a character-sheet reference image is attached."""
    scene = (image_scene_description or "").strip()
    mood = (story_visual_sensory_detail or "").strip()
    mood_clause = f" Atmosphere: {mood}." if mood else ""
    return (
        "Storybook illustration matching the character in the reference image. "
        "Keep the protagonist and their agency visually consistent with the reference "
        f"(same face, outfit, colors, and agency props). Scene: {scene}.{mood_clause}"
    )


async def ensure_character_sheet(
    state: Any,
    *,
    image_service: Any = None,
) -> Optional[CharacterSheet]:
    """Lock sheet once after ch1 agency pick. Idempotent; fails soft to None."""
    existing = get_character_sheet(state)
    if existing is not None:
        return existing

    agency = {}
    metadata = getattr(state, "metadata", None)
    if isinstance(metadata, dict):
        agency = metadata.get("agency") or {}
    if not isinstance(agency, dict):
        agency = {}

    agency_name = str(agency.get("name") or "").strip() or "Unknown Agency"
    agency_category = str(agency.get("category") or "").strip()
    agency_visual_details = str(agency.get("visual_details") or "").strip()
    protagonist_description = (
        str(getattr(state, "protagonist_description", "") or "").strip()
        or "A young adventurer"
    )
    sensory = getattr(state, "selected_sensory_details", None) or {}
    story_visual = ""
    if isinstance(sensory, dict):
        story_visual = str(sensory.get("visuals") or "").strip()

    visual_summary = "; ".join(
        part
        for part in (
            protagonist_description,
            f"agency={agency_name}",
            agency_visual_details,
        )
        if part
    )

    prompt = build_character_sheet_prompt(
        protagonist_description=protagonist_description,
        agency_name=agency_name,
        agency_category=agency_category,
        agency_visual_details=agency_visual_details,
        story_visual_sensory_detail=story_visual,
    )

    if image_service is None:
        from app.services.websocket.image_generator import get_image_service

        image_service = get_image_service()

    llm_context = {
        "adventure_id": (
            metadata.get("adventure_id") if isinstance(metadata, dict) else None
        ),
        "chapter_number": 1,
        "chapter_type": "story",
        "character_sheet": True,
    }

    try:
        jpeg_b64 = await image_service.generate_image_async(
            prompt,
            context=llm_context,
        )
    except Exception as exc:
        logger.error("character_sheet generation failed: %s", exc)
        return None

    if not jpeg_b64:
        logger.warning("character_sheet generation returned no image; text-only fallback")
        return None

    try:
        sheet = CharacterSheet(
            jpeg_bytes=base64.b64decode(jpeg_b64),
            mime=CHARACTER_SHEET_MIME,
            locked_chapter=1,
            agency_name=agency_name,
            visual_summary=visual_summary,
        )
    except Exception as exc:
        logger.error("character_sheet decode failed: %s", exc)
        return None

    if not isinstance(getattr(state, "metadata", None), dict):
        state.metadata = {}
    state.metadata["character_sheet"] = sheet.to_metadata_dict()
    logger.info(
        "character_sheet_locked",
        extra={
            "agency_name": agency_name,
            "jpeg_bytes": len(sheet.jpeg_bytes),
            "locked_chapter": 1,
            "adventure_id": llm_context.get("adventure_id"),
        },
    )
    return sheet
