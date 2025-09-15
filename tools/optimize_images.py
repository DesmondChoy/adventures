import sys
from pathlib import Path
from PIL import Image


SIZES = [320, 640, 1024, 1536]
QUALITY = 75  # Reasonable visual quality vs size


def optimize_image(src: Path, out_dir: Path, widths: list[int] | None = None):
    if src.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return
    try:
        img = Image.open(src).convert("RGB")
    except Exception as e:
        print(f"Skip {src}: {e}")
        return

    width, height = img.size
    stem = src.stem

    out_dir.mkdir(parents=True, exist_ok=True)

    targets = sorted(set(widths or SIZES))
    for target_w in targets:
        if target_w >= width:
            # Avoid upscaling; clamp to original width
            target_w = width
        scale = target_w / float(width)
        target_h = int(height * scale)
        variant = img.resize((target_w, target_h), Image.LANCZOS) if target_w != width else img
        out = out_dir / f"{stem}@{target_w}.webp"
        variant.save(out, "WEBP", quality=QUALITY, method=6)
        print(f"Wrote {out} ({target_w}w)")


def main():
    """Optimize only specified images.

    Usage:
      python tools/optimize_images.py [paths...]

    - If no paths are given, defaults to only the hero image to avoid
      generating unnecessary files.
    - Accepts files or directories. Directories are searched recursively for
      png/jpg/jpeg files.
    """
    root = Path("app/static/images")
    out_root = root / "optimized"

    # Default to hero asset only if no args provided, with minimal variant
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        default_targets = {root / "learning-adventure-library.png": [1024]}
        to_process = list(default_targets.items())
    else:
        to_process = []
        for a in args:
            p = a if a.is_absolute() else Path(a)
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                        to_process.append((f, SIZES))
            elif p.is_file():
                to_process.append((p, SIZES))
            else:
                # try resolving relative to root
                rp = root / p
                if rp.exists() and rp.is_file():
                    to_process.append((rp, SIZES))

    count = 0
    for src, widths in to_process:
        if src.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            rel = src.relative_to(root)
            out_dir = out_root / rel.parent
            optimize_image(src, out_dir, widths)
            count += 1
    print(f"Optimized {count} source image(s)")


if __name__ == "__main__":
    sys.exit(main())
