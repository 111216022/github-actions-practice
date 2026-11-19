"""將成對的測資檔案合併為一份 JSON，保留原始空白與換行。"""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def collect_testcases(source):
    inputs = sorted(source.rglob("*.input.txt"))
    if not inputs:
        raise ValueError(f"找不到輸入測資：{source}")

    expected_files = {path.with_name(path.name.removesuffix(".input.txt") + ".expected.txt")
                      for path in inputs}
    actual_files = set(source.rglob("*.expected.txt"))
    if expected_files != actual_files:
        missing = sorted(str(path) for path in expected_files - actual_files)
        orphaned = sorted(str(path) for path in actual_files - expected_files)
        raise ValueError(f"測資配對不完整；缺少答案：{missing}；缺少輸入：{orphaned}")

    cases = []
    for path in inputs:
        expected = path.with_name(path.name.removesuffix(".input.txt") + ".expected.txt")
        cases.append({
            "id": path.relative_to(source).as_posix().removesuffix(".input.txt"),
            # 直接解碼位元組，避免 read_text() 自動轉換 CRLF 換行。
            "input": path.read_bytes().decode("utf-8-sig"),
            "expected": expected.read_bytes().decode("utf-8-sig"),
        })
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "testcases")
    parser.add_argument("--output", type=Path, default=ROOT / "testcases" / "testcases.json")
    args = parser.parse_args()
    try:
        cases = collect_testcases(args.source)
        content = json.dumps(cases, ensure_ascii=False, indent=2) + "\n"
        args.output.write_bytes(content.encode("utf-8"))
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(f"已合併 {len(cases)} 組測資：{args.output}")


if __name__ == "__main__":
    main()
