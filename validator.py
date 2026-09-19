"""Validate one pair of test files from the command line."""

import argparse
import math
from pathlib import Path
import sys

from validator_core import validate


def positive_seconds(value):
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("時間上限必須是大於 0 的有限秒數。")
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("時間上限必須是大於 0 的有限秒數。")
    return seconds


def read_test_file(path):
    # Accept a UTF-8 BOM from Windows editors without changing input line endings.
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return file.read()


def print_output(title, text):
    print(f"--- {title} ---")
    if text:
        print(text, end="" if text.endswith("\n") else "\n")
    else:
        print("（空）")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="讀取測資檔案，執行專案的 hello.py，並自動比對實際輸出與預期答案。",
    )
    parser.add_argument("--input", required=True, type=Path, help="輸入測資檔案（UTF-8）")
    parser.add_argument("--expected", required=True, type=Path, help="預期輸出檔案（UTF-8）")
    parser.add_argument(
        "--timeout", type=positive_seconds, default=5.0,
        help="執行時間上限，單位為秒（預設：5）",
    )
    args = parser.parse_args(argv)

    try:
        script = Path(__file__).resolve().with_name("hello.py")
        if not script.is_file():
            parser.error(f"找不到要驗證的 hello.py：{script}")
        input_text = read_test_file(args.input.expanduser())
        expected_output = read_test_file(args.expected.expanduser())
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(f"無法讀取檔案（測資須為 UTF-8）：{error}")

    result = validate(
        [sys.executable, "-X", "utf8", str(script)], input_text, expected_output,
        timeout=args.timeout, cwd=script.parent,
    )
    print(f"{'PASS' if result.passed else 'FAIL'}：{result.message}")
    code = "無" if result.returncode is None else str(result.returncode)
    print(f"耗時：{result.elapsed:.3f} 秒｜程式結束代碼：{code}")
    print_output("實際輸出（stdout）", result.stdout)
    if not result.passed:
        print_output("預期輸出", expected_output)
    if result.stderr:
        print_output("程式錯誤訊息（stderr）", result.stderr)
    return 0 if result.passed else 1


if __name__ == "__main__":
    # Keep results printable even on terminals that cannot encode every character.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    sys.exit(main())
