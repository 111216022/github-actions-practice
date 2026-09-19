import sys
import unittest

from validator_core import normalize_output, validate


class ValidatorTests(unittest.TestCase):
    def run_python(self, source, input_text="", expected="", timeout=5):
        return validate([sys.executable, "-c", source], input_text, expected, timeout)

    def test_sends_input_and_captures_stdout_and_stderr(self):
        result = self.run_python(
            "import sys; a, b = map(int, sys.stdin.read().split()); "
            "print(a + b); print('diagnostic', file=sys.stderr)",
            "2 3\n", "5",
        )
        self.assertTrue(result.passed)
        self.assertEqual(normalize_output(result.stdout), "5")
        self.assertIn("diagnostic", result.stderr)

    def test_wrong_output_identifies_line(self):
        result = self.run_python("print('first'); print('wrong')", expected="first\nright")
        self.assertFalse(result.passed)
        self.assertIn("第 2 行", result.message)

    def test_whitespace_and_extra_blank_lines_matter(self):
        self.assertNotEqual(normalize_output("5 \n"), normalize_output("5"))
        self.assertNotEqual(normalize_output("5\n\n"), normalize_output("5\n"))
        self.assertEqual(normalize_output("a\r\nb\r\n"), normalize_output("a\nb"))

    def test_nonzero_exit_does_not_pass_even_when_output_matches(self):
        result = self.run_python("import sys; print('5'); sys.exit(2)", expected="5")
        self.assertFalse(result.passed)
        self.assertEqual(result.returncode, 2)

    def test_timeout_keeps_partial_output(self):
        result = self.run_python(
            "import time; print('started', flush=True); time.sleep(10)", timeout=1,
        )
        self.assertFalse(result.passed)
        self.assertIsNone(result.returncode)
        self.assertIn("逾時", result.message)
        self.assertIn("started", result.stdout)

    def test_missing_executable(self):
        result = validate(["./nonexistent-validator-test-program.exe"], "", "")
        self.assertFalse(result.passed)
        self.assertIn("無法啟動", result.message)

    def test_empty_output(self):
        self.assertTrue(self.run_python("pass").passed)

    def test_utf8_input_and_output(self):
        result = self.run_python(
            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
            "測試資料\n", "測試資料",
        )
        self.assertTrue(result.passed)

    def test_invalid_utf8_does_not_pass_using_replacement_character(self):
        result = self.run_python(
            "import sys; sys.stdout.buffer.write(bytes([255]))", expected="\ufffd",
        )
        self.assertFalse(result.passed)
        self.assertIn("UTF-8", result.message)

    def test_invalid_timeout(self):
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.run_python("pass", timeout=timeout)


if __name__ == "__main__":
    unittest.main()
