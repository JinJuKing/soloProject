import time
import msvcrt
import pyupbit


def select_ticker():
    coin = input("자동매매할 코인을 입력하세요 (BTC / ETH) : ").upper()

    if coin == "BTC":
        return "KRW-BTC"
    elif coin == "ETH":
        return "KRW-ETH"
    else:
        print("BTC 또는 ETH만 입력할 수 있습니다.")
        return None


def show_coin_info(ticker):
    current_price = pyupbit.get_current_price(ticker)
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)

    today_open = df.iloc[0]["open"]
    change_rate = ((current_price - today_open) / today_open) * 100

    print("\n===== 코인 정보 =====")
    print(f"대상: {ticker}")
    print(f"현재가: {current_price:,.0f}원")
    print(f"오늘 시가: {today_open:,.0f}원")
    print(f"오늘 변동률: {change_rate:.2f}%")
    print("====================\n")

    return current_price


def get_krw_balance(upbit):
    balances = upbit.get_balances()

    for item in balances:
        if item["currency"] == "KRW":
            return float(item["balance"])

    return 0


def auto_trade_test(upbit):
    ticker = select_ticker()

    if ticker is None:
        return

    current_price = show_coin_info(ticker)

    krw_balance = get_krw_balance(upbit)
    print(f"현재 보유 원화: {krw_balance:,.0f}원")

    buy_amount = float(input("매수 금액을 입력하세요: "))

    if buy_amount > krw_balance:
        print("매수 금액이 현재 보유 원화보다 큽니다.")
        return

    profit_percent = float(input("익절 퍼센트를 입력하세요 (예: 5): "))
    loss_percent = float(input("손절 퍼센트를 입력하세요 (예: 5): "))

    bought_price = current_price
    bought_volume = buy_amount / bought_price

    target_price = bought_price * (1 + profit_percent / 100)
    stop_loss_price = bought_price * (1 - loss_percent / 100)

    print("\n===== 자동매매 테스트 시작 =====")
    print(f"대상: {ticker}")
    print(f"가상 매수가: {bought_price:,.0f}원")
    print(f"가상 매수금액: {buy_amount:,.0f}원")
    print(f"가상 보유수량: {bought_volume:.8f}개")
    print(f"익절 기준가: {target_price:,.0f}원")
    print(f"손절 기준가: {stop_loss_price:,.0f}원")
    print("실제 주문은 하지 않는 테스트 모드입니다.")
    print("S = 즉시 가상매도 / 종료는 Ctrl + C")
    print("==============================\n")

    while True:
        current_price = pyupbit.get_current_price(ticker)

        profit = (current_price - bought_price) * bought_volume
        profit_rate = ((current_price - bought_price) / bought_price) * 100

        print(
            f"현재가: {current_price:,.0f}원 | "
            f"수익률: {profit_rate:.2f}% | "
            f"예상손익: {profit:,.0f}원 | "
            f"S=즉시매도 / 종료=Ctrl+C"
        )

        if current_price >= target_price:
            print("\n익절 기준 도달!")
            print(f"가상 매도가: {current_price:,.0f}원")
            print(f"예상 수익: {profit:,.0f}원")
            print(f"예상 수익률: {profit_rate:.2f}%")
            break

        if current_price <= stop_loss_price:
            print("\n손절 기준 도달!")
            print(f"가상 매도가: {current_price:,.0f}원")
            print(f"예상 손익: {profit:,.0f}원")
            print(f"예상 수익률: {profit_rate:.2f}%")
            break

        for _ in range(50):
            if msvcrt.kbhit():
                key = msvcrt.getch().decode().upper()

                if key == "S":
                    print("\n즉시 가상매도 실행!")
                    print(f"가상 매도가: {current_price:,.0f}원")
                    print(f"예상 손익: {profit:,.0f}원")
                    print(f"예상 수익률: {profit_rate:.2f}%")
                    return

            time.sleep(0.1)