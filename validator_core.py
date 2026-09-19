"""Run one standard-input test case and compare its standard output."""

from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import time
from typing import Optional, Sequence


@dataclass
class ValidationResult:
    stdout: str
    stderr: str
    returncode: Optional[int]
    elapsed: float
    passed: bool
    message: str


def normalize_output(text: str) -> str:
    """Normalize line endings and ignore one optional final line break."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text[:-1] if text.endswith("\n") else text


def decode_output(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def validate(
    command: Sequence[str],
    input_text: str,
    expected_output: str,
    timeout: float = 5.0,
    cwd: Optional[Path] = None,
) -> ValidationResult:
    """Execute directly (without a shell), send UTF-8 input, and capture output."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("執行時間上限必須是大於 0 的有限數字。")
    if not command:
        raise ValueError("請指定執行檔。")

    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            input=input_text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            cwd=cwd,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as error:
        return ValidationResult(
            decode_output(error.stdout or b""),
            decode_output(error.stderr or b""),
            None,
            time.monotonic() - started,
            False,
            f"執行逾時：超過 {timeout:g} 秒，已停止執行程式。",
        )
    except OSError as error:
        return ValidationResult(
            "", str(error), None, time.monotonic() - started, False,
            "無法啟動執行檔，請查看錯誤訊息。",
        )

    stdout = decode_output(completed.stdout)
    stderr = decode_output(completed.stderr)
    actual = normalize_output(stdout)
    expected = normalize_output(expected_output)
    # Replacement characters are for display only: malformed UTF-8 must not pass.
    valid_encoding = True
    try:
        completed.stdout.decode("utf-8")
    except UnicodeDecodeError:
        valid_encoding = False

    passed = completed.returncode == 0 and valid_encoding and actual == expected
    if completed.returncode != 0:
        message = f"執行失敗：結束代碼 {completed.returncode}。"
    elif not valid_encoding:
        message = "無法比對：程式輸出不是有效的 UTF-8 文字。"
    elif passed:
        message = "通過：實際輸出與預期輸出相符。"
    else:
        actual_lines = actual.split("\n")
        expected_lines = expected.split("\n")
        for index in range(max(len(actual_lines), len(expected_lines))):
            actual_line = actual_lines[index] if index < len(actual_lines) else None
            expected_line = expected_lines[index] if index < len(expected_lines) else None
            if actual_line != expected_line:
                message = f"未通過：第 {index + 1} 行不同（包含空白差異）。"
                break

    return ValidationResult(
        stdout, stderr, completed.returncode,
        time.monotonic() - started, passed, message,
    )
