import sys
import types
from pathlib import Path
import importlib.util

import pytest

from app.models.story import ChapterType


def _ensure_pandas_stub():
    if "pandas" in sys.modules:
        return

    pandas_stub = types.ModuleType("pandas")

    class _DataFrame:  # Minimal placeholder for type hints
        ...

    def _not_implemented(*args, **kwargs):
        raise RuntimeError("pandas stub invoked during tests")

    pandas_stub.DataFrame = _DataFrame
    pandas_stub.read_csv = _not_implemented
    pandas_stub.concat = _not_implemented
    pandas_stub.Series = _DataFrame

    sys.modules["pandas"] = pandas_stub


def _install_init_data_stub():
    if "app.init_data" in sys.modules:
        return

    import app  # Ensure base package is loaded

    init_data_stub = types.ModuleType("app.init_data")

    def sample_question(topic, exclude_questions=None, difficulty="Reasonably Challenging"):
        return {
            "question": "Stub question?",
            "answers": [
                {"text": "Answer 1", "is_correct": True},
                {"text": "Answer 2", "is_correct": False},
                {"text": "Answer 3", "is_correct": False},
            ],
            "explanation": "Stub explanation",
            "topic": topic,
            "subtopic": "Stub",
            "difficulty": difficulty,
        }

    init_data_stub.sample_question = sample_question  # type: ignore[attr-defined]
    sys.modules["app.init_data"] = init_data_stub
    setattr(app, "init_data", init_data_stub)


_ensure_pandas_stub()
_install_init_data_stub()


def _load_content_generator_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "websocket"
        / "content_generator.py"
    )
    spec = importlib.util.spec_from_file_location(
        "content_generator_module", module_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


content_generator = _load_content_generator_module()


@pytest.mark.asyncio
async def test_extract_regular_choices_errors_when_missing_choices():
    story_body = "Nisha studies the glowing map carefully."
    story_content = (
        f"{story_body}\n\n"
        "<CHOICES>\n"
        "Choice A: Follow the shimmering trail toward the lagoon.\n"
        "Choice B: Double back to see whether Faelan needs help.\n"
        "</CHOICES>\n"
    )

    with pytest.raises(ValueError):
        await content_generator.extract_regular_choices(
            ChapterType.STORY,
            story_content,
            current_chapter_number=3,
        )

