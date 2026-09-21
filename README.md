# github-actions-practice
Practice project for learning GitHub Actions

## 逐行註解閱讀方式

專案的 Python、C++、GitHub Actions 設定及 `.gitignore` 已加入繁體中文註解。
Python 的 `#`、C++ 的 `//` 後面是說明，不會作為程式執行；Python 的三引號文字是文件字串。
註解放在程式上一行時，說明緊接著的那一行；放在行尾時，說明同一行。
空白行用來分隔段落；Python 的縮排則決定函式、迴圈與條件判斷的範圍，不可任意刪除。
Markdown 的 `#` 是標題、三個反引號包住的是程式區塊，文件本身不會自動執行指令。

建議依序閱讀 [hello.py](hello.py)、[validator.py](validator.py)、[validator_core.py](validator_core.py)，
再閱讀 [核心測試](tests/test_validator_core.py)、[CLI 測試](tests/test_validator_cli.py)、
[GitHub Actions](.github/workflows/hello.yml) 與 [C++ 範例](examples/sum.cpp)。
所有 `.txt` 都是純資料；各檔案每一行的內容與用途整理在 [測資逐行說明](docs/test-data-lines.md)。

## Validator：CLI 單筆測資驗證工具

從輸入測資檔案讀取內容，固定執行專案內的 `hello.py`，再與預期輸出檔案自動比對。
結果直接顯示在終端機，不需要 GUI 或互動操作。
需要 Python 3.9 以上，無須安裝額外套件。

### 使用方式

使用者將解答寫在 [hello.py](hello.py)，從標準輸入讀取測資，只印出答案。
目前提供兩數相加的範例，使用 `sys.stdin.read().split()`，支援空格或分行輸入。

在專案資料夾執行，指定輸入測資與正確答案檔案：

```powershell
# 執行驗證工具；--input 指定輸入檔，--expected 指定答案檔；這兩個檔案需先自行準備。
python validator.py --input ".\input.txt" --expected ".\output.txt"
```

- `--input`：輸入測資檔案，內容會自動傳給程式的標準輸入（stdin）。
- `--expected`：輸出測資檔案，也就是正確答案，用來比對程式的標準輸出（stdout）。
- `--timeout`：選填，執行時間上限，單位為秒，預設為 5。

路徑相對於下指令時所在的資料夾，也可以使用絕對路徑；路徑含空格時請加引號。
每次執行都會重新讀取檔案，不需要將測資貼進程式碼。
驗證目標固定為 `validator.py` 同一個資料夾的 `hello.py`，使用啟動 validator 的 Python 執行。

例如使用專案內的加法測資：

```powershell
# 使用 examples 內附的測資與答案，並把解答程式的時間上限設成 3 秒。
python validator.py --input ".\examples\input.txt" --expected ".\examples\expected.txt" --timeout 3
```

[examples/input.txt](examples/input.txt) 內容為 `2 3`；
[examples/expected.txt](examples/expected.txt) 的正確答案為 `5`。
專案中的 `hello.py` 已提供對應解答，可以直接執行上面的指令。

### 已附測資

[testcases/sum](testcases/sum/README.md) 提供 **12 組兩數相加測資**，每組包含輸入檔與正確答案檔。
涵蓋正數、零、負數、正負混合、相消、大數、32 位元整數邊界、分行與空白格式。

```powershell
# 執行第 01 組正數加法測資，將 hello.py 的實際結果與同名答案檔比對。
python validator.py --input ".\testcases\sum\01_positive.input.txt" --expected ".\testcases\sum\01_positive.expected.txt"
```

資料夾說明中也提供跑完全部 12 組的 PowerShell 迴圈。
這些測資適用於 `hello.py` 範例的兩數相加規格；其他題目需要對應的題目規格與答案。

### GitHub Actions 自動驗證

[hello.yml](.github/workflows/hello.yml) 會在每次 push 時自動觸發，不限分支。
第一次請將 Workflow、`hello.py`、`validator.py`、`validator_core.py` 與 `testcases/sum` 測資一併提交並推送到 GitHub。
之後學生只要修改 `hello.py`、commit 並 push，就不需要在本機開終端機執行 validator。

```text
學生修改 hello.py → git push → Workflow 自動觸發 → validator 逐筆驗證
                                                   ├─ 全部 PASS → 綠勾
                                                   └─ 任一 FAIL → 紅叉
```

Workflow 會準備 Python 3.12，搜尋 `testcases/sum/*.input.txt`，並搭配同名的 `.expected.txt` 呼叫 validator。
目前共 12 組；日後新增同格式的測資檔案並推送，也會自動納入驗證。
每組解答最多執行 5 秒，失敗後仍會繼續驗證其餘測資。
答案錯誤、程式異常、逾時、缺少答案檔或完全沒有測資，都會讓驗證步驟失敗。

推送後，到 GitHub 儲存庫的 **Actions → Validate hello.py → 該次執行 → run-python → Run validator**，
展開各測資群組即可查看 PASS／FAIL；失敗時會顯示原因及相關輸出。
GitHub 依步驟的結束代碼判定成功或失敗（[官方說明](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/set-exit-codes)）。

### 參數說明

查看完整參數：

```powershell
# 顯示可用參數與預設值，顯示完就結束，不會執行 hello.py。
python validator.py --help
```

### CLI 結果

通過時的輸出範例（耗時依實際執行而定）：

```text
PASS：通過：實際輸出與預期輸出相符。
耗時：0.025 秒｜程式結束代碼：0
--- 實際輸出（stdout） ---
5
```

上述四行依序表示：驗證是否通過與原因、耗時及解答結束代碼、實際輸出區塊的標題、解答印出的答案。

答案不同時會顯示 `FAIL`、第一個不同的行號、實際輸出與預期輸出。
程式異常結束或逾時也會顯示 `FAIL`；有標準錯誤（stderr）時一併列出。

| Validator 結束代碼 | 意義 |
| --- | --- |
| 0 | 答案相符，且程式正常結束 |
| 1 | 答案不符、執行失敗、逾時或程式輸出編碼無效 |
| 2 | 參數錯誤、指定檔案不存在，或測資無法讀取 |

PowerShell 可使用 `$LASTEXITCODE` 取得結束代碼。
自動化腳本或 GitHub Actions 也可以根據非 0 結束代碼判定失敗。

### 執行方式與比對規則

- 一次驗證一組輸入與預期輸出檔案，`hello.py` 可用 `input()` 或 `sys.stdin` 讀取資料，以 `print()` 輸出答案。
- 測資檔案須為 UTF-8，接受含 BOM 的檔案；讀取時移除檔案開頭的 BOM。
- 輸入保留原有換行與空白，以 UTF-8 傳入；不自動補換行，送完後關閉標準輸入，程式可以讀到 EOF。
- `hello.py` 以獨立的 Python 行程執行，啟用 UTF-8 模式，工作目錄為它所在的專案資料夾。
- 逾時會停止啟動的程式，並顯示已擷取的輸出。
- 程式輸出須為 UTF-8，編碼無效時不會判定通過。
- 比對時統一 Windows／Linux 換行格式，忽略最後一個換行；其餘空格、Tab、多餘空白行皆須相符。
- stderr 另外列出，不參與答案比對。程式結束代碼非 0 時視為執行失敗。

本版直接在本機執行程式，沒有沙箱隔離；請執行你信任的程式碼。
目前不支援要求程式自行開啟指定檔案的輸入／輸出方式、互動式對話、批次測資或子行程管理。

### 程式結構與測試

- `hello.py`：使用者撰寫的解答，目前為兩數相加範例。
- `validator.py`：CLI 參數、測資檔案讀取、執行 `hello.py`、結果顯示與結束代碼。
- `validator_core.py`：執行程式與比對答案。
- `tests/test_validator_core.py`：核心功能測試。
- `tests/test_validator_cli.py`：透過 CLI 實際執行程式的整合測試。

執行測試：

```powershell
# -m 執行 unittest 模組；discover 自動尋找測試；-s tests 指定資料夾；-v 顯示每個測試的詳細結果。
python -m unittest discover -s tests -v
```
