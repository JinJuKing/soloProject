# soloProject 메인 실행 파일
# 환경변수(.env)에서 API 키를 읽고 업비트 연결 후 잔고 조회

import os
from dotenv import load_dotenv
import pyupbit

# modules 폴더 기능 가져오기
from modules.buy import buy_test
from modules.sell import sell_test

# .env 파일 불러오기
load_dotenv()

# API 키 읽기
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")

# 업비트 로그인 객체 생성
upbit = pyupbit.Upbit(access, secret)

# 잔고 조회
balances = upbit.get_balances()
print("현재 잔고:", balances)

# 테스트 함수 실행
buy_test()
sell_test()