# 匯入 os，用來取得原本的環境變數。
import os
# 匯入 Path，處理測試資料與程式路徑。
from pathlib import Path
# 匯入 shutil，用來複製程式到測試用資料夾。
import shutil
# 匯入 subprocess，用獨立行程測試真正的 CLI。
import subprocess
# 匯入 sys，取得目前 Python 執行檔的位置。
import sys
# 匯入 tempfile，建立測試用暫存資料夾。
import tempfile
# 匯入 unittest 測試框架。
import unittest

# 匯入讀檔函式，直接檢查它是否保留原始換行。
from validator import read_test_file


# 由此測試檔的絕對路徑往上兩層取得專案根目錄，再指向 validator.py。
CLI = Path(__file__).resolve().parents[1] / "validator.py"


# 定義 CLI 整合測試類別，繼承 unittest 的斷言與生命週期功能。
class ValidatorCliTests(unittest.TestCase):
    # setUp 會在每個測試方法之前執行，建立各自獨立的測試環境。
    def setUp(self):
        # 建立名稱含空格的暫存目錄，同時測試含空格路徑的支援。
        self.directory = tempfile.TemporaryDirectory(prefix="validator test ")
        # 登記測試結束時清除暫存目錄，即使測試失敗也會呼叫。
        self.addCleanup(self.directory.cleanup)
        # 把暫存目錄名稱轉成 Path 物件，供下面組合子路徑。
        self.folder = Path(self.directory.name)
        # 設定輸入檔路徑，檔名刻意包含空格。
        self.input = self.folder / "input data.txt"
        # 設定正確答案檔路徑，檔名也包含空格。
        self.expected = self.folder / "expected output.txt"
        # 設定測試用專案資料夾路徑。
        self.project = self.folder / "project files"
        # 實際建立測試用專案資料夾。
        self.project.mkdir()
        # 依序處理 CLI、核心模組及解答程式三個檔案。
        for name in ("validator.py", "validator_core.py", "hello.py"):
            # 把原專案的檔案複製到暫存專案，讓測試修改副本。
            shutil.copyfile(CLI.parent / name, self.project / name)
        # 保存暫存 hello.py 的路徑，供各測試替換內容。
        self.script = self.project / "hello.py"
        # 建立 UTF-8 輸入檔，內容是兩個整數 2、3。
        self.input.write_text("2 3\n", encoding="utf-8")
        # 建立 UTF-8 預期答案檔，內容是 5 加換行。
        self.expected.write_text("5\n", encoding="utf-8")

    # 定義啟動 CLI 的輔助函式；*extra 收集額外命令列參數。
    def run_cli(self, *extra):
        # 啟動獨立的 validator 行程並回傳其執行結果。
        return subprocess.run(
            # 使用目前 Python 執行暫存專案的 validator.py；參數以清單傳入，含空格路徑不會被拆開。
            [sys.executable, str(self.project / "validator.py"),
             # 提供輸入與答案路徑，再用 *extra 展開額外參數；重複選項會由 argparse 採用後面的值。
             "--input", str(self.input), "--expected", str(self.expected), *extra],
            # 分別擷取 CLI 的 stdout 與 stderr，供測試檢查。
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            # 以 UTF-8 解碼 CLI 輸出，並限制整個 CLI 最多等待 15 秒。
            encoding="utf-8", timeout=15,
            # 沿用目前環境變數，覆寫 PYTHONIOENCODING，固定子行程文字串流編碼為 UTF-8。
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            # 刻意在暫存資料夾啟動，驗證 CLI 不依賴使用者目前目錄尋找 hello.py。
            cwd=self.folder,
        )  # 結束上方多行函式呼叫的參數列表。

    # 測試路徑含空格時能正常讀取測資並顯示通過結果。
    def test_pass_reads_files_with_spaces_in_paths(self):
        # 以預設測資執行 CLI。
        result = self.run_cli()
        # 確認結束代碼為 0；不符合時將 stderr 當成斷言失敗訊息。
        self.assertEqual(result.returncode, 0, result.stderr)
        # 確認 stdout 包含 PASS。
        self.assertIn("PASS", result.stdout)
        # 確認 stdout 有實際輸出的區塊標題。
        self.assertIn("實際輸出", result.stdout)
        # 確認 stdout 包含獨立一行的答案 5。
        self.assertIn("\n5\n", result.stdout)

    # 測試答案錯誤時是否同時顯示實際與預期答案。
    def test_wrong_answer_prints_actual_and_expected(self):
        # 將預期答案故意改成 6，讓它與計算結果 5 不同。
        self.expected.write_text("6\n", encoding="utf-8")
        # 執行 CLI 取得錯誤答案的判定。
        result = self.run_cli()
        # 確認驗證失敗使用結束代碼 1。
        self.assertEqual(result.returncode, 1)
        # 確認畫面包含 FAIL。
        self.assertIn("FAIL", result.stdout)
        # 確認指出第 1 行不同。
        self.assertIn("第 1 行", result.stdout)
        # 確認顯示實際答案 5。
        self.assertIn("\n5\n", result.stdout)
        # 確認也顯示預期答案 6。
        self.assertIn("\n6\n", result.stdout)

    # 測試輸入檔不存在時應回報使用方式錯誤。
    def test_missing_input_is_usage_error(self):
        # 以額外 --input 覆寫原路徑，指向不存在的 missing.txt。
        result = self.run_cli("--input", str(self.folder / "missing.txt"))
        # 確認參數或檔案問題使用結束代碼 2。
        self.assertEqual(result.returncode, 2)
        # 確認 stderr 包含讀檔失敗的友善訊息。
        self.assertIn("無法讀取檔案", result.stderr)
        # 確認沒有顯示未處理例外的 Traceback 堆疊。
        self.assertNotIn("Traceback", result.stderr)

    # 測試缺少 hello.py 時應回報使用方式錯誤。
    def test_missing_hello_is_usage_error(self):
        # 把暫存解答改名，製造找不到 hello.py 的情境。
        self.script.rename(self.project / "renamed.py")
        # 執行 CLI。
        result = self.run_cli()
        # 確認缺少解答檔案的結束代碼為 2。
        self.assertEqual(result.returncode, 2)
        # 確認 stderr 說明找不到要驗證的 hello.py。
        self.assertIn("找不到要驗證的 hello.py", result.stderr)

    # 測試選擇的是 validator 同目錄的 hello.py，而非目前工作目錄中的同名檔。
    def test_uses_hello_next_to_validator_instead_of_current_directory(self):
        # 在工作目錄建立一份一執行就會拋出 RuntimeError 的假解答。
        (self.folder / "hello.py").write_text("raise RuntimeError('wrong script')", encoding="utf-8")
        # 執行 CLI，應選到暫存專案內的正確解答。
        result = self.run_cli()
        # 確認仍能正常通過；否則顯示 stderr 協助找原因。
        self.assertEqual(result.returncode, 0, result.stderr)

    # 測試解答有 Python 語法錯誤時的處理。
    def test_syntax_error_in_hello_is_validation_failure(self):
        # 把暫存解答改成缺少右括號的函式宣告，故意造成語法錯誤。
        self.script.write_text("def broken(\n", encoding="utf-8")
        # 執行 CLI，讓它捕捉解答程式的失敗。
        result = self.run_cli()
        # 確認解答失敗使 validator 回傳 1。
        self.assertEqual(result.returncode, 1)
        # 確認 CLI 把解答 stderr 中的 SyntaxError 顯示在結果畫面。
        self.assertIn("SyntaxError", result.stdout)

    # 測試測資檔案編碼無效時的處理。
    def test_invalid_encoding_is_usage_error(self):
        # 把預期答案改成無效 UTF-8 位元組 0xff。
        self.expected.write_bytes(b"\xff")
        # 執行 CLI，觸發讀檔解碼失敗。
        result = self.run_cli()
        # 確認測資讀取問題回傳 2。
        self.assertEqual(result.returncode, 2)
        # 確認錯誤訊息包含 UTF-8。
        self.assertIn("UTF-8", result.stderr)
        # 確認沒有直接印出未處理的例外堆疊。
        self.assertNotIn("Traceback", result.stderr)

    # 測試檔案開頭含 UTF-8 BOM 時仍能讀取。
    def test_utf8_bom_files(self):
        # 用 utf-8-sig 寫入帶 BOM 的輸入測資。
        self.input.write_text("2 3\n", encoding="utf-8-sig")
        # 以相同編碼寫入帶 BOM 的預期答案。
        self.expected.write_text("5\n", encoding="utf-8-sig")
        # 確認含 BOM 的兩個檔案仍能通過，CLI 回傳 0。
        self.assertEqual(self.run_cli().returncode, 0)

    # 測試讀檔函式保留 CRLF 換行與行尾空白。
    def test_reading_preserves_input_line_endings_and_trailing_whitespace(self):
        # 直接寫入原始位元組，包含 Windows 換行及一行空格，避免寫檔時自動轉換換行。
        self.input.write_bytes(b"2 3\r\n \r\n")
        # 確認讀回的字串與原始內容完全相同，沒有移除空白或轉換 CRLF。
        self.assertEqual(read_test_file(self.input), "2 3\r\n \r\n")

    # 測試解答執行失敗時是否顯示 stderr。
    def test_runtime_failure_reports_stderr(self):
        # 開始覆寫暫存解答程式。
        self.script.write_text(
            # 子程式印 problem 到 stderr，再以代碼 7 結束；檔案以 UTF-8 寫入。
            "import sys; print('problem', file=sys.stderr); sys.exit(7)", encoding="utf-8",
        )  # 結束上方多行函式呼叫的參數列表。
        # 執行 CLI。
        result = self.run_cli()
        # 確認 validator 本身回傳驗證失敗代碼 1。
        self.assertEqual(result.returncode, 1)
        # 確認畫面包含 FAIL。
        self.assertIn("FAIL", result.stdout)
        # 確認畫面另有顯示解答程式的結束代碼 7。
        self.assertIn("結束代碼 7", result.stdout)
        # 確認解答的 problem 診斷訊息有被列出。
        self.assertIn("problem", result.stdout)

    # 測試解答逾時時是否回報驗證失敗。
    def test_timeout_returns_failure(self):
        # 建立會睡眠 10 秒的解答程式。
        self.script.write_text("import time; time.sleep(10)", encoding="utf-8")
        # 將 CLI 的解答時間上限設為 0.5 秒，故意觸發逾時。
        result = self.run_cli("--timeout", "0.5")
        # 確認逾時使 validator 回傳 1。
        self.assertEqual(result.returncode, 1)
        # 確認畫面包含逾時說明。
        self.assertIn("逾時", result.stdout)

    # 測試無效的 --timeout 是否被 argparse 拒絕。
    def test_invalid_timeout_is_usage_error(self):
        # 把時間上限設成 nan（非數值）。
        result = self.run_cli("--timeout", "nan")
        # 確認時間參數錯誤回傳代碼 2。
        self.assertEqual(result.returncode, 2)

    # 測試解答使用文字模式 stdin 與 print 時仍能處理中文。
    def test_hello_reads_utf8_input_and_prints_utf8_output(self):
        # 將解答改成讀完整份文字並原樣印出；end='' 避免額外補換行。
        self.script.write_text("import sys; print(sys.stdin.read(), end='')", encoding="utf-8")
        # 寫入包含中文與標點的 UTF-8 輸入檔。
        self.input.write_text("你好，測資！\n", encoding="utf-8")
        # 寫入相同的預期答案。
        self.expected.write_text("你好，測資！\n", encoding="utf-8")
        # 確認中文輸入與輸出能完成驗證，CLI 回傳 0。
        self.assertEqual(self.run_cli().returncode, 0)


# 只有直接執行此測試檔時才進入下方程式。
if __name__ == "__main__":
    # 啟動 unittest，執行本檔案中的所有測試。
    unittest.main()
