# soloProject 메인 실행 파일

import os
from dotenv import load_dotenv
import pyupbit

from modules.buy import buy_test
from modules.sell import sell_test
from modules.check import check_balance

load_dotenv()

access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")

upbit = pyupbit.Upbit(access, secret)

# 잔고 출력은 check.py 담당
check_balance(upbit)

buy_test()
sell_test()