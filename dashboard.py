from datetime import datetime
from pathlib import Path

import pandas as pd
import pyupbit
import streamlit as st


TRADE_LOG_PATH = Path("data/trades.csv")
COINS = {
    "BTC": "KRW-BTC",
    "ETH": "KRW-ETH",
    "XRP": "KRW-XRP",
    "SOL": "KRW-SOL",
    "DOGE": "KRW-DOGE",
}


def format_krw(value):
    return f"{value:,.0f}원"


def format_percent(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def get_current_price(ticker):
    price = pyupbit.get_current_price(ticker)
    if price is None:
        raise RuntimeError("현재가를 가져오지 못했습니다.")
    return float(price)


def get_price_history(ticker, count):
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=count)
    if df is None or df.empty:
        return pd.DataFrame()

    chart_df = df[["close"]].rename(columns={"close": "현재가"})
    chart_df.index.name = "시간"
    return chart_df


def ensure_trade_log():
    TRADE_LOG_PATH.parent.mkdir(exist_ok=True)
    if not TRADE_LOG_PATH.exists():
        pd.DataFrame(
            columns=[
                "time",
                "ticker",
                "side",
                "reason",
                "price",
                "amount",
                "volume",
                "profit",
                "profit_rate",
            ]
        ).to_csv(TRADE_LOG_PATH, index=False, encoding="utf-8-sig")


def load_trade_log():
    ensure_trade_log()
    return pd.read_csv(TRADE_LOG_PATH)


def append_trade_log(row):
    ensure_trade_log()
    log = load_trade_log()
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    log.to_csv(TRADE_LOG_PATH, index=False, encoding="utf-8-sig")


def reset_position():
    st.session_state.position = None


def buy_virtual_position(ticker, price, amount, target_percent, stop_percent):
    volume = amount / price
    st.session_state.position = {
        "ticker": ticker,
        "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "buy_price": price,
        "amount": amount,
        "volume": volume,
        "target_percent": target_percent,
        "stop_percent": stop_percent,
        "target_price": price * (1 + target_percent / 100),
        "stop_price": price * (1 - stop_percent / 100),
    }
    append_trade_log(
        {
            "time": st.session_state.position["buy_time"],
            "ticker": ticker,
            "side": "BUY",
            "reason": "가상매수",
            "price": price,
            "amount": amount,
            "volume": volume,
            "profit": 0,
            "profit_rate": 0,
        }
    )


def sell_virtual_position(price, reason):
    position = st.session_state.position
    if position is None:
        return

    profit = (price - position["buy_price"]) * position["volume"]
    profit_rate = ((price - position["buy_price"]) / position["buy_price"]) * 100
    append_trade_log(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticker": position["ticker"],
            "side": "SELL",
            "reason": reason,
            "price": price,
            "amount": position["amount"] + profit,
            "volume": position["volume"],
            "profit": profit,
            "profit_rate": profit_rate,
        }
    )
    reset_position()


def show_position(current_price):
    position = st.session_state.position
    if position is None:
        st.info("아직 가상 보유 중인 코인이 없습니다.")
        return

    profit = (current_price - position["buy_price"]) * position["volume"]
    profit_rate = ((current_price - position["buy_price"]) / position["buy_price"]) * 100

    cols = st.columns(4)
    cols[0].metric("가상 매수가", format_krw(position["buy_price"]))
    cols[1].metric("보유 수량", f"{position['volume']:.8f}")
    cols[2].metric("예상 손익", format_krw(profit), format_percent(profit_rate))
    cols[3].metric("매수 시간", position["buy_time"])

    target_hit = current_price >= position["target_price"]
    stop_hit = current_price <= position["stop_price"]

    st.progress(
        min(
            max(
                (current_price - position["stop_price"])
                / (position["target_price"] - position["stop_price"]),
                0,
            ),
            1,
        )
    )

    cols = st.columns(3)
    cols[0].write(f"익절가: **{format_krw(position['target_price'])}**")
    cols[1].write(f"손절가: **{format_krw(position['stop_price'])}**")
    cols[2].write(f"상태: **{'익절 도달' if target_hit else '손절 도달' if stop_hit else '진행 중'}**")

    if target_hit:
        sell_virtual_position(current_price, "익절")
        st.success("익절 기준에 도달해서 가상 매도 기록을 남겼습니다.")
        st.rerun()

    if stop_hit:
        sell_virtual_position(current_price, "손절")
        st.warning("손절 기준에 도달해서 가상 매도 기록을 남겼습니다.")
        st.rerun()


def main():
    st.set_page_config(page_title="가상 자동매매 대시보드", layout="wide")
    st.title("가상 자동매매 대시보드")

    if "position" not in st.session_state:
        reset_position()

    with st.sidebar:
        st.header("설정")
        coin = st.selectbox("코인", list(COINS.keys()))
        ticker = COINS[coin]
        buy_amount = st.number_input("가상 매수 금액", min_value=1000, value=10000, step=1000)
        target_percent = st.number_input("익절 퍼센트", min_value=0.1, value=3.0, step=0.1)
        stop_percent = st.number_input("손절 퍼센트", min_value=0.1, value=2.0, step=0.1)
        chart_count = st.slider("차트 길이(분)", min_value=30, max_value=240, value=120, step=30)

    try:
        current_price = get_current_price(ticker)
    except Exception as exc:
        st.error(f"가격 조회 실패: {exc}")
        return

    top_cols = st.columns(4)
    top_cols[0].metric("선택 코인", ticker)
    top_cols[1].metric("현재가", format_krw(current_price))

    history = get_price_history(ticker, chart_count)
    if not history.empty:
        open_price = float(history["현재가"].iloc[0])
        change_rate = ((current_price - open_price) / open_price) * 100
        top_cols[2].metric("차트 기준 변동률", format_percent(change_rate))
        top_cols[3].metric("조회 구간", f"{chart_count}분")
    else:
        top_cols[2].metric("차트 기준 변동률", "-")
        top_cols[3].metric("조회 구간", f"{chart_count}분")

    st.divider()

    left, right = st.columns([2, 1])

    with left:
        st.subheader("가격 차트")
        if history.empty:
            st.warning("차트 데이터를 가져오지 못했습니다.")
        else:
            chart_data = history.copy()
            position = st.session_state.position
            if position and position["ticker"] == ticker:
                chart_data["가상 매수가"] = position["buy_price"]
                chart_data["익절가"] = position["target_price"]
                chart_data["손절가"] = position["stop_price"]
            st.line_chart(chart_data)

    with right:
        st.subheader("가상 포지션")
        show_position(current_price)

        position = st.session_state.position
        buy_disabled = position is not None
        sell_disabled = position is None

        if st.button("가상 매수", disabled=buy_disabled, use_container_width=True):
            buy_virtual_position(ticker, current_price, buy_amount, target_percent, stop_percent)
            st.success("가상 매수 기록을 남겼습니다.")
            st.rerun()

        if st.button("즉시 가상 매도", disabled=sell_disabled, use_container_width=True):
            sell_virtual_position(current_price, "수동매도")
            st.success("즉시 가상 매도 기록을 남겼습니다.")
            st.rerun()

    st.divider()

    st.subheader("거래 기록")
    log = load_trade_log()
    if log.empty:
        st.caption("거래 기록이 아직 없습니다.")
    else:
        view = log.tail(30).copy()
        for column in ["price", "amount", "profit"]:
            view[column] = view[column].map(lambda value: format_krw(float(value)))
        view["profit_rate"] = view["profit_rate"].map(lambda value: format_percent(float(value)))
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.caption("이 화면은 가상매매 전용입니다. 실제 매수/매도 주문은 실행하지 않습니다.")


if __name__ == "__main__":
    main()
