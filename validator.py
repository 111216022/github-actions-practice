"""從命令列讀取一組輸入與答案檔案，執行解答並顯示比對結果。"""

# 匯入命令列參數解析工具 argparse。
import argparse
# 匯入 math，稍後檢查秒數是否為有限數字。
import math
# 匯入 Path，以物件方式處理檔案路徑。
from pathlib import Path
# 匯入 sys，取得 Python 執行檔、輸出串流與結束程式的方法。
import sys

# 從同專案的 validator_core 匯入執行與比對答案的 validate 函式。
from validator_core import validate


# 定義 argparse 使用的轉換函式，把參數文字轉成合法秒數。
def positive_seconds(value):
    # 嘗試轉換；遇到下方指定的例外時改為顯示參數錯誤。
    try:
        # 把文字轉成浮點數，例如 "0.5" 變成 0.5。
        seconds = float(value)
    # 捕捉無法轉成浮點數的 ValueError。
    except ValueError:
        # 回報 argparse 可辨識的參數錯誤，讓 CLI 顯示用法並以代碼 2 結束。
        raise argparse.ArgumentTypeError("時間上限必須是大於 0 的有限秒數。")
    # 排除 NaN、正負無限大，以及小於或等於零的秒數。
    if not math.isfinite(seconds) or seconds <= 0:
        # 回報秒數不合法，停止解析這個參數。
        raise argparse.ArgumentTypeError("時間上限必須是大於 0 的有限秒數。")
    # 回傳驗證通過的浮點秒數。
    return seconds


# 定義讀取測資檔案的函式，path 是 Path 物件。
def read_test_file(path):
    # 接受 Windows 編輯器可能加入的 UTF-8 BOM，同時保留測資原有換行。
    # 以文字模式讀檔；utf-8-sig 會移除開頭的 BOM，newline="" 保留原本換行，with 會自動關檔。
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        # 讀取並回傳整份檔案的字串。
        return file.read()


# 定義輸出區塊的顯示函式，接收標題與文字。
def print_output(title, text):
    # 使用 f-string 將 title 插入分隔標題並印出。
    print(f"--- {title} ---")
    # 文字不是空字串時，印出實際內容。
    if text:
        # 若文字已以換行結尾就不再補換行，否則補一個，避免下一段接在同一行。
        print(text, end="" if text.endswith("\n") else "\n")
    # 文字為空時改走此分支。
    else:
        # 印出空內容提示，方便區分沒有輸出與未顯示。
        print("（空）")


# 定義 CLI 主函式；argv=None 時解析使用者的命令列參數，也可傳入參數清單。
def main(argv=None):
    # 建立命令列解析器，同時自動提供 --help。
    parser = argparse.ArgumentParser(
        # 設定 --help 顯示的程式用途說明。
        description="讀取測資檔案，執行專案的 hello.py，並自動比對實際輸出與預期答案。",
    )  # 結束上方多行函式呼叫的參數列表。
    # 定義必填的 --input，把使用者輸入的路徑轉成 Path。
    parser.add_argument("--input", required=True, type=Path, help="輸入測資檔案（UTF-8）")
    # 定義必填的 --expected，指定正確答案檔案路徑。
    parser.add_argument("--expected", required=True, type=Path, help="預期輸出檔案（UTF-8）")
    # 開始定義可選的執行時間參數。
    parser.add_argument(
        # --timeout 使用 positive_seconds 驗證與轉換，未指定時為 5 秒。
        "--timeout", type=positive_seconds, default=5.0,
        # 設定 --timeout 在說明畫面中的文字。
        help="執行時間上限，單位為秒（預設：5）",
    )  # 結束上方多行函式呼叫的參數列表。
    # 解析參數；缺少必填值或格式錯誤時，argparse 會顯示錯誤並結束。
    args = parser.parse_args(argv)

    # 開始處理尋找程式與讀檔過程可能發生的錯誤。
    try:
        # 取得本檔案的絕對路徑，再把檔名換成 hello.py，確保執行同資料夾的解答。
        script = Path(__file__).resolve().with_name("hello.py")
        # 檢查目標路徑是否為存在的普通檔案。
        if not script.is_file():
            # 找不到 hello.py 時顯示用法錯誤，並以代碼 2 結束。
            parser.error(f"找不到要驗證的 hello.py：{script}")
        # 將輸入路徑開頭的 ~ 展開為使用者家目錄，再讀取測資。
        input_text = read_test_file(args.input.expanduser())
        # 以相同方式讀取預期答案檔案。
        expected_output = read_test_file(args.expected.expanduser())
    # 捕捉檔案存取、文字編碼或路徑值的錯誤，將例外存入 error。
    except (OSError, UnicodeError, ValueError) as error:
        # 顯示讀檔失敗原因，並以參數錯誤代碼 2 結束。
        parser.error(f"無法讀取檔案（測資須為 UTF-8）：{error}")

    # 呼叫核心驗證函式，取得包含輸出、耗時與是否通過的結果。
    result = validate(
        # 使用目前的 Python 啟動 hello.py；-X utf8 開啟 UTF-8 模式，後兩個參數是輸入與答案。
        [sys.executable, "-X", "utf8", str(script)], input_text, expected_output,
        # 傳入使用者指定的時間上限，並以 hello.py 所在資料夾作為子行程工作目錄。
        timeout=args.timeout, cwd=script.parent,
    )  # 結束上方多行函式呼叫的參數列表。
    # 依 passed 選擇 PASS 或 FAIL，再印出具體判定訊息。
    print(f"{'PASS' if result.passed else 'FAIL'}：{result.message}")
    # 如果沒有結束代碼就顯示「無」，否則將整數代碼轉成字串。
    code = "無" if result.returncode is None else str(result.returncode)
    # 印出耗時（小數點後三位）及解答程式的結束代碼。
    print(f"耗時：{result.elapsed:.3f} 秒｜程式結束代碼：{code}")
    # 顯示解答程式的標準輸出 stdout。
    print_output("實際輸出（stdout）", result.stdout)
    # 驗證未通過時，額外顯示預期答案以便比較。
    if not result.passed:
        # 印出預期輸出區塊。
        print_output("預期輸出", expected_output)
    # 如果標準錯誤 stderr 有內容，就顯示它。
    if result.stderr:
        # 印出解答程式的錯誤或診斷訊息。
        print_output("程式錯誤訊息（stderr）", result.stderr)
    # 回傳 validator 的結束代碼：通過為 0，驗證失敗為 1。
    return 0 if result.passed else 1


# 只有直接執行 validator.py 才啟動 CLI；被匯入時只提供函式。
if __name__ == "__main__":
    # 終端機無法表示某些字元時，也要讓驗證結果能順利印出。
    # 依序處理標準輸出與標準錯誤兩個文字串流。
    for stream in (sys.stdout, sys.stderr):
        # 檢查串流是否支援 reconfigure，避免特殊環境沒有這個方法。
        if hasattr(stream, "reconfigure"):
            # 無法用終端機編碼表示的字元改印反斜線跳脫形式，避免顯示結果時崩潰。
            stream.reconfigure(errors="backslashreplace")
    # 執行 main()，並以其回傳值作為整個 validator 行程的結束代碼。
    sys.exit(main())
