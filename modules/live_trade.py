import os
import time
from datetime import datetime

import pyupbit
from dotenv import load_dotenv


def get_upbit_client(access=None, secret=None):
    if not access or not secret:
        load_dotenv()
        access = access or os.getenv("UPBIT_ACCESS_KEY")
        secret = secret or os.getenv("UPBIT_SECRET_KEY")

    if not access or not secret:
        return None

    return pyupbit.Upbit(access, secret)


def coin_currency(ticker):
    return ticker.replace("KRW-", "")


def get_balance(upbit, currency):
    if upbit is None:
        return 0.0

    balance = upbit.get_balance(currency)
    if balance is None:
        return 0.0

    return float(balance)


def get_account_snapshot(upbit, ticker):
    currency = coin_currency(ticker)
    return {
        "krw": get_balance(upbit, "KRW"),
        "coin": get_balance(upbit, currency),
        "currency": currency,
    }


def place_market_buy(upbit, ticker, amount):
    currency = coin_currency(ticker)
    before_volume = get_balance(upbit, currency)
    result = upbit.buy_market_order(ticker, amount)

    if isinstance(result, dict) and "error" in result:
        return result, 0.0

    time.sleep(1)
    after_volume = get_balance(upbit, currency)
    bought_volume = max(after_volume - before_volume, 0.0)

    if bought_volume == 0 and isinstance(result, dict):
        try:
            bought_volume = float(result.get("executed_volume") or 0)
        except (TypeError, ValueError):
            bought_volume = 0.0

    return result, bought_volume


def place_market_sell(upbit, ticker, volume):
    currency = coin_currency(ticker)
    available_volume = get_balance(upbit, currency)
    sell_volume = min(volume, available_volume)

    if sell_volume <= 0:
        return {"error": {"name": "invalid_volume", "message": "매도 수량이 없습니다."}}

    return upbit.sell_market_order(ticker, sell_volume)


def build_live_position(ticker, entry_price, amount, volume, target_percent, stop_percent):
    return {
        "ticker": ticker,
        "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "buy_price": entry_price,
        "amount": amount,
        "volume": volume,
        "target_percent": target_percent,
        "stop_percent": stop_percent,
        "target_price": entry_price * (1 + target_percent / 100),
        "stop_price": entry_price * (1 - stop_percent / 100),
        "direction": "LONG",
        "direction_label": "실거래 롱",
        "mode": "LIVE",
    }


def calculate_recommendation(history):
    if history is None or history.empty or len(history) < 10:
        return 1.0, 0.7, "데이터 부족으로 보수적인 기본값을 사용했습니다."

    returns = history["현재가"].pct_change().dropna().abs()
    recent_volatility = float(returns.tail(30).mean() * 100)

    target_percent = min(max(recent_volatility * 4, 0.5), 3.0)
    stop_percent = min(max(recent_volatility * 2.5, 0.3), 2.0)
    message = "최근 1분봉 변동성을 기준으로 계산한 참고값입니다. 수익을 보장하지 않습니다."
    return round(target_percent, 2), round(stop_percent, 2), message
