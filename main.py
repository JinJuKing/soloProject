# soloProject 메인 실행 파일

import os
from dotenv import load_dotenv
import pyupbit

from modules.buy import buy_market
from modules.sell import sell_by_percent
from modules.check import check_balance

load_dotenv()

access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")

upbit = pyupbit.Upbit(access, secret)

print("===== soloProject =====")
print("1. 지갑 내용 확인")
print("2. 매수하기")
print("3. 매도하기")
print("=======================")

choice = input("원하는 작업을 선택하세요 (1 / 2 / 3) : ")

if choice == "1":
    check_balance(upbit)

elif choice == "2":
    check_balance(upbit)
    buy_market(upbit)
    check_balance(upbit)

elif choice == "3":
    check_balance(upbit)
    sell_by_percent(upbit)
    check_balance(upbit)

else:
    print("잘못 입력했습니다. 1, 2, 3 중에서 선택하세요.")