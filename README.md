# github-actions-practice
Practice project for learning GitHub Actions

哈囉 我要上台大 (希望可以)

## Validator：CLI 單筆測資驗證工具

從輸入測資檔案讀取內容，固定執行專案內的 `hello.py`，再與預期輸出檔案自動比對。
結果直接顯示在終端機，不需要 GUI 或互動操作。
需要 Python 3.9 以上，無須安裝額外套件。

### 使用方式

使用者將解答寫在 [hello.py](hello.py)，從標準輸入讀取測資，只印出答案。
目前提供兩數相加的範例，使用 `sys.stdin.read().split()`，支援空格或分行輸入。

在專案資料夾執行，指定輸入測資與正確答案檔案：

```powershell
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
python validator.py --input ".\examples\input.txt" --expected ".\examples\expected.txt" --timeout 3
```

[examples/input.txt](examples/input.txt) 內容為 `2 3`；
[examples/expected.txt](examples/expected.txt) 的正確答案為 `5`。
專案中的 `hello.py` 已提供對應解答，可以直接執行上面的指令。

### 已附測資

[testcases/sum](testcases/sum/README.md) 提供 **12 組兩數相加測資**，每組包含輸入檔與正確答案檔。
涵蓋正數、零、負數、正負混合、相消、大數、32 位元整數邊界、分行與空白格式。

```powershell
python validator.py --input ".\testcases\sum\01_positive.input.txt" --expected ".\testcases\sum\01_positive.expected.txt"
```

資料夾說明中也提供跑完全部 12 組的 PowerShell 迴圈。
這些測資適用於 `hello.py` 範例的兩數相加規格；其他題目需要對應的題目規格與答案。

GitHub Actions 的 [hello.yml](.github/workflows/hello.yml) 會在 push 時逐筆驗證這 12 組測資；任何一組失敗都會讓工作流程失敗。

### 參數說明

查看完整參數：

```powershell
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
python -m unittest discover -s tests -v
```
