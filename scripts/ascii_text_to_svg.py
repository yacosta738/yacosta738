"""Convert an existing plain-text ASCII portrait into an SVG text fragment."""
import argparse
from pathlib import Path
from xml.sax.saxutils import escape


def ascii_text_to_svg(source: Path, color: str, font_size: float,
                      line_height: float, x: float, y: float) -> str:
    rows = source.read_text(encoding="utf-8").splitlines()
    if not rows:
        raise ValueError(f"ASCII source is empty: {source}")
    tspans = "\n".join(
        f'    <tspan x="{x:g}" dy="{0 if index == 0 else line_height:g}">{escape(row)}</tspan>'
        for index, row in enumerate(rows)
    )
    return (
        f'<text x="{x:g}" y="{y:g}" font-family="monospace" '
        f'font-size="{font_size:g}" fill="{color}" xml:space="preserve">\n'
        f'{tspans}\n  </text>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--color", default="#c9d1d9")
    parser.add_argument("--font-size", type=float, default=5.2)
    parser.add_argument("--line-height", type=float, default=9.2)
    parser.add_argument("--x", type=float, default=18)
    parser.add_argument("--y", type=float, default=22)
    args = parser.parse_args()
    args.out.write_text(
        ascii_text_to_svg(
            args.input, args.color, args.font_size, args.line_height, args.x, args.y
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
