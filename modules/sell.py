def sell_by_percent(upbit):
    coin = input("어떤 코인을 매도할까요? (BTC / ETH) : ").upper()

    if coin == "BTC":
        ticker = "KRW-BTC"
    elif coin == "ETH":
        ticker = "KRW-ETH"
    else:
        print("BTC 또는 ETH만 입력 가능합니다.")
        return

    percent = float(input("몇 % 매도할까요? (25 / 50 / 100) : "))

    balances = upbit.get_balances()
    my_balance = 0

    for item in balances:
        if item["currency"] == coin:
            my_balance = float(item["balance"])
            break

    if my_balance == 0:
        print(f"{coin} 보유 수량이 없습니다.")
        return

    volume = my_balance * (percent / 100)

    print(f"\n보유수량: {my_balance:.8f} {coin}")
    print(f"{percent:.0f}% 매도 수량: {volume:.8f} {coin}")

    result = upbit.sell_market_order(ticker, volume)

    if "error" in result:
        print("\n===== 매도 실패 =====")
        print(f"오류명: {result['error'].get('name')}")
        print(f"메시지: {result['error'].get('message')}")
        print("====================\n")
        return result

    print("\n===== 매도 주문 결과 =====")
    print(f"마켓: {result['market']}")
    print("주문구분: 매도")
    print(f"매도비율: {percent:.0f}%")
    print(f"매도수량: {volume:.8f}")
    print(f"주문상태: {result['state']}")
    print(f"주문번호: {result['uuid']}")
    print("========================\n")

    return result