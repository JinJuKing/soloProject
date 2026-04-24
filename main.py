import pyupbit

price = pyupbit.get_current_price("KRW-BTC")
print("현재 비트코인 가격:", price)