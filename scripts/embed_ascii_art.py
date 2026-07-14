"""Embed a generated ASCII SVG fragment into the profile card templates."""
import argparse
from pathlib import Path


def embed_fragment(card_path: Path, fragment: str, color: str) -> None:
    card = card_path.read_text(encoding="utf-8")
    comment_start = card.index("  <!-- ASCII art")
    group_start = card.index("  <g", comment_start)
    group_end = card.index("\n  </g>", group_start) + len("\n  </g>")
    indented = "\n".join(f"    {line}" for line in fragment.replace("#c9d1d9", color).splitlines())
    replacement = card[comment_start:group_start] + "  <g>\n" + indented + "\n  </g>"
    card_path.write_text(card[:comment_start] + replacement + card[group_end:], encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragment", type=Path, required=True)
    parser.add_argument("--dark", type=Path, required=True)
    parser.add_argument("--light", type=Path, required=True)
    args = parser.parse_args()

    fragment = args.fragment.read_text(encoding="utf-8")
    embed_fragment(args.dark, fragment, "#c9d1d9")
    embed_fragment(args.light, fragment, "#24292f")


if __name__ == "__main__":
    main()
