# 兩數相加測資

這 12 組測資對應專案的 hello.py 加法範例：每次讀取兩個整數 a、b，輸出 a + b。
每組的兩個輸入數值與答案均在 32 位元有號整數範圍內。
其他題目需要依該題目的規格另行產生測資。

每個 *.input.txt 是輸入測資，同名的 *.expected.txt 是正確答案。
每次執行使用一對檔案，檔案內不包含測資筆數。

## 合併成 JSON

在專案根目錄執行以下指令，將 `testcases` 下所有配對測資依路徑排序，合併為 [testcases.json](../testcases.json)：

```powershell
python scripts/merge_testcases.py
```

JSON 最外層是陣列，每一筆包含測資識別名稱、輸入與預期輸出，例如：

```json
[
  {
    "id": "sum/01_positive",
    "input": "2 3\n",
    "expected": "5\n"
  }
]
```

`input` 和 `expected` 保留原始換行、空格與 Tab（UTF-8 BOM 會移除）。
每筆仍是獨立測資，不會把所有輸入串成一次程式執行。
修改原始 `.txt` 後，請重新執行合併指令；缺少配對檔案或沒有測資時會回報錯誤。
可用 `--source` 指定來源資料夾、`--output` 指定輸出 JSON 路徑。
目前 validator 與 GitHub Actions 仍使用原本的 `.txt`；JSON 作為合併匯出檔。

## 執行原始測資

每個測資檔案的逐行內容、空格、Tab 與換行說明，請看 [測資逐行說明](../../docs/test-data-lines.md)。
下方表格每列對應一組輸入與答案檔；Markdown 的 `|` 用來分隔表格欄位。

| 編號 | 情境 | 正確答案 |
| --- | --- | --- |
| 01_positive | 2 + 3 | 5 |
| 02_zero | 0 + 0 | 0 |
| 03_zero_operand | 0 + 42 | 42 |
| 04_negative | -12 + -8 | -20 |
| 05_mixed_positive | -7 + 20 | 13 |
| 06_mixed_negative | 7 + -20 | -13 |
| 07_cancel | 123456789 + -123456789 | 0 |
| 08_large | 1000000000 + 1000000000 | 2000000000 |
| 09_int_max | 2147483646 + 1 | 2147483647 |
| 10_int_min | -2147483647 + -1 | -2147483648 |
| 11_separate_lines | 18、24 放在不同的行 | 42 |
| 12_whitespace | 18、24 之間使用 Tab，開頭含空格 | 42 |

將解答寫在專案的 hello.py，先依根目錄 README 編譯 validator.cpp，再在專案根目錄執行：

```powershell
# 在專案根目錄執行 validator，將第 01 組輸入送給 hello.py，再與該組答案比對。
.\validator.exe --input ".\testcases\sum\01_positive.input.txt" --expected ".\testcases\sum\01_positive.expected.txt"
```

一次跑完全部測資可使用 PowerShell 迴圈；每一筆都會個別啟動程式：

```powershell
# 建立計數變數，從零開始累計未通過的測資筆數。
$failedCount = 0
# 找出所有輸入檔，依檔名排序，再用管線 | 將每個檔案交給 ForEach-Object 的區塊處理。
Get-ChildItem -LiteralPath ".\testcases\sum" -Filter "*.input.txt" | Sort-Object Name | ForEach-Object {
    # $_ 是目前處理的檔案；用完整路徑替換副檔名，找出對應的答案檔。
    $expectedPath = $_.FullName.Replace(".input.txt", ".expected.txt")
    # 顯示目前檔名；$() 讓雙引號字串內的屬性存取先求值，再插入文字。
    Write-Host "測資：$($_.Name)"
    # 用目前輸入檔與配對答案啟動 validator；每組都會重新執行 hello.py。
    .\validator.exe --input $_.FullName --expected $expectedPath
    # $LASTEXITCODE 是剛執行程式的結束代碼；-ne 表示不等於，非零就將失敗數加一。
    if ($LASTEXITCODE -ne 0) { $failedCount += 1 }
} # 結束每個檔案要執行的區塊，直到所有輸入檔都處理完。
# 印出累計失敗筆數；這行只顯示數量，不會自行設定整段腳本的失敗結束代碼。
Write-Host "失敗筆數：$failedCount"
```
