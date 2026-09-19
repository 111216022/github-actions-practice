"""請在這裡撰寫解答：從標準輸入讀取測資，將答案印到標準輸出。"""

import sys


def main():
    a, b = map(int, sys.stdin.read().split())
    print(a + b)


if __name__ == "__main__":
    main()
