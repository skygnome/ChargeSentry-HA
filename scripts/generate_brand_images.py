#!/usr/bin/env python3
"""Generate the integration's brand images from the master artwork.

Home Assistant 2026.3 and later serve brand images straight out of
``custom_components/<domain>/brand/``, so that directory is what actually
reaches the UI. Its files have to satisfy the same specification as the
home-assistant/brands repository, which caps the logo well below the size of
the master artwork:

- ``icon.png``   256x256, ``icon@2x.png`` 512x512, both exactly square.
- ``logo.png``   shortest side 128-256; ``logo@2x.png`` shortest side 256-512.
- PNG, transparent, trimmed to the subject.

So ``brand/logo.png`` in the repository root stays the full-resolution master
and is not shipped, and this script derives the four files that are.

Usage: python3 scripts/generate_brand_images.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "brand" / "logo.png"
OUT = ROOT / "custom_components" / "chargesentry_rest" / "brand"

# Row at which the wordmark starts in the master, i.e. the bottom of the badge.
# The icon is the badge alone; re-check this if the artwork is ever replaced.
BADGE_BOTTOM = 535

ICON_SIZE = 256
LOGO_SHORTEST_SIDE = 256


def trim(image: Image.Image) -> Image.Image:
    """Crop away the transparent border."""
    bbox = image.getbbox()
    if bbox is None:
        raise SystemExit("the master artwork is fully transparent")
    return image.crop(bbox)


def save(image: Image.Image, name: str) -> None:
    """Write a PNG, optimised and interlaced as the specification prefers."""
    image.save(OUT / name, "PNG", optimize=True, interlace=1)
    print(f"{name}: {image.width}x{image.height}")


def scale_to_shortest_side(image: Image.Image, shortest: int) -> Image.Image:
    """Scale so the shorter edge lands exactly on ``shortest``."""
    factor = shortest / min(image.size)
    size = (round(image.width * factor), round(image.height * factor))
    return image.resize(size, Image.LANCZOS)


def square(image: Image.Image, size: int) -> Image.Image:
    """Centre the image on a transparent square canvas and scale it to size."""
    side = max(image.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return canvas.resize((size, size), Image.LANCZOS)


def main() -> None:
    """Generate every shipped brand image from the master."""
    OUT.mkdir(parents=True, exist_ok=True)
    master = Image.open(MASTER).convert("RGBA")

    logo = trim(master)
    save(scale_to_shortest_side(logo, LOGO_SHORTEST_SIDE), "logo.png")
    save(scale_to_shortest_side(logo, LOGO_SHORTEST_SIDE * 2), "logo@2x.png")

    badge = trim(master.crop((0, 0, master.width, BADGE_BOTTOM)))
    save(square(badge, ICON_SIZE), "icon.png")
    save(square(badge, ICON_SIZE * 2), "icon@2x.png")


if __name__ == "__main__":
    main()
