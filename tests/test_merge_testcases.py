import tempfile
from pathlib import Path
import unittest

from scripts.merge_testcases import collect_testcases


class MergeTestcasesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.source = Path(directory.name)

    def test_preserves_whitespace_unicode_and_empty_answer(self):
        (self.source / "case.input.txt").write_bytes("  中文\t24\r\n\n".encode("utf-8-sig"))
        (self.source / "case.expected.txt").write_bytes(b"")
        self.assertEqual(collect_testcases(self.source), [
            {"id": "case", "input": "  中文\t24\r\n\n", "expected": ""},
        ])

    def test_empty_directory_is_error(self):
        with self.assertRaises(ValueError):
            collect_testcases(self.source)

    def test_unpaired_files_are_errors(self):
        (self.source / "case.input.txt").write_bytes(b"2 3\n")
        with self.assertRaises(ValueError):
            collect_testcases(self.source)
        (self.source / "case.expected.txt").write_bytes(b"5\n")
        (self.source / "orphan.expected.txt").write_bytes(b"0\n")
        with self.assertRaises(ValueError):
            collect_testcases(self.source)

    def test_subdirectories_keep_distinct_sorted_ids(self):
        for name in ("b", "a"):
            folder = self.source / name
            folder.mkdir()
            (folder / "01.input.txt").write_bytes(b"2 3")
            (folder / "01.expected.txt").write_bytes(b"5")
        self.assertEqual([case["id"] for case in collect_testcases(self.source)],
                         ["a/01", "b/01"])


if __name__ == "__main__":
    unittest.main()
