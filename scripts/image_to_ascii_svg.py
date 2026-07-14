"""
One-time tool: converts a personal photo into a monochrome ASCII-art SVG fragment.

Usage:
    python3 image_to_ascii_svg.py \
        --image /tmp/opencode/yuniel-photo.png \
        --out assets/ascii_art_fragment.svg \
        --cols 38 --color "#64FFDA" --font-size 9 --line-height 10 --x 10 --y 20

This is NOT part of the daily metrics pipeline (profile_card.py). It runs once to
produce a fixed <tspan> block that gets pasted into the SVG templates by hand.
"""
import argparse
from xml.sax.saxutils import escape

from PIL import Image

# Density ramp from "empty" (dark background) to "full ink" (bright highlight).
RAMP = " .:-=+*#%@"

# Terminal/monospace characters are taller than they are wide (~0.55 aspect ratio),
# so we compress row count relative to column count to avoid a stretched portrait.
CHAR_ASPECT_RATIO = 0.55


def luminance_to_char(luminance: int, ramp: str) -> str:
    """Maps a 0-255 luminance value to a character in the density ramp."""
    index = round(luminance / 255 * (len(ramp) - 1))
    return ramp[index]


def image_to_ascii_rows(image_path: str, cols: int) -> list[str]:
    """Loads an image and returns a list of ASCII-art rows (strings)."""
    image = Image.open(image_path).convert("L")
    width, height = image.size
    rows = round((height / width) * cols * CHAR_ASPECT_RATIO)
    resized = image.resize((cols, rows))
    pixels = list(resized.getdata())

    ascii_rows = []
    for row_index in range(rows):
        row_pixels = pixels[row_index * cols : (row_index + 1) * cols]
        ascii_rows.append("".join(luminance_to_char(p, RAMP) for p in row_pixels))
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
    parser.add_argument("--x", type=int, default=10)
    parser.add_argument("--y", type=int, default=20)
    args = parser.parse_args()

    rows = image_to_ascii_rows(args.image, args.cols)
    fragment = rows_to_svg_fragment(
        rows, args.color, args.font_size, args.line_height, args.x, args.y
    )
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(fragment)
    print(f"Wrote {len(rows)} rows x {args.cols} cols to {args.out}")


if __name__ == "__main__":
    main()
