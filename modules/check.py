import pyupbit

def check_balance(upbit):
    balances = upbit.get_balances()
    total_money = 0

    print("===== 현재 보유 자산 =====")

    for coin in balances:
        currency = coin["currency"]
        balance = float(coin["balance"])

        if currency == "KRW":
            money = balance

        else:
            ticker = f"KRW-{currency}"

            try:
                price = pyupbit.get_current_price(ticker)

                if price is None:
                    money = 0
                else:
                    money = balance * price

            except:
                money = 0

        total_money += money
        print(f"{currency} : {money:,.0f}원")

    print("=======================")
    print(f"총 보유 자산 : {total_money:,.0f}원")