"""Behavioral and structural performance guards for story YAML parse reuse."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from app.data import story_loader
from app.data.story_loader import StoryLoader


@pytest.fixture(autouse=True)
def clear_parse_cache():
    story_loader._parse_story_yaml.cache_clear()
    yield
    story_loader._parse_story_yaml.cache_clear()


def test_full_library_matches_fresh_safe_load_in_enumeration_order():
    directory = "app/data/stories"
    expected = {}
    for filename in os.listdir(directory):
        if filename.endswith((".yaml", ".yml")):
            with open(os.path.join(directory, filename), encoding="utf-8") as source:
                expected[Path(filename).stem] = yaml.safe_load(source)
    assert StoryLoader().load_all_stories() == {"story_categories": expected}
    assert list(StoryLoader().load_all_stories()["story_categories"]) == list(expected)


def test_fresh_loaders_reuse_parsing_without_sharing_mutable_data(tmp_path):
    (tmp_path / "world.yaml").write_text("name: Forest\nitems: &items [compass]\nalias: *items\n")
    with patch.object(story_loader.yaml, "safe_load", wraps=yaml.safe_load) as parse:
        first = StoryLoader(str(tmp_path)).load_all_stories()["story_categories"]["world"]
        first["items"].append("map")
        assert first["items"] is first["alias"]
        for _ in range(100):
            other = StoryLoader(str(tmp_path)).load_all_stories()["story_categories"]["world"]
            assert other == {"name": "Forest", "items": ["compass"], "alias": ["compass"]}
            assert other["items"] is other["alias"]
            assert other["items"] is not first["items"]
        assert parse.call_count == 1


def test_instance_cache_and_refresh_preserve_existing_contract(tmp_path):
    path = tmp_path / "world.yaml"
    path.write_text("name: Forest\n")
    loader = StoryLoader(str(tmp_path))
    first = loader.load_all_stories()
    first["story_categories"]["world"]["name"] = "Changed by caller"
    assert loader.load_all_stories() is first
    refreshed = loader.load_all_stories(refresh=True)
    assert refreshed is not first
    assert refreshed["story_categories"]["world"]["name"] == "Forest"
    path.write_text("name: Castle\n")
    assert loader.load_all_stories() is refreshed
    assert loader.load_all_stories(refresh=True)["story_categories"]["world"]["name"] == "Castle"


def test_same_size_edit_with_restored_mtime_invalidates_by_contents(tmp_path):
    path = tmp_path / "world.yaml"
    path.write_text("name: Forest\n")
    assert StoryLoader(str(tmp_path)).get_display_name("world") == "Forest"
    before = path.stat()
    path.write_text("name: Castle\n")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert path.stat().st_size == before.st_size
    assert StoryLoader(str(tmp_path)).get_display_name("world") == "Castle"


def test_add_remove_and_enumeration_order_are_observed(tmp_path, monkeypatch):
    first = tmp_path / "first.yaml"
    first.write_text("name: First\n")
    assert StoryLoader(str(tmp_path)).get_available_categories() == ["first"]
    second = tmp_path / "second.yml"
    second.write_text("name: Second\n")
    monkeypatch.setattr(story_loader.os, "listdir", lambda path: ["second.yml", "first.yaml"])
    assert StoryLoader(str(tmp_path)).get_available_categories() == ["second", "first"]
    first.unlink()
    monkeypatch.setattr(story_loader.os, "listdir", lambda path: ["second.yml"])
    assert StoryLoader(str(tmp_path)).get_available_categories() == ["second"]


def test_invalid_yaml_retains_stream_error_details_and_is_not_cached(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("name: [unfinished\n")
    with open(path, encoding="utf-8") as source:
        with pytest.raises(yaml.YAMLError) as original:
            yaml.safe_load(source)
    with patch.object(story_loader.yaml, "safe_load", wraps=yaml.safe_load) as parse:
        for _ in range(2):
            with pytest.raises(ValueError) as actual:
                StoryLoader(str(tmp_path)).load_all_stories()
            assert str(actual.value) == f"Failed to load story data: {original.value}"
        assert parse.call_count == 2


def test_warm_cache_still_observes_open_errors(tmp_path, monkeypatch):
    path = tmp_path / "world.yaml"
    path.write_text("name: Forest\n")
    StoryLoader(str(tmp_path)).load_all_stories()

    def deny_open(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("builtins.open", deny_open)
    with pytest.raises(ValueError, match="Failed to load story data: denied"):
        StoryLoader(str(tmp_path)).load_all_stories()


@pytest.mark.parametrize("prefix", [b"name: Forest\n", b"name: @invalid\n"])
def test_late_invalid_utf8_preserves_original_error_precedence_and_offset(tmp_path, prefix):
    path = tmp_path / "broken.yaml"
    path.write_bytes(prefix + b"# padding\n" * 3000 + b"\xff")
    with open(path, encoding="utf-8") as source:
        with pytest.raises((UnicodeError, yaml.YAMLError)) as original:
            yaml.safe_load(source)
    with pytest.raises(ValueError) as actual:
        StoryLoader(str(tmp_path)).load_all_stories()
    assert str(actual.value) == f"Failed to load story data: {original.value}"


def test_safe_yaml_types_and_recursive_aliases_survive_copy(tmp_path):
    (tmp_path / "world.yaml").write_text(
        "day: 2026-10-23\nflags: !!set {a: null, b: null}\n"
        "binary: !!binary YWJj\nloop: &loop [*loop]\n"
    )
    first = StoryLoader(str(tmp_path)).load_all_stories()["story_categories"]["world"]
    second = StoryLoader(str(tmp_path)).load_all_stories()["story_categories"]["world"]
    assert first["day"] == second["day"]
    assert second["flags"] == {"a", "b"}
    assert second["binary"] == b"abc"
    assert first["loop"][0] is first["loop"]
    assert second["loop"][0] is second["loop"]
    assert first["loop"] is not second["loop"]


def test_parse_cache_is_bounded_across_file_versions(tmp_path):
    path = tmp_path / "world.yaml"
    for number in range(40):
        path.write_text(f"number: {number}\n")
        actual = StoryLoader(str(tmp_path)).load_all_stories()
        assert actual["story_categories"]["world"]["number"] == number
    assert story_loader._parse_story_yaml.cache_info().currsize == 32


def test_deep_alias_graph_that_safe_load_accepts_still_loads(tmp_path):
    # Duplicate keys leave only the deepest chain reachable from the root.
    # Source syntax stays shallow, so safe_load does not recurse down the chain.
    depth = sys.getrecursionlimit() + 10
    path = tmp_path / "world.yaml"
    path.write_text("value: &n0 []\n" + "".join(
        f"value: &n{number} [*n{number - 1}]\n" for number in range(1, depth + 1)))
    with open(path, encoding="utf-8") as source:
        original = yaml.safe_load(source)
    for _ in range(2):
        actual = StoryLoader(str(tmp_path)).load_all_stories()["story_categories"]["world"]
        value = actual["value"]
        for _ in range(depth):
            value = value[0]
        assert value == []
        assert actual["value"] is not original["value"]
