"""Tests for in-place string patches, including fixed-size slots.

Run with: python -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tokipatch import font, patcher  # noqa: E402


class Edit:
    def __init__(self, data: bytes):
        self.original = data
        self.data = bytearray(data)
        self.log = []


def table(*names: str, slot: int = 33) -> bytes:
    """A table of fixed-size records, like DATE.EXN's place names."""
    out = bytearray()
    for name in names:
        out += name.encode("shift_jis").ljust(slot, b"\0")
    return bytes(out)


def patch(offset, original, text, slot=None):
    return patcher.StringPatch("EXEDIR/TEST.EXN", offset, original, text, "test.json", slot=slot)


class SlotTest(unittest.TestCase):
    def test_without_slot_only_padding_is_available(self):
        data = table("海", "神社") + b"\0" * 3
        with self.assertRaisesRegex(ValueError, "only 4 are available"):
            patcher.apply_string(patch(0, "海", "Beach"), Edit(data), font.PairEncoder())

    def test_slot_allows_the_whole_record(self):
        data = table("海", "神社") + b"\0" * 3
        edit = Edit(data)
        patcher.apply_string(patch(0, "海", "the beach", slot=33), edit, font.PairEncoder())
        encoded = font.PairEncoder().encode("the beach")
        self.assertEqual(bytes(edit.data[:33]), encoded.ljust(33, b"\0"))
        self.assertEqual(bytes(edit.data[33:]), data[33:])   # next record untouched

    def test_slot_text_must_leave_room_for_nul(self):
        data = table("海")
        with self.assertRaisesRegex(ValueError, "only 33 are available"):
            patcher.apply_string(patch(0, "海", "x" * 33, slot=33), Edit(data), font.PairEncoder())

    def test_slot_tail_must_be_nul(self):
        data = bytearray(table("海", "神社"))
        data[20] = 0x41   # something stored inside the first record
        with self.assertRaisesRegex(ValueError, "aren't all NUL"):
            patcher.apply_string(patch(0, "海", "Beach", slot=33), Edit(bytes(data)), font.PairEncoder())

    def test_slot_wrong_size_catches_the_next_record(self):
        data = table("海", "神社")
        with self.assertRaisesRegex(ValueError, "aren't all NUL"):
            patcher.apply_string(patch(0, "海", "Beach", slot=40), Edit(data), font.PairEncoder())

    def test_original_still_checked(self):
        data = table("海")
        with self.assertRaisesRegex(ValueError, "expected"):
            patcher.apply_string(patch(0, "山", "Hill", slot=33), Edit(data), font.PairEncoder())


if __name__ == "__main__":
    unittest.main()
