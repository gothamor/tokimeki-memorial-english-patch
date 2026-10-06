"""Applies translation files (JSON) to the data track.

A translation file can contain:

  "strings": in-place text replacements
      {"file", "offset", "original", "text", "encoding"?}
      `encoding` is "pairs" (default: English letter pairs, 1 byte per letter,
      drawn with redrawn font glyphs; see font.py) or "fullwidth" (each letter
      as a full-width Shift-JIS character, 2 bytes and 12 px per letter).

  "images":  pixels copied from an 8-bit indexed PNG into an 8bpp bitmap
      {"file", "png", "pixels", "stride", "x", "y", "rects", "original_crc32"}
      `pixels` is the file offset of the bitmap, `stride` its width in bytes,
      (x, y) where the PNG's top-left lands, and `rects` the [x, y, w, h] areas
      of the PNG to copy (everything else is left alone).

  "bytes":   raw byte replacements, for code/data hacks
      {"file", "offset", "original", "replacement", "comment"}
      `original` and `replacement` are hex strings of equal length; the
      patcher refuses to run unless the file holds exactly `original`.

  "dialogue": blocks of script strings that are repacked, not fitted in place
      {"file", "base", "max_cells"?, "lines": [{"offset", "original", "text"}]}
      `base` is the RAM address the file is loaded to (its string pointers
      are absolute). The space of every translated string is pooled, the
      English is packed into it, and every pointer is updated (script.py).
      The English must keep the original's line breaks, choices and name
      codes (scene scripts time events to display lines). A line with an
      empty "text" is left untouched.
"""

from __future__ import annotations

import json
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from . import font, png, script, text
from .cd import Track
from .iso9660 import Entry, list_files

EXPECTED_BOOT = b"cdrom:SLPM_86.053"
CHECKSUM_MARKER = b"\x12\x10"
ENCODINGS = ("pairs", "fullwidth")


@dataclass
class StringPatch:
    file: str
    offset: int
    original: str
    text: str
    source: str  # translation file it came from, for error messages
    encoding: str = "pairs"


@dataclass
class ImagePatch:
    file: str
    png: Path
    pixels: int
    stride: int
    x: int
    y: int
    rects: List[List[int]]
    original_crc32: int
    source: str


@dataclass
class BytePatch:
    file: str
    offset: int
    original: bytes
    replacement: bytes
    comment: str
    source: str


@dataclass
class DialogueLine:
    offset: int
    original: str
    text: str


@dataclass
class DialogueBlock:
    file: str
    base: int
    lines: List[DialogueLine]
    source: str
    max_cells: int = script.MAX_CELLS


@dataclass
class FileEdit:
    entry: Entry
    original: bytes
    data: bytearray
    log: List[str] = field(default_factory=list)


def load_translations(paths: List[Path]):
    """Return (strings, images, byte_patches, dialogue) from the given JSON files."""
    strings, images, byte_patches, dialogue = [], [], [], []
    for path in paths:
        path = Path(path)
        doc = json.loads(path.read_text(encoding="utf-8"))
        for item in doc.get("strings", []):
            encoding = item.get("encoding", "pairs")
            if encoding not in ENCODINGS:
                raise ValueError(f"{path.name}: unknown encoding {encoding!r} (use {ENCODINGS})")
            strings.append(StringPatch(
                file=item["file"].upper().lstrip("/"),
                offset=int(item["offset"], 0),
                original=item["original"],
                text=item["text"],
                source=path.name,
                encoding=encoding,
            ))
        for item in doc.get("images", []):
            images.append(ImagePatch(
                file=item["file"].upper().lstrip("/"),
                png=path.parent / item["png"],
                pixels=int(item["pixels"], 0),
                stride=item["stride"],
                x=item["x"],
                y=item["y"],
                rects=item["rects"],
                original_crc32=int(item["original_crc32"], 0),
                source=path.name,
            ))
        for item in doc.get("bytes", []):
            original = bytes.fromhex(item["original"])
            replacement = bytes.fromhex(item["replacement"])
            if len(original) != len(replacement):
                raise ValueError(f"{path.name}: bytes patch at {item['offset']} changes length")
            byte_patches.append(BytePatch(
                file=item["file"].upper().lstrip("/"),
                offset=int(item["offset"], 0),
                original=original,
                replacement=replacement,
                comment=item.get("comment", ""),
                source=path.name,
            ))
        for item in doc.get("dialogue", []):
            dialogue.append(DialogueBlock(
                file=item["file"].upper().lstrip("/"),
                base=int(item["base"], 0),
                lines=[DialogueLine(int(line["offset"], 0), line["original"], line["text"])
                       for line in item["lines"]],
                source=path.name,
                max_cells=item.get("max_cells", script.MAX_CELLS),
            ))
    return strings, images, byte_patches, dialogue


def check_disc(files: Dict[str, Entry], track: Track) -> None:
    cnf = files.get("SYSTEM.CNF")
    if cnf is None or EXPECTED_BOOT not in track.read_file(cnf.lba, cnf.size):
        raise ValueError("This doesn't look like Tokimeki Memorial: Forever with You "
                         "(PlayStation the Best, SLPM-86053).")


def has_checksum(data: bytes) -> bool:
    """Most data files end with a big-endian 16-bit byte sum + 12 10.

    The game verifies it after every load and silently retries forever on a
    mismatch (which shows up as a hang on a white or black screen).
    """
    return (len(data) >= 4 and data[-2:] == CHECKSUM_MARKER
            and sum(data[:-4]) & 0xFFFF == int.from_bytes(data[-4:-2], "big"))


def fix_checksum(data: bytearray) -> None:
    data[-4:-2] = (sum(data[:-4]) & 0xFFFF).to_bytes(2, "big")


def apply_string(patch: StringPatch, edit: FileEdit, pairs: font.PairEncoder) -> None:
    where = f"{patch.source}: {patch.file} @ {patch.offset:#x}"
    data = edit.data
    original = patch.original.encode("shift_jis")
    end = patch.offset + len(original)
    if bytes(data[patch.offset:end]) != original or data[end:end + 1] != b"\0":
        found = bytes(data[patch.offset:end]).decode("shift_jis", "replace")
        raise ValueError(f"{where}: expected {patch.original!r}, found {found!r}")

    # The string owns its terminator plus any zero padding up to the next
    # 4-byte boundary (the compiler aligns string literals to 4 bytes).
    capacity = len(original) + 1
    while (patch.offset + capacity) % 4 and data[patch.offset + capacity] == 0:
        capacity += 1

    if patch.encoding == "pairs":
        new = pairs.encode(patch.text)
        max_letters = (capacity - 1) // 2 * 2
    else:
        new = text.encode(patch.text)
        max_letters = (capacity - 1) // 2
    if len(new) + 1 > capacity:
        raise ValueError(f"{where}: {patch.text!r} needs {len(new) + 1} bytes "
                         f"but only {capacity} are available "
                         f"(max {max_letters} characters with {patch.encoding} encoding)")
    data[patch.offset:patch.offset + capacity] = new.ljust(capacity, b"\0")
    edit.log.append(f"{patch.offset:#07x}: {patch.original}  ->  {patch.text}")
    # Japanese is 12 px per 2 bytes and pair/full-width English is 12 px per 2
    # bytes too, so anything longer than the original bytes draws wider.
    if len(new) > len(original):
        edit.log.append(f"    note: {len(new) * 6} px wide vs {len(original) * 6} px originally; "
                        "check it fits on screen")


def apply_dialogue(block: DialogueBlock, edit: FileEdit, pairs: font.PairEncoder) -> None:
    """Repack a block's translated strings into the space they occupied.

    Each string's slot is its bytes + NUL + zero padding to the next 4-byte
    boundary (as for in-place strings). All slots are pooled, the English is
    packed into the pool, and every pointer to a moved string is rewritten.
    Strings referenced from code, or by no pointer we can find, must fit in
    their own slot.
    """
    data, orig = edit.data, edit.original
    jobs, slots = [], {}
    for line in sorted((x for x in block.lines if x.text), key=lambda x: x.offset):
        where = f"{block.source}: {block.file} @ {line.offset:#x}"
        raw = script.encode_original(line.original)
        end = line.offset + len(raw)
        if bytes(data[line.offset:end]) != raw or data[end:end + 1] != b"\0":
            found = script.decode(script.read_string(orig, line.offset))
            raise ValueError(f"{where}: expected {line.original!r}, found {found!r}")
        capacity = len(raw) + 1
        while (line.offset + capacity) % 4 and data[line.offset + capacity] == 0:
            capacity += 1
        new, widths = script.encode_english(line.text, pairs)
        if script.structure(line.text) != script.structure(line.original):
            raise ValueError(f"{where}: the English must have the same line breaks, choices "
                             f"and name codes as the original ({script.structure(line.original)}), "
                             f"has {script.structure(line.text)}: {line.text!r}")
        for n, cells in enumerate(widths):
            if cells > block.max_cells:
                raise ValueError(f"{where}: display line {n + 1} is {cells} cells wide "
                                 f"(max {block.max_cells}; a letter is 1 cell, a name "
                                 f"code counts as its longest name): {line.text!r}")
        pointers = script.find_pointers(orig, block.base, line.offset)
        movable = bool(pointers) and not script.code_references(orig, block.base, line.offset)
        jobs.append((line, new, pointers, movable, where))
        slots[line.offset] = line.offset + capacity

    # Merge adjacent slots into spans and clear them.
    spans: List[List[int]] = []
    for start, stop in sorted(slots.items()):
        if spans and spans[-1][1] == start:
            spans[-1][1] = stop
        else:
            spans.append([start, stop])
    for start, stop in spans:
        for pos, target in script.pointers_into(orig, block.base, start, stop):
            if target not in slots:
                raise ValueError(f"{block.source}: {block.file}: word at {pos:#x} points into "
                                 f"translated text at {target:#x}, not at a string start")
        data[start:stop] = bytes(stop - start)

    free = [list(span) for span in spans]

    def take(start: int, size: int) -> None:
        for span in free:
            if span[0] <= start and start + size <= span[1]:
                free.remove(span)
                free.extend(x for x in ([span[0], start], [start + size, span[1]]) if x[1] > x[0])
                free.sort()
                return
        raise AssertionError(f"{start:#x} isn't free")

    # Strings that can't move keep their own slot; the rest are packed in
    # order, each into the first free gap that holds it.
    placed = {}
    for line, new, pointers, movable, where in jobs:
        if not movable:
            capacity = slots[line.offset] - line.offset
            if len(new) + 1 > capacity:
                reason = "is referenced from code" if pointers else "has no pointer to it"
                raise ValueError(f"{where}: the string {reason}, so it can't move, and the "
                                 f"English needs {len(new) + 1} bytes but only {capacity} "
                                 f"are available")
            take(line.offset, len(new) + 1)
            placed[line.offset] = line.offset
    total = sum(stop - start for start, stop in spans)
    needed = sum(len(job[1]) + 1 for job in jobs)
    for line, new, pointers, movable, where in jobs:
        if movable:
            span = next((x for x in free if x[1] - x[0] >= len(new) + 1), None)
            if span is None:
                raise ValueError(f"{block.source}: {block.file}: the English doesn't fit in the "
                                 f"space of the original strings ({needed} bytes needed, "
                                 f"{total} available)")
            placed[line.offset] = span[0]
            take(span[0], len(new) + 1)

    for line, new, pointers, movable, where in jobs:
        at = placed[line.offset]
        data[at:at + len(new)] = new
        for p in pointers:
            data[p:p + 4] = (block.base + at).to_bytes(4, "little")
        edit.log.append(f"{line.offset:#07x} -> {at:#07x}: {line.text!r}")
    edit.log.append(f"dialogue: {len(jobs)} string(s), {needed} of {total} bytes used")


def _rect_offsets(patch: ImagePatch, rect: List[int]):
    rx, ry, rw, rh = rect
    for row in range(ry, ry + rh):
        yield row, patch.pixels + (patch.y + row) * patch.stride + patch.x + rx


def apply_image(patch: ImagePatch, edit: FileEdit) -> None:
    where = f"{patch.source}: {patch.file} <- {patch.png.name}"
    width, height, pixels = png.read_indexed(patch.png)
    data = edit.data

    crc = 0
    for rect in patch.rects:
        rx, ry, rw, rh = rect
        if rx + rw > width or ry + rh > height or patch.x + rx + rw > patch.stride:
            raise ValueError(f"{where}: rect {rect} is out of bounds")
        for _, off in _rect_offsets(patch, rect):
            crc = zlib.crc32(data[off:off + rw], crc)
    if crc != patch.original_crc32:
        raise ValueError(f"{where}: target pixels don't match the expected original "
                         f"(crc32 {crc:#010x}, expected {patch.original_crc32:#010x})")

    for rect in patch.rects:
        rx, _, rw, _ = rect
        for row, off in _rect_offsets(patch, rect):
            data[off:off + rw] = pixels[row * width + rx:row * width + rx + rw]
    edit.log.append(f"{patch.pixels:#07x}: image {patch.png.name}")


def apply_bytes(patch: BytePatch, edit: FileEdit) -> None:
    where = f"{patch.source}: {patch.file} @ {patch.offset:#x}"
    end = patch.offset + len(patch.original)
    found = bytes(edit.data[patch.offset:end])
    if found != patch.original:
        raise ValueError(f"{where}: expected bytes {patch.original.hex()}, found {found.hex()}")
    edit.data[patch.offset:end] = patch.replacement
    edit.log.append(f"{patch.offset:#07x}: bytes {patch.original.hex()} -> {patch.replacement.hex()}"
                    + (f"  ({patch.comment})" if patch.comment else ""))


def plan(track: Track, strings: List[StringPatch], images: List[ImagePatch],
         free_codes: List[int], byte_patches: List[BytePatch] = (),
         dialogue: List[DialogueBlock] = ()) -> List[FileEdit]:
    """Validate and apply every patch in memory, against the unmodified disc.

    `free_codes` are the font glyphs available for English letter pairs
    (translation/font/free_glyphs.txt).
    """
    files = list_files(track)
    check_disc(files, track)

    edits: Dict[str, FileEdit] = {}

    def edit_for(path: str, source: str) -> FileEdit:
        if path not in edits:
            entry = files.get(path)
            if entry is None or entry.is_dir:
                raise ValueError(f"{source}: no file {path!r} on the disc")
            data = track.read_file(entry.lba, entry.size)
            edits[path] = FileEdit(entry, data, bytearray(data))
        return edits[path]

    pairs = font.PairEncoder(free_codes)
    for s in strings:
        apply_string(s, edit_for(s.file, s.source), pairs)
    for i in images:
        apply_image(i, edit_for(i.file, i.source))
    for b in byte_patches:
        apply_bytes(b, edit_for(b.file, b.source))
    for d in dialogue:
        apply_dialogue(d, edit_for(d.file, d.source), pairs)

    if pairs.assigned:
        exe = edit_for(font.EXE, "font")
        exe.log.extend(pairs.write_glyphs(exe.data))

    for path, edit in edits.items():
        if has_checksum(edit.original):
            if edit.data[-4:] != edit.original[-4:]:
                raise ValueError(f"{path}: a patch overwrote the file's checksum trailer")
            fix_checksum(edit.data)
            edit.log.append("checksum updated")
    return list(edits.values())


def apply(track: Track, edits: List[FileEdit], log=print) -> None:
    for edit in edits:
        sectors = track.write_file(edit.entry.lba, edit.original, bytes(edit.data))
        log(f"  {edit.entry.path} ({sectors} sector(s))")
        for line in edit.log:
            log(f"    {line}")
