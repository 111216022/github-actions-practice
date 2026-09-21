# 測資逐行說明

本頁列出專案所有 26 個 `.txt` 檔案的每一行。它們是程式讀取的資料，不能直接插入註解，否則會改變測試結果。

內容欄使用字串表示法：雙引號用來標示範圍，不是檔案內容；`\n` 代表 LF 換行、`\r\n` 代表 CRLF 換行、`\t` 代表 Tab。引號內的空格也屬於實際資料。

輸入檔提供兩個整數，`split()` 會以空格、Tab 或換行分隔它們。答案檔是預期的總和；validator 會統一換行格式，並忽略最多一個結尾換行。

| 檔案 | 行號 | 原始內容（含換行） | 這一行的用途 |
| --- | --- | --- | --- |
| [examples/expected.txt](../examples/expected.txt) | 1 | `"5\n"` | 預期答案為 5，用來比對 hello.py 的標準輸出。 |
| [examples/input.txt](../examples/input.txt) | 1 | `"2 3\n"` | 提供第一個整數 a = 2 與第二個整數 b = 3。 |
| [testcases/sum/01_positive.expected.txt](../testcases/sum/01_positive.expected.txt) | 1 | `"5\n"` | 預期答案為 5，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/01_positive.input.txt](../testcases/sum/01_positive.input.txt) | 1 | `"2 3\n"` | 提供第一個整數 a = 2 與第二個整數 b = 3。 |
| [testcases/sum/02_zero.expected.txt](../testcases/sum/02_zero.expected.txt) | 1 | `"0\n"` | 預期答案為 0，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/02_zero.input.txt](../testcases/sum/02_zero.input.txt) | 1 | `"0 0\n"` | 提供第一個整數 a = 0 與第二個整數 b = 0。 |
| [testcases/sum/03_zero_operand.expected.txt](../testcases/sum/03_zero_operand.expected.txt) | 1 | `"42\n"` | 預期答案為 42，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/03_zero_operand.input.txt](../testcases/sum/03_zero_operand.input.txt) | 1 | `"0 42\n"` | 提供第一個整數 a = 0 與第二個整數 b = 42。 |
| [testcases/sum/04_negative.expected.txt](../testcases/sum/04_negative.expected.txt) | 1 | `"-20\n"` | 預期答案為 -20，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/04_negative.input.txt](../testcases/sum/04_negative.input.txt) | 1 | `"-12 -8\n"` | 提供第一個整數 a = -12 與第二個整數 b = -8。 |
| [testcases/sum/05_mixed_positive.expected.txt](../testcases/sum/05_mixed_positive.expected.txt) | 1 | `"13\n"` | 預期答案為 13，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/05_mixed_positive.input.txt](../testcases/sum/05_mixed_positive.input.txt) | 1 | `"-7 20\n"` | 提供第一個整數 a = -7 與第二個整數 b = 20。 |
| [testcases/sum/06_mixed_negative.expected.txt](../testcases/sum/06_mixed_negative.expected.txt) | 1 | `"-13\n"` | 預期答案為 -13，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/06_mixed_negative.input.txt](../testcases/sum/06_mixed_negative.input.txt) | 1 | `"7 -20\n"` | 提供第一個整數 a = 7 與第二個整數 b = -20。 |
| [testcases/sum/07_cancel.expected.txt](../testcases/sum/07_cancel.expected.txt) | 1 | `"0\n"` | 預期答案為 0，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/07_cancel.input.txt](../testcases/sum/07_cancel.input.txt) | 1 | `"123456789 -123456789\n"` | 提供第一個整數 a = 123456789 與第二個整數 b = -123456789。 |
| [testcases/sum/08_large.expected.txt](../testcases/sum/08_large.expected.txt) | 1 | `"2000000000\n"` | 預期答案為 2000000000，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/08_large.input.txt](../testcases/sum/08_large.input.txt) | 1 | `"1000000000 1000000000\n"` | 提供第一個整數 a = 1000000000 與第二個整數 b = 1000000000。 |
| [testcases/sum/09_int_max.expected.txt](../testcases/sum/09_int_max.expected.txt) | 1 | `"2147483647\n"` | 預期答案為 2147483647，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/09_int_max.input.txt](../testcases/sum/09_int_max.input.txt) | 1 | `"2147483646 1\n"` | 提供第一個整數 a = 2147483646 與第二個整數 b = 1。 |
| [testcases/sum/10_int_min.expected.txt](../testcases/sum/10_int_min.expected.txt) | 1 | `"-2147483648\n"` | 預期答案為 -2147483648，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/10_int_min.input.txt](../testcases/sum/10_int_min.input.txt) | 1 | `"-2147483647 -1\n"` | 提供第一個整數 a = -2147483647 與第二個整數 b = -1。 |
| [testcases/sum/11_separate_lines.expected.txt](../testcases/sum/11_separate_lines.expected.txt) | 1 | `"42\n"` | 預期答案為 42，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/11_separate_lines.input.txt](../testcases/sum/11_separate_lines.input.txt) | 1 | `"18\n"` | 提供整數 a = 18；另一個整數放在另一行，測試分行輸入。 |
| [testcases/sum/11_separate_lines.input.txt](../testcases/sum/11_separate_lines.input.txt) | 2 | `"24\n"` | 提供整數 b = 24；另一個整數放在另一行，測試分行輸入。 |
| [testcases/sum/12_whitespace.expected.txt](../testcases/sum/12_whitespace.expected.txt) | 1 | `"42\n"` | 預期答案為 42，用來比對 hello.py 的標準輸出。 |
| [testcases/sum/12_whitespace.input.txt](../testcases/sum/12_whitespace.input.txt) | 1 | `"  18\t24\n"` | 提供第一個整數 a = 18 與第二個整數 b = 24。開頭有兩個空格，兩數之間用 Tab 分隔，測試空白解析。 |
