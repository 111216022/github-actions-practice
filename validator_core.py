"""執行一筆標準輸入測資，並比較程式的標準輸出與正確答案。"""

# 匯入 dataclass，自動產生資料類別的初始化等方法。
from dataclasses import dataclass
# 匯入 math，用來檢查時間上限是否合法。
import math
# 匯入 Path，作為工作目錄參數的型別提示。
from pathlib import Path
# 匯入 subprocess，用來啟動解答程式並擷取輸出。
import subprocess
# 匯入 time，用來計算執行耗時。
import time
# 匯入型別提示：Optional 表示也可為 None；Sequence 表示序列。
from typing import Optional, Sequence


# 將下方類別轉成 dataclass，可依欄位順序建立結果物件。
@dataclass
# 定義存放一次驗證結果的資料類別。
class ValidationResult:
    # stdout 欄位保存解答的標準輸出文字；str 是型別提示。
    stdout: str
    # stderr 欄位保存解答的錯誤或診斷文字。
    stderr: str
    # 保存解答結束代碼；逾時或啟動失敗時可以是 None。
    returncode: Optional[int]
    # 保存執行耗時，以浮點秒數表示。
    elapsed: float
    # 保存驗證是否通過的布林值 True 或 False。
    passed: bool
    # 保存給使用者看的判定說明。
    message: str


# 定義輸出正規化函式，接收並回傳字串；型別提示不會自行強制轉型。
def normalize_output(text: str) -> str:
    """統一換行格式，並忽略最多一個結尾換行。"""
    # 將 Windows 的 CRLF 與單獨 CR 換行都轉成 LF，方便跨平台比較。
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 如果結尾是換行，只移除最後一個字元；其他空白與多餘換行仍保留。
    return text[:-1] if text.endswith("\n") else text


# 定義把原始位元組轉成顯示文字的函式。
def decode_output(data: bytes) -> str:
    # 以 UTF-8 解碼，無法解碼的位元組以替代字元顯示，避免顯示時拋出例外。
    return data.decode("utf-8", errors="replace")


# 開始定義核心驗證函式，下列各行列出它接受的參數。
def validate(
    # command 是包含執行檔與各個參數的字串序列。
    command: Sequence[str],
    # input_text 是要送給解答程式的標準輸入文字。
    input_text: str,
    # expected_output 是要拿來比對的正確答案文字。
    expected_output: str,
    # timeout 是秒數上限，預設為 5 秒。
    timeout: float = 5.0,
    # cwd 是子行程工作目錄；None 表示沿用目前的工作目錄。
    cwd: Optional[Path] = None,
# 結束參數列表，宣告此函式回傳 ValidationResult。
) -> ValidationResult:
    """直接啟動程式、不經 shell，傳入 UTF-8 輸入並收集輸出。"""
    # 檢查 timeout 是否為有限且大於零的數字。
    if not math.isfinite(timeout) or timeout <= 0:
        # 不合法時拋出 ValueError，交由呼叫端處理。
        raise ValueError("執行時間上限必須是大於 0 的有限數字。")
    # 檢查命令序列是否為空，避免沒有可執行的目標。
    if not command:
        # 空命令時拋出 ValueError。
        raise ValueError("請指定執行檔。")

    # 記錄單調時鐘的起始時間，避免系統校時影響耗時計算。
    started = time.monotonic()
    # 嘗試啟動並等待解答程式完成。
    try:
        # 啟動子行程，預設不經過 shell，等待完成後取得執行結果。
        completed = subprocess.run(
            # 將命令序列轉成列表；第一項是執行檔，其餘為參數。
            list(command),
            # 將輸入編碼為 UTF-8 位元組送進 stdin，送完後關閉輸入讓子行程讀到 EOF。
            input=input_text.encode("utf-8"),
            # 以管線擷取標準輸出，而非直接印在父行程的終端機。
            stdout=subprocess.PIPE,
            # 另以管線擷取標準錯誤，與答案輸出分開保存。
            stderr=subprocess.PIPE,
            # 設定等待上限；超過後 subprocess.run 會終止並等待直接啟動的子行程。
            timeout=timeout,
            # 指定子行程的工作目錄。
            cwd=cwd,
            # Windows 使用 CREATE_NO_WINDOW 隱藏子行程視窗；其他平台沒有此常數時使用 0。
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )  # 結束上方多行函式呼叫的參數列表。
    # 捕捉逾時例外，保留例外物件提供的部分輸出。
    except subprocess.TimeoutExpired as error:
        # 建立並立即回傳逾時的驗證結果，欄位依 dataclass 宣告順序傳入。
        return ValidationResult(
            # 解碼逾時前已收到的 stdout；沒有資料時使用空位元組。
            decode_output(error.stdout or b""),
            # 解碼逾時前已收到的 stderr；沒有資料時使用空位元組。
            decode_output(error.stderr or b""),
            # 結束代碼填 None，表示此處沒有取得正常完成的結束代碼。
            None,
            # 以現在時間減起始時間，記錄本次已花費的秒數。
            time.monotonic() - started,
            # passed 設為 False，因為逾時不能算通過。
            False,
            # 建立逾時訊息；:g 以精簡數字格式顯示秒數。
            f"執行逾時：超過 {timeout:g} 秒，已停止執行程式。",
        )  # 結束上方多行函式呼叫的參數列表。
    # 捕捉找不到執行檔、權限不足等作業系統層級的啟動錯誤。
    except OSError as error:
        # 建立並回傳啟動失敗的結果。
        return ValidationResult(
            # 依序填入空 stdout、錯誤文字、無結束代碼、耗時及未通過。
            "", str(error), None, time.monotonic() - started, False,
            # 填入提示使用者查看錯誤訊息的說明。
            "無法啟動執行檔，請查看錯誤訊息。",
        )  # 結束上方多行函式呼叫的參數列表。

    # 把子行程收集到的 stdout 位元組轉成顯示文字。
    stdout = decode_output(completed.stdout)
    # 把子行程收集到的 stderr 位元組轉成顯示文字。
    stderr = decode_output(completed.stderr)
    # 將實際輸出統一換行格式，供後續比對使用。
    actual = normalize_output(stdout)
    # 同樣正規化預期答案，讓兩邊採用相同規則。
    expected = normalize_output(expected_output)
    # 替代字元僅用於顯示；編碼不合法的輸出仍必須判定失敗。
    # 先假設輸出的 UTF-8 編碼正確。
    valid_encoding = True
    # 再以嚴格模式檢查原始輸出，避免替代字元掩蓋錯誤。
    try:
        # 不提供 errors="replace"，遇到無效 UTF-8 會拋出例外。
        completed.stdout.decode("utf-8")
    # 捕捉 UTF-8 解碼失敗。
    except UnicodeDecodeError:
        # 標記輸出編碼無效，後續不可判定通過。
        valid_encoding = False

    # 只有正常結束、編碼有效且答案相同三個條件同時成立，才算通過。
    passed = completed.returncode == 0 and valid_encoding and actual == expected
    # 優先判斷解答是否以非零代碼結束。
    if completed.returncode != 0:
        # 將非零結束代碼填入執行失敗訊息。
        message = f"執行失敗：結束代碼 {completed.returncode}。"
    # 程式正常結束但輸出編碼錯誤時走此分支。
    elif not valid_encoding:
        # 說明輸出不是合法 UTF-8，因此不能通過。
        message = "無法比對：程式輸出不是有效的 UTF-8 文字。"
    # 如果所有通過條件都成立，走此分支。
    elif passed:
        # 設定答案相符的成功訊息。
        message = "通過：實際輸出與預期輸出相符。"
    # 其餘情況代表答案不同，開始尋找第一個差異行。
    else:
        # 以換行拆開實際輸出，保留各行文字。
        actual_lines = actual.split("\n")
        # 以相同方法拆開預期答案。
        expected_lines = expected.split("\n")
        # 逐行比較直到較長一方的末尾；index 從 0 開始。
        for index in range(max(len(actual_lines), len(expected_lines))):
            # 取得實際輸出的該行；如果已超出行數，用 None 表示缺行。
            actual_line = actual_lines[index] if index < len(actual_lines) else None
            # 取得預期答案的該行；如果已超出行數，用 None 表示缺行。
            expected_line = expected_lines[index] if index < len(expected_lines) else None
            # 判斷這一行的文字或是否存在有沒有不同。
            if actual_line != expected_line:
                # 記錄第一個不同的行號，index + 1 轉為使用者習慣的從 1 起算。
                message = f"未通過：第 {index + 1} 行不同（包含空白差異）。"
                # 找到首個差異後停止迴圈，不再比對剩下的行。
                break

    # 把正常執行後的各項資料組成驗證結果並回傳。
    return ValidationResult(
        # 依序保存原始顯示文字 stdout、stderr，以及解答結束代碼。
        stdout, stderr, completed.returncode,
        # 保存本次耗時、是否通過及判定訊息。
        time.monotonic() - started, passed, message,
    )  # 結束上方多行函式呼叫的參數列表。
