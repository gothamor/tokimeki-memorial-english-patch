"""Measure how much of the game's text is translated, and update the README bar.

Usage:
  python tools/progress.py [--extracted extracted] [--update-readme] [--by-file]

Needs the files extracted by tools/extract.py. "Text" is every NUL-terminated
run of Shift-JIS characters (plus the dialogue control codes) that contains
kana, in every extracted file except `SPEAKTST/` (voice-test copies of the
`SERIFU/` lines; game-internals §6e). A run counts as translated when it lies
inside the original of a translation entry whose English differs from the
Japanese. The unit is Japanese characters, so a long dialogue line weighs more
than a menu label. Graphics (pre-drawn text) and kanji-only labels aren't
counted.

--update-readme rewrites the block between the `progress:start` and
`progress:end` markers in README.md.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A string: Shift-JIS characters and the one-byte dialogue codes
# (game-internals §6e), ending in NUL. Runs that aren't NUL-terminated are
# almost always graphics or code that happens to decode.
STRING = re.compile(rb"(?:[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[ qPGpmFYSOWAMn])+(?=\x00)")
SJIS_CHAR = re.compile(rb"[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]")
KANA = re.compile("[ぁ-んァ-ン]")

SKIP_DIRS = {"CDROM/SPEAKTST"}

# README areas, by directory (the dialogue script folders, game-internals §6).
# Everything else is OTHER_AREA.
AREAS = {
    "CDROM/SERIFU": "Dialogue",
    "CDROM/BUNKA": "Dialogue",
}
OTHER_AREA = "Menus and other text"
AREA_ORDER = ["Dialogue", OTHER_AREA]

BAR_WIDTH = 20


def game_strings(data: bytes):
    """(start, end, japanese chars) for every Japanese string in `data`."""
    for m in STRING.finditer(data):
        chars = SJIS_CHAR.findall(m.group())
        if len(chars) < 2:
            continue
        try:
            text = b"".join(chars).decode("shift_jis")
        except UnicodeDecodeError:
            continue
        if KANA.search(text):
            yield m.start(), m.end(), len(chars)


def translated_ranges(extracted: Path) -> dict[str, list[tuple[int, int]]]:
    """Byte ranges (original string up to its NUL) of every translated entry."""
    ranges: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    cache: dict[str, bytes] = {}

    def add(file: str, entry: dict) -> None:
        text = entry.get("text", "")
        if not text or text == entry.get("original"):
            return
        if file not in cache:
            cache[file] = (extracted / file).read_bytes()
        data = cache[file]
        start = int(entry["offset"], 16)
        ranges[file].append((start, data.index(b"\x00", start)))

    for path in sorted((ROOT / "translation").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for entry in doc.get("strings", []):
            add(entry["file"], entry)
        for block in doc.get("dialogue", []):
            for line in block["lines"]:
                add(block["file"], line)
    return ranges


def area_of(rel: str) -> str:
    return AREAS.get("/".join(rel.split("/")[:2]), OTHER_AREA)


def measure(extracted: Path):
    done = translated_ranges(extracted)
    total: collections.Counter = collections.Counter()
    translated: collections.Counter = collections.Counter()
    per_file = []
    for path in sorted(extracted.rglob("*")):
        rel = path.relative_to(extracted).as_posix()
        if not path.is_file() or rel == "files.tsv" or rel.startswith("dumps/"):
            continue
        if "/".join(rel.split("/")[:2]) in SKIP_DIRS:
            continue
        spans = done.get(rel, [])
        file_total = file_done = 0
        for start, end, n in game_strings(path.read_bytes()):
            file_total += n
            if any(s <= start and end <= e for s, e in spans):
                file_done += n
        if file_total:
            area = area_of(rel)
            total[area] += file_total
            translated[area] += file_done
            per_file.append((rel, file_done, file_total))
    return total, translated, per_file


def bar(fraction: float) -> str:
    filled = round(fraction * BAR_WIDTH)
    if fraction > 0 and filled == 0:
        filled = 1
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def pct(done: int, total: int) -> str:
    value = 100 * done / total if total else 0.0
    return f"{value:.1f}%" if value < 10 else f"{value:.0f}%"


def readme_block(total, translated) -> str:
    all_total, all_done = sum(total.values()), sum(translated.values())
    lines = [
        f"**Translated: {pct(all_done, all_total)}**",
        "",
        "```text",
        f"{'Whole game':<22} {bar(all_done / all_total)} {pct(all_done, all_total):>6}",
    ]
    for area in AREA_ORDER:
        if total[area]:
            frac = translated[area] / total[area]
            lines.append(f"{area:<22} {bar(frac)} {pct(translated[area], total[area]):>6}")
    lines += [
        "```",
        "",
        f"<sub>{all_done:,} of {all_total:,} Japanese characters of in-game text, "
        "measured by <code>tools/progress.py</code>. Pre-drawn graphics text isn't "
        "counted.</sub>",
    ]
    return "\n".join(lines)


def update_readme(block: str) -> None:
    readme = ROOT / "README.md"
    text = readme.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"  # keep the checkout's line endings
    pattern = re.compile(r"(<!-- progress:start -->\r?\n).*?(<!-- progress:end -->)", re.S)
    if not pattern.search(text):
        sys.exit("README.md has no <!-- progress:start --> / <!-- progress:end --> markers")
    body = (block + "\n").replace("\n", newline)
    readme.write_bytes(pattern.sub(lambda m: m.group(1) + body + m.group(2), text).encode("utf-8"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--extracted", type=Path, default=ROOT / "extracted")
    ap.add_argument("--update-readme", action="store_true")
    ap.add_argument("--by-file", action="store_true", help="also list every file with text")
    args = ap.parse_args()

    total, translated, per_file = measure(args.extracted)
    if args.by_file:
        for rel, done, n in per_file:
            print(f"{pct(done, n):>6} {done:7,}/{n:<7,} {rel}")
        print()
    block = readme_block(total, translated)
    print(block)
    if args.update_readme:
        update_readme(block)
        print("\nREADME.md updated.")


if __name__ == "__main__":
    main()
