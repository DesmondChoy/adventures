"""Content-hashed static asset URLs and ES module import map generation."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

STATIC_ROOT = (Path(__file__).resolve().parents[1] / "static").resolve()


@lru_cache(maxsize=256)
def _hash_file_for_stat(path_str: str, mtime_ns: int, size: int) -> str:
    del mtime_ns, size
    return hashlib.sha256(Path(path_str).read_bytes()).hexdigest()[:10]


def static_url(asset_path: str) -> str:
    """Return `/static/<asset_path>?v=<sha256[:10]>` from the real file on disk."""
    normalized = asset_path.lstrip("/").removeprefix("static/")

    resolved = (STATIC_ROOT / normalized).resolve()
    if not resolved.is_relative_to(STATIC_ROOT) or not resolved.is_file():
        raise FileNotFoundError(f"Static asset not found: {asset_path}")

    stat = resolved.stat()
    digest = _hash_file_for_stat(str(resolved), stat.st_mtime_ns, stat.st_size)
    return f"/static/{normalized}?v={digest}"


def build_js_importmap() -> dict[str, dict[str, str]]:
    """Map every served JS module path to its single content-hashed URL."""
    js_dir = STATIC_ROOT / "js"
    imports: dict[str, str] = {}
    for js_file in sorted(js_dir.glob("*.js")):
        rel = js_file.relative_to(STATIC_ROOT).as_posix()
        imports[f"/static/{rel}"] = static_url(rel)
    return {"imports": imports}


def js_importmap_json() -> str:
    """Serialize the JS import map safely for embedding in a `<script>` tag."""
    return json.dumps(build_js_importmap(), separators=(",", ":")).replace(
        "</", "<\\/"
    )
