"""
One-time tool: converts a personal photo into a monochrome ASCII-art SVG fragment.

Usage:
    python3 image_to_ascii_svg.py \
        --image /tmp/opencode/yuniel-photo.png \
        --out assets/ascii_art_fragment.svg \
        --cols 38 --color "#64FFDA" --font-size 9 --line-height 10 --x 10 --y 20

This is NOT part of the daily metrics pipeline (profile_card.py). It produces a
fixed <tspan> block that scripts/embed_ascii_art.py inserts into both templates.
"""
import argparse
from xml.sax.saxutils import escape

from statistics import median

from PIL import Image, ImageOps

# Density ramp from "empty" (dark background) to "full ink" (bright highlight).
RAMP = " .:-=+*#%@"

# Terminal/monospace characters are taller than they are wide (~0.55 aspect ratio),
# so we compress row count relative to column count to avoid a stretched portrait.
CHAR_ASPECT_RATIO = 0.55


def luminance_to_char(luminance: int, ramp: str) -> str:
    """Maps a 0-255 luminance value to a character in the density ramp."""
    index = round(luminance / 255 * (len(ramp) - 1))
    return ramp[index]


def estimate_background_color(image: Image.Image) -> tuple[int, int, int]:
    """Estimate a portrait backdrop from samples along the upper side edges."""
    width, height = image.size
    samples = []
    step = max(1, height // 100)
    for y in range(int(height * 0.1), int(height * 0.75), step):
        for x in (0, int(width * 0.02), int(width * 0.98), width - 1):
            samples.append(image.getpixel((x, y)))
    return tuple(round(median(pixel[channel] for pixel in samples)) for channel in range(3))


def is_background_pixel(pixel: tuple[int, int, int], background: tuple[int, int, int]) -> bool:
    """Detect the smooth, red-dominant backdrop without erasing skin tones."""
    red, green, blue = pixel
    bg_red, bg_green, bg_blue = background
    distance = sum((value - bg) ** 2 for value, bg in zip(pixel, background)) ** 0.5
    return (
        distance < 75
        and red - green > (bg_red - bg_green) - 20
        and green - blue < (bg_green - bg_blue) + 20
    )


def image_to_ascii_rows(image_path: str, cols: int, *, invert: bool = False,
                        remove_background: bool = False,
                        char_aspect_ratio: float = CHAR_ASPECT_RATIO) -> list[str]:
    """Loads an image and returns a list of ASCII-art rows (strings)."""
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    rows = round((height / width) * cols * char_aspect_ratio)
    resized = image.resize((cols, rows))
    grayscale = ImageOps.autocontrast(resized.convert("L"), cutoff=1)
    background = estimate_background_color(image) if remove_background else None

    ascii_rows = []
    for row_index in range(rows):
        chars = []
        for column_index in range(cols):
            pixel = resized.getpixel((column_index, row_index))
            if background and is_background_pixel(pixel, background):
                chars.append(" ")
                continue
            luminance = grayscale.getpixel((column_index, row_index))
            if invert:
                luminance = 255 - luminance
            chars.append(luminance_to_char(luminance, RAMP))
        ascii_rows.append("".join(chars))
    if remove_background:
        while ascii_rows and not ascii_rows[0].strip():
            ascii_rows.pop(0)
        while ascii_rows and not ascii_rows[-1].strip():
            ascii_rows.pop()
    return ascii_rows


def rows_to_svg_fragment(rows: list[str], color: str, font_size: int,
                          line_height: int, x: int, y: int) -> str:
    """Wraps ASCII rows into a <text> element with one <tspan> per row."""
    tspans = "\n".join(
        f'    <tspan x="{x}" dy="{line_height if i else 0}">{escape(row)}</tspan>'
        for i, row in enumerate(rows)
    )
    return (
        f'<text x="{x}" y="{y}" font-family="monospace" font-size="{font_size}" '
        f'fill="{color}" xml:space="preserve">\n{tspans}\n  </text>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cols", type=int, default=38)
    parser.add_argument("--color", default="#64FFDA")
    parser.add_argument("--font-size", type=int, default=9)
    parser.add_argument("--line-height", type=int, default=10)
    parser.add_argument("--char-aspect-ratio", type=float, default=CHAR_ASPECT_RATIO)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--remove-background", action="store_true")
    parser.add_argument("--x", type=int, default=10)
    parser.add_argument("--y", type=int, default=20)
    args = parser.parse_args()

    rows = image_to_ascii_rows(
        args.image,
        args.cols,
        invert=args.invert,
        remove_background=args.remove_background,
        char_aspect_ratio=args.char_aspect_ratio,
    )
    fragment = rows_to_svg_fragment(
        rows, args.color, args.font_size, args.line_height, args.x, args.y
    )
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(fragment)
    print(f"Wrote {len(rows)} rows x {args.cols} cols to {args.out}")


if __name__ == "__main__":
    main()
