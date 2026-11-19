# 加密測資

`testcases/testcases.json` 可以加密成 `testcases/testcases.json.enc`。
ECDH 是金鑰協商演算法：此工具使用 P-256 ECDH，經 HKDF-SHA256 衍生
32 bytes 金鑰，再以 AES-256-GCM 加密並驗證完整性。
參考 [ECDH 官方文件](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ec/)
與 [AES-GCM 官方文件](https://cryptography.io/en/latest/hazmat/primitives/aead/)。

## 安裝與產生金鑰

在專案根目錄執行（Windows PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/crypto_testcases.py keygen
```

公鑰為 `keys/public_key.pem`，私鑰為 `keys/private_key.pem`。
已有金鑰時 `keygen` 會拒絕覆寫，避免舊密文無法解密。
目前這組私鑰也直接寫在 `validator.cpp` 的 `EMBEDDED_PRIVATE_KEY` 常數中，
編譯後不需要額外的私鑰檔即可解密。原始私鑰檔未設密碼，已加入 `.gitignore`；
但這不會隱藏 C++ 原始碼與執行檔中的內嵌私鑰。
自訂私鑰位置時，也應自行排除 Git 追蹤。

## 合併、加密與驗證

```powershell
.\.venv\Scripts\python.exe scripts/merge_testcases.py
.\.venv\Scripts\python.exe scripts/crypto_testcases.py encrypt --input testcases/testcases.json --output testcases/testcases.json.enc --public-key keys/public_key.pem
$env:PATH = "C:\msys64\ucrt64\bin;" + $env:PATH
g++ -std=c++17 -O2 -Wall -Wextra -pedantic -static validator.cpp -o validator.exe
.\validator.exe --testcases testcases/testcases.json.enc --python .venv/Scripts/python.exe --timeout 5
```

Linux 使用 `.venv/bin/python` 與 `./validator`，編譯輸出改為 `-o validator`。

預設使用 C++ 內嵌私鑰；加上 `--private-key keys/other_private_key.pem` 可改用其他私鑰。
明確指定的私鑰檔若不存在或無法解密，會回報錯誤，不會退回使用內嵌私鑰。
若更換公私鑰，需同步更新 C++ 的 `EMBEDDED_PRIVATE_KEY` PEM 內容、重新編譯，
並以新公鑰重新加密測資；單獨產生新金鑰不會自動更新內嵌常數。

validator 會呼叫執行檔旁的 `scripts/crypto_testcases.py`，使用指定的 Python
完成解密與 JSON 解析，再交回 C++ 逐筆執行 `hello.py`，不產生明文 JSON 檔。
私鑰 PEM 透過工具的標準輸入傳遞，不放在命令列參數中，也不另存私鑰檔。
部署時需一起提供該 Python 工具並安裝 `requirements.txt`。
每組測資各有 `--timeout` 秒上限；解密工具另有 30 秒上限。
錯誤私鑰、竄改或格式不合法的測資會在執行 `hello.py` 前回傳 2。
全部通過回傳 0；任一組錯誤或逾時回傳 1，仍繼續測試後續組別。
原本的 `--input` / `--expected` 模式仍可使用，不能與 `--testcases` 混用。

需要匯出明文時，可另外執行：

```powershell
.\.venv\Scripts\python.exe scripts/crypto_testcases.py decrypt --input testcases/testcases.json.enc --output testcases/decrypted.json --private-key keys/private_key.pem
```

## 密文格式與保密範圍

`.enc` 是二進位檔，依序包含版本標頭 `TESTCASES-ENC-v1\0`、65 bytes
暫時性公鑰、32 bytes 隨機 salt、12 bytes 隨機 nonce，以及含 16 bytes
驗證標籤的 AES-GCM 密文。整個標頭也納入完整性驗證。
每次加密都產生新的暫時性私鑰、salt、nonce；只有接收者公鑰會重複使用。

目前原始 `.txt` 與 `testcases.json` 仍留在專案中，因此這是加解密流程示範，
不會隱藏已公開的測資。內嵌私鑰可從原始碼或執行檔取得，適合方便執行的示範用途，
不能對拿到程式的人保護測資。執行 `hello.py` 沒有沙箱隔離，與 validator 同權限的程式
可能讀取私鑰；不能用此流程防止不可信的受測程式取得秘密。
公鑰加密也不代表驗證寄件者身份，持有公鑰的人都能產生新的有效密文。

CI 安裝加密套件，用臨時金鑰驗證指定私鑰模式，也以 `keys/public_key.pem`
產生密文驗證內嵌私鑰模式。現有正式測資步驟仍使用 `.txt`。
