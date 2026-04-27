import pandas as pd
import pyupbit
import requests
import streamlit as st

from modules.formatting import make_coin_label


UPBIT_API_URL = "https://api.upbit.com/v1"

COIN_OPTIONS = {
    "비트코인 (BTC)": "KRW-BTC",
    "이더리움 (ETH)": "KRW-ETH",
    "리플 (XRP)": "KRW-XRP",
    "솔라나 (SOL)": "KRW-SOL",
    "도지코인 (DOGE)": "KRW-DOGE",
}


@st.cache_data(ttl=60)
def get_krw_market_names():
    response = requests.get(
        f"{UPBIT_API_URL}/market/all",
        params={"isDetails": "false"},
        timeout=10,
    )
    response.raise_for_status()

    markets = response.json()
    return {
        item["market"]: item["korean_name"]
        for item in markets
        if item["market"].startswith("KRW-")
    }


@st.cache_data(ttl=5)
def get_top_movers(limit=3):
    names = get_krw_market_names()
    tickers = list(names.keys())
    rows = []

    for index in range(0, len(tickers), 100):
        chunk = tickers[index : index + 100]
        response = requests.get(
            f"{UPBIT_API_URL}/ticker",
            params={"markets": ",".join(chunk)},
            timeout=10,
        )
        response.raise_for_status()
        rows.extend(response.json())

    movers = pd.DataFrame(
        [
            {
                "코인": make_coin_label(names[item["market"]], item["market"]),
                "마켓": item["market"],
                "현재가": item["trade_price"],
                "전일대비": item["signed_change_rate"] * 100,
                "변동금액": item["signed_change_price"],
            }
            for item in rows
        ]
    )

    gainers = movers.sort_values("전일대비", ascending=False).head(limit).copy()
    losers = movers.sort_values("전일대비", ascending=True).head(limit).copy()
    return gainers, losers


def get_current_price(ticker):
    price = pyupbit.get_current_price(ticker)
    if price is None:
        raise RuntimeError("현재가를 가져오지 못했습니다.")
    return float(price)


def get_price_history(ticker, count):
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=count)
    if df is None or df.empty:
        return pd.DataFrame()

    chart_df = df[["open", "high", "low", "close", "volume"]].rename(
        columns={
            "open": "시가",
            "high": "고가",
            "low": "저가",
            "close": "현재가",
            "volume": "거래량",
        }
    )
    chart_df.index.name = "시간"
    return chart_df
