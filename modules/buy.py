def buy_market(upbit):
    coin = input("원하는 코인을 입력하세요 (BTC / ETH) : ").upper()

    if coin == "BTC":
        ticker = "KRW-BTC"
    elif coin == "ETH":
        ticker = "KRW-ETH"
    else:
        print("BTC 또는 ETH만 입력할 수 있습니다.")
        return

    amount = float(input("얼마 매수할까요? : "))

    print(f"\n{ticker} {amount:,.0f}원 시장가 매수 시도")

    result = upbit.buy_market_order(ticker, amount)

    if "error" in result:
        print("\n===== 매수 실패 =====")
        print(f"오류명: {result['error'].get('name')}")
        print(f"메시지: {result['error'].get('message')}")
        print("====================\n")
        return result

    print("\n===== 매수 주문 결과 =====")
    print(f"마켓: {result['market']}")
    print("주문구분: 매수")
    print("주문방식: 시장가")
    print(f"주문금액: {float(result['price']):,.0f}원")
    print(f"예약수수료: {float(result['reserved_fee']):,.0f}원")
    print(f"주문상태: {result['state']}")
    print(f"체결수량: {result['executed_volume']}")
    print(f"체결횟수: {result['trades_count']}회")
    print(f"주문번호: {result['uuid']}")
    print("========================\n")

    return result