# 匯入 sys，用目前的 Python 執行檔啟動測試程式。
import sys
# 匯入 Python 內建的 unittest 測試框架。
import unittest

# 匯入待測的換行正規化函式及核心驗證函式。
from validator_core import normalize_output, validate


# 建立測試類別；繼承 TestCase 後可使用 assert 系列斷言。
class ValidatorTests(unittest.TestCase):
    # 定義測試輔助函式，預設輸入與答案為空、時間上限為 5 秒。
    def run_python(self, source, input_text="", expected="", timeout=5):
        # 用目前 Python 的 -c 選項執行 source 字串，並回傳驗證結果。
        return validate([sys.executable, "-c", source], input_text, expected, timeout)

    # 測試能否傳入 stdin 並分別收集 stdout、stderr；test_ 開頭會被 unittest 發現。
    def test_sends_input_and_captures_stdout_and_stderr(self):
        # 開始執行下方字串構成的小程式。
        result = self.run_python(
            # 子程式先匯入 sys，讀取兩個整數；相鄰的字串常值會自動接成一段程式。
            "import sys; a, b = map(int, sys.stdin.read().split()); "
            # 子程式印出總和到 stdout，並把 diagnostic 印到 stderr。
            "print(a + b); print('diagnostic', file=sys.stderr)",
            # 設定輸入為 2、3 加換行，預期答案為 5。
            "2 3\n", "5",
        )  # 結束上方多行函式呼叫的參數列表。
        # 確認結果判定通過；斷言失敗會讓此測試失敗。
        self.assertTrue(result.passed)
        # 確認實際 stdout 正規化後等於 5。
        self.assertEqual(normalize_output(result.stdout), "5")
        # 確認 diagnostic 出現在 stderr，驗證錯誤串流有被擷取。
        self.assertIn("diagnostic", result.stderr)

    # 測試答案不符時能指出第一個不同的行號。
    def test_wrong_output_identifies_line(self):
        # 讓程式輸出 first 與 wrong，預期第二行卻為 right。
        result = self.run_python("print('first'); print('wrong')", expected="first\nright")
        # 確認答案不同時判定不通過。
        self.assertFalse(result.passed)
        # 確認訊息指出差異在第 2 行。
        self.assertIn("第 2 行", result.message)

    # 測試空白與多餘空行仍有意義，但換行格式可不同。
    def test_whitespace_and_extra_blank_lines_matter(self):
        # 確認尾端空格不會被移除，所以兩個答案不同。
        self.assertNotEqual(normalize_output("5 \n"), normalize_output("5"))
        # 確認多餘空行不會被全部忽略，所以兩個答案不同。
        self.assertNotEqual(normalize_output("5\n\n"), normalize_output("5\n"))
        # 確認 CRLF 與 LF 經正規化後相同，且允許少一個結尾換行。
        self.assertEqual(normalize_output("a\r\nb\r\n"), normalize_output("a\nb"))

    # 測試即使答案正確，非零結束代碼仍不能通過。
    def test_nonzero_exit_does_not_pass_even_when_output_matches(self):
        # 子程式印出正確的 5，但故意以代碼 2 結束。
        result = self.run_python("import sys; print('5'); sys.exit(2)", expected="5")
        # 確認結果不通過。
        self.assertFalse(result.passed)
        # 確認保留子程式原本的結束代碼 2。
        self.assertEqual(result.returncode, 2)

    # 測試逾時後仍保留已產生的部分輸出。
    def test_timeout_keeps_partial_output(self):
        # 開始執行會超時的小程式。
        result = self.run_python(
            # 立即印出並 flush 清空輸出緩衝區，再睡 10 秒；驗證上限只有 1 秒。
            "import time; print('started', flush=True); time.sleep(10)", timeout=1,
        )  # 結束上方多行函式呼叫的參數列表。
        # 確認逾時結果不通過。
        self.assertFalse(result.passed)
        # 確認逾時時未提供正常完成的結束代碼。
        self.assertIsNone(result.returncode)
        # 確認判定訊息包含「逾時」。
        self.assertIn("逾時", result.message)
        # 確認停止前印出的 started 仍被保存。
        self.assertIn("started", result.stdout)

    # 測試不存在的執行檔是否被正確處理。
    def test_missing_executable(self):
        # 指定不存在的程式，輸入及預期答案均為空字串。
        result = validate(["./nonexistent-validator-test-program.exe"], "", "")
        # 確認啟動失敗不會被誤判通過。
        self.assertFalse(result.passed)
        # 確認結果包含無法啟動的說明。
        self.assertIn("無法啟動", result.message)

    # 測試沒有任何輸出的程式是否能與空答案匹配。
    def test_empty_output(self):
        # pass 是不做任何事的 Python 敘述；正常結束且輸出為空，因此應通過。
        self.assertTrue(self.run_python("pass").passed)

    # 測試中文 UTF-8 輸入與輸出的傳遞。
    def test_utf8_input_and_output(self):
        # 開始執行會原樣回傳輸入位元組的程式。
        result = self.run_python(
            # 使用 buffer 以位元組讀入並寫出，避免子程式文字編碼干擾測試。
            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
            # 輸入中文加換行，預期中文不含末尾換行，驗證可忽略一個末尾換行。
            "測試資料\n", "測試資料",
        )  # 結束上方多行函式呼叫的參數列表。
        # 確認中文資料能通過比對。
        self.assertTrue(result.passed)

    # 測試錯誤編碼不能因顯示成替代字元而被誤判正確。
    def test_invalid_utf8_does_not_pass_using_replacement_character(self):
        # 開始執行故意輸出無效 UTF-8 的程式。
        result = self.run_python(
            # 輸出位元組 255（不是有效的單獨 UTF-8 字元），預期文字設成 Unicode 替代字元。
            "import sys; sys.stdout.buffer.write(bytes([255]))", expected="\ufffd",
        )  # 結束上方多行函式呼叫的參數列表。
        # 確認即使顯示文字看似相符，仍判定不通過。
        self.assertFalse(result.passed)
        # 確認訊息指出 UTF-8 編碼問題。
        self.assertIn("UTF-8", result.message)

    # 測試不合法的時間上限。
    def test_invalid_timeout(self):
        # 依序測試零、負數、NaN（非數值）與正無限大。
        for timeout in (0, -1, float("nan"), float("inf")):
            # subTest 區分各組參數；assertRaises 要求區塊內必須拋出 ValueError。
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                # 以不合法上限呼叫驗證，應在啟動子程式前就拋出例外。
                self.run_python("pass", timeout=timeout)


# 直接執行此測試檔時才進入下方程式。
if __name__ == "__main__":
    # 交給 unittest 找出並執行本檔案的測試。
    unittest.main()
