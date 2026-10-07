"""Regression tests for finding dialogue strings in script files.

The fixtures are synthetic: they reproduce the layouts seen in the game's
SERIFU files (strings after a NUL, strings directly after a pointer table,
pointers into the middle of a string) without containing any game data.

Run with: python -m unittest discover tests
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import dump_dialogue  # noqa: E402
from tokipatch import font, patcher, script  # noqa: E402

BASE = 0x80198000


class Script:
    """Builds a script file: strings and pointer words, with known offsets."""

    def __init__(self, base: int = BASE):
        self.base = base
        self.data = bytearray()
        self.fixups = []        # (word offset, label, delta)
        self.labels = {}

    def string(self, label: str, raw: bytes, align: bool = True):
        self.labels[label] = len(self.data)
        self.data += raw + b"\0"
        while align and len(self.data) % 4:
            self.data += b"\0"

    def text(self, label: str, text: str):
        self.string(label, script.encode_original(text))

    def pointer(self, label: str, delta: int = 0):
        self.fixups.append((len(self.data), label, delta))
        self.data += bytes(4)

    def word(self, value: int):
        self.data += struct.pack("<I", value)

    def build(self) -> bytes:
        for pos, label, delta in self.fixups:
            struct.pack_into("<I", self.data, pos, self.base + self.labels[label] + delta)
        return bytes(self.data)


def layout(base: int = BASE):
    s = Script(base)
    s.text("after_nul", "あいう")                 # file start, then NUL-padded
    s.pointer("after_nul")                        # a scene's pointer table...
    s.pointer("after_table")
    s.text("after_table", "かきく\nけこ")         # ...directly followed by a string
    s.pointer("after_table", 2)                   # pointer into the middle (unaligned)
    s.text("long", "さしすせそたち")
    s.pointer("long")
    s.pointer("long", 4)                          # aligned pointer into the middle
    s.word(0x80010000)                            # a pointer word outside this file
    s.text("after_foreign", "なにぬ")
    s.pointer("after_foreign")
    s.string("ascii", b"PP")                      # control codes only, no Japanese
    s.pointer("ascii")
    s.string("binary", b"\x01\x02")               # not text at all
    s.pointer("binary")
    s.word(base + 0x100000)                       # points past the end of the file
    return s, s.build()


class StartsString(unittest.TestCase):
    def setUp(self):
        self.s, self.data = layout()
        self.at = self.s.labels

    def test_file_start_and_after_nul(self):
        self.assertTrue(dump_dialogue.starts_string(self.data, BASE, 0))
        self.assertTrue(dump_dialogue.starts_string(self.data, BASE, self.at["long"]))

    def test_after_pointer_table(self):
        off = self.at["after_table"]
        self.assertEqual(self.data[off - 1], 0x80)   # the case the old check rejected
        self.assertTrue(dump_dialogue.starts_string(self.data, BASE, off))

    def test_interior_offsets_rejected(self):
        self.assertFalse(dump_dialogue.starts_string(self.data, BASE, self.at["after_table"] + 2))
        self.assertFalse(dump_dialogue.starts_string(self.data, BASE, self.at["long"] + 4))

    def test_after_word_pointing_outside_the_file_rejected(self):
        self.assertFalse(dump_dialogue.starts_string(self.data, BASE, self.at["after_foreign"]))

    def test_after_pointer_with_wrong_base_rejected(self):
        # With another base the preceding words are no longer in-file pointers.
        self.assertFalse(dump_dialogue.starts_string(self.data, BASE + 0x800, self.at["after_table"]))


class Targets(unittest.TestCase):
    def setUp(self):
        self.s, self.data = layout()
        self.at = self.s.labels
        self.rejected = {}
        self.found = dump_dialogue.targets(self.data, BASE, self.rejected)

    def test_finds_strings_after_nul_and_after_pointer_table(self):
        self.assertEqual(self.found, {
            self.at["after_nul"]: "あいう",
            self.at["after_table"]: "かきく\nけこ",
            self.at["long"]: "さしすせそたち",
        })

    def test_reports_interior_and_unproven_targets(self):
        interior = "not at a string start (interior pointer?)"
        self.assertEqual(self.rejected, {
            self.at["after_table"] + 2: interior,
            self.at["long"] + 4: interior,
            self.at["after_foreign"]: interior,
            self.at["ascii"]: "no Japanese text",
        })

    def test_undecodable_and_out_of_file_targets_ignored(self):
        self.assertNotIn(self.at["binary"], self.found)
        self.assertNotIn(self.at["binary"], self.rejected)

    def test_rejected_is_optional(self):
        self.assertEqual(dump_dialogue.targets(self.data, BASE), self.found)

    def test_guess_base(self):
        self.assertEqual(dump_dialogue.guess_base(self.data), BASE)

    def test_guess_base_off_the_0x800_grid(self):
        # GASSH_FU.BIN loads at 0x801B4400; a 0x800-step search can't find it.
        _, data = layout(0x801B4400)
        self.assertEqual(dump_dialogue.guess_base(data), 0x801B4400)


class Edit:
    def __init__(self, data: bytes):
        self.original = data
        self.data = bytearray(data)
        self.log = []


def block(lines):
    return patcher.DialogueBlock("SERIFU/TEST.BIN", BASE, [
        patcher.DialogueLine(off, original, text) for off, original, text in lines], "test")


class RepackAfterPointerTable(unittest.TestCase):
    """The patcher already handles strings after a table; keep it that way."""

    def setUp(self):
        s = Script()
        s.text("first", "あいう")
        s.pointer("first")
        s.pointer("second")
        s.text("second", "かきく\nけこ")
        s.pointer("second")
        self.s, self.data = s, s.build()

    def word(self, data, pos):
        return struct.unpack_from("<I", data, pos)[0]

    def test_pointers_rewritten_and_table_kept(self):
        first, second = self.s.labels["first"], self.s.labels["second"]
        table = first + 8
        edit = Edit(self.data)
        patcher.apply_dialogue(block([
            (first, "あいう", "Hi"),
            (second, "かきく\nけこ", "Hello th\nyo"),
        ]), edit, font.PairEncoder())
        out = bytes(edit.data)
        self.assertEqual(len(out), len(self.data))
        english = {text: script.encode_english(text, font.PairEncoder())[0]
                   for text in ("Hi", "Hello th\nyo")}
        # Every pointer lands on its string's English.
        self.assertEqual(script.read_string(out, self.word(out, table) - BASE), english["Hi"])
        for pos in (table + 4, second + 12):
            self.assertEqual(script.read_string(out, self.word(out, pos) - BASE),
                             english["Hello th\nyo"])
        # Each string fits back in its own slot, so the table between them is
        # byte-identical: nothing was packed over it.
        self.assertEqual(out[table:table + 8], self.data[table:table + 8])

    def test_closing_bracket_must_match_original(self):
        # The game draws a thought's "）" itself unless the string contains it.
        first = self.s.labels["first"]
        with self.assertRaisesRegex(ValueError, "end with '\\)'"):
            patcher.apply_dialogue(block([(first, "あいう", "Hi.)")]),
                                   Edit(self.data), font.PairEncoder())
        s = Script()
        s.text("thought", "あいう）")
        s.pointer("thought")
        data = s.build()
        with self.assertRaisesRegex(ValueError, "end with '\\)'"):
            patcher.apply_dialogue(block([(0, "あいう）", "Hi.")]), Edit(data), font.PairEncoder())
        patcher.apply_dialogue(block([(0, "あいう）", "Hi.)")]), Edit(data), font.PairEncoder())

    def test_interior_pointer_still_refused(self):
        s = Script()
        s.text("first", "あいう")
        s.pointer("second")
        s.text("second", "かきく\nけこ")
        s.pointer("second", 2)
        data = s.build()
        with self.assertRaisesRegex(ValueError, "not at a string start"):
            patcher.apply_dialogue(block([(s.labels["second"], "かきく\nけこ", "Hello th\nyo")]),
                                   Edit(data), font.PairEncoder())


if __name__ == "__main__":
    unittest.main()
