"""請在這裡撰寫解答：從標準輸入讀取測資，將答案印到標準輸出。"""

# 匯入 sys 模組，使用標準輸入 sys.stdin 讀取資料。
import sys


# 定義主函式；此時只建立函式，呼叫 main() 才會執行內容。
def main():
    # read() 讀到輸入結束（EOF）；split() 按空白切開；map(int, ...) 轉成整數，再分別放入 a、b，必須恰好有兩個數字。
    a, b = map(int, sys.stdin.read().split())
    # 計算 a + b，將答案印到標準輸出，並在最後加上換行。
    print(a - b)


# 只有直接執行此檔案時才進入下方區塊；被其他檔案 import 時不執行。
if __name__ == "__main__":
    # 呼叫 main()，開始讀取輸入並計算答案。
    main()
