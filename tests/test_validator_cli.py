import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from validator import read_test_file


CLI = Path(__file__).resolve().parents[1] / "validator.py"


class ValidatorCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="validator test ")
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.input = self.folder / "input data.txt"
        self.expected = self.folder / "expected output.txt"
        self.project = self.folder / "project files"
        self.project.mkdir()
        for name in ("validator.py", "validator_core.py", "hello.py"):
            shutil.copyfile(CLI.parent / name, self.project / name)
        self.script = self.project / "hello.py"
        self.input.write_text("2 3\n", encoding="utf-8")
        self.expected.write_text("5\n", encoding="utf-8")

    def run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(self.project / "validator.py"),
             "--input", str(self.input), "--expected", str(self.expected), *extra],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", timeout=15,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            cwd=self.folder,
        )

    def test_pass_reads_files_with_spaces_in_paths(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("實際輸出", result.stdout)
        self.assertIn("\n5\n", result.stdout)

    def test_wrong_answer_prints_actual_and_expected(self):
        self.expected.write_text("6\n", encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("第 1 行", result.stdout)
        self.assertIn("\n5\n", result.stdout)
        self.assertIn("\n6\n", result.stdout)

    def test_missing_input_is_usage_error(self):
        result = self.run_cli("--input", str(self.folder / "missing.txt"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("無法讀取檔案", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_hello_is_usage_error(self):
        self.script.rename(self.project / "renamed.py")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("找不到要驗證的 hello.py", result.stderr)

    def test_uses_hello_next_to_validator_instead_of_current_directory(self):
        (self.folder / "hello.py").write_text("raise RuntimeError('wrong script')", encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_syntax_error_in_hello_is_validation_failure(self):
        self.script.write_text("def broken(\n", encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("SyntaxError", result.stdout)

    def test_invalid_encoding_is_usage_error(self):
        self.expected.write_bytes(b"\xff")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_utf8_bom_files(self):
        self.input.write_text("2 3\n", encoding="utf-8-sig")
        self.expected.write_text("5\n", encoding="utf-8-sig")
        self.assertEqual(self.run_cli().returncode, 0)

    def test_reading_preserves_input_line_endings_and_trailing_whitespace(self):
        self.input.write_bytes(b"2 3\r\n \r\n")
        self.assertEqual(read_test_file(self.input), "2 3\r\n \r\n")

    def test_runtime_failure_reports_stderr(self):
        self.script.write_text(
            "import sys; print('problem', file=sys.stderr); sys.exit(7)", encoding="utf-8",
        )
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("結束代碼 7", result.stdout)
        self.assertIn("problem", result.stdout)

    def test_timeout_returns_failure(self):
        self.script.write_text("import time; time.sleep(10)", encoding="utf-8")
        result = self.run_cli("--timeout", "0.5")
        self.assertEqual(result.returncode, 1)
        self.assertIn("逾時", result.stdout)

    def test_invalid_timeout_is_usage_error(self):
        result = self.run_cli("--timeout", "nan")
        self.assertEqual(result.returncode, 2)

    def test_hello_reads_utf8_input_and_prints_utf8_output(self):
        self.script.write_text("import sys; print(sys.stdin.read(), end='')", encoding="utf-8")
        self.input.write_text("你好，測資！\n", encoding="utf-8")
        self.expected.write_text("你好，測資！\n", encoding="utf-8")
        self.assertEqual(self.run_cli().returncode, 0)


if __name__ == "__main__":
    unittest.main()
