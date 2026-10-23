"""Generate responsive WebP variants for the six public landing-page images.

Run from any directory with the repository's Python environment:
    .venv/bin/python tools/optimize_landing_images.py

Originals stay untouched. Illustration variants favor transfer size; screenshot
variants retain a higher quality setting for UI text. Output names are stable so
landing markup can use width descriptors in srcset.
"""

from pathlib import Path

from PIL import Image, ImageOps


IMAGE_ROOT = Path(__file__).resolve().parents[1] / "app" / "static" / "images"
OUTPUT_DIR = IMAGE_ROOT / "landing"
WORLD_IMAGES = (
    "stories/clockwork_sky_city.jpg",
    "stories/underwater_kingdom_of_sunken_ships.jpg",
    "stories/living_inside_your_own_drawing.jpg",
)
WALKTHROUGH_IMAGES = (
    "adventure-selection.png",
    "monster-encounter.png",
    "red-green-portal.png",
)


def generate_variants(relative_source: str, *, screenshot: bool) -> None:
    source = IMAGE_ROOT / relative_source
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")

    width, height = image.size
    requested_widths = (480, 720, width) if screenshot else (480, 848)
    target_widths = sorted({min(target, width) for target in requested_widths})
    quality = 90 if screenshot else 80
    print(f"Source {relative_source}: {width}x{height}, {source.stat().st_size} bytes")

    for target_width in target_widths:
        target_height = round(height * target_width / width)
        variant = (
            image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            if target_width != width
            else image
        )
        destination = OUTPUT_DIR / f"{source.stem}-{target_width}.webp"
        variant.save(destination, "WEBP", quality=quality, method=6)
        print(
            f"  {destination.name}: {target_width}x{target_height}, "
            f"{destination.stat().st_size} bytes, quality={quality}"
        )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for relative_source in WORLD_IMAGES:
        generate_variants(relative_source, screenshot=False)
    for relative_source in WALKTHROUGH_IMAGES:
        generate_variants(relative_source, screenshot=True)


if __name__ == "__main__":
    main()
