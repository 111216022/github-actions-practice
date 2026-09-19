# 兩數相加測資

這 12 組測資對應專案的 hello.py 加法範例：每次讀取兩個整數 a、b，輸出 a + b。
每組的兩個輸入數值與答案均在 32 位元有號整數範圍內。
其他題目需要依該題目的規格另行產生測資。

每個 *.input.txt 是輸入測資，同名的 *.expected.txt 是正確答案。
每次執行使用一對檔案，檔案內不包含測資筆數。

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

將解答寫在專案的 hello.py，然後在專案根目錄執行：

```powershell
python validator.py --input ".\testcases\sum\01_positive.input.txt" --expected ".\testcases\sum\01_positive.expected.txt"
```

一次跑完全部測資可使用 PowerShell 迴圈；每一筆都會個別啟動程式：

```powershell
$failedCount = 0
Get-ChildItem -LiteralPath ".\testcases\sum" -Filter "*.input.txt" | Sort-Object Name | ForEach-Object {
    $expectedPath = $_.FullName.Replace(".input.txt", ".expected.txt")
    Write-Host "測資：$($_.Name)"
    python validator.py --input $_.FullName --expected $expectedPath
    if ($LASTEXITCODE -ne 0) { $failedCount += 1 }
}
Write-Host "失敗筆數：$failedCount"
```
