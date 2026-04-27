from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pyupbit
import requests
import streamlit as st


TRADE_LOG_PATH = Path("data/trades.csv")
COIN_OPTIONS = {
    "비트코인 (BTC)": "KRW-BTC",
    "이더리움 (ETH)": "KRW-ETH",
    "리플 (XRP)": "KRW-XRP",
    "솔라나 (SOL)": "KRW-SOL",
    "도지코인 (DOGE)": "KRW-DOGE",
}
UPBIT_API_URL = "https://api.upbit.com/v1"


def format_krw(value):
    value = float(value)
    if value >= 1000 or value.is_integer():
        return f"{value:,.0f}원"
    if value >= 1:
        return f"{value:,.2f}".rstrip("0").rstrip(".") + "원"
    return f"{value:,.4f}".rstrip("0").rstrip(".") + "원"


def format_percent(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def ticker_symbol(ticker):
    return ticker.replace("KRW-", "")


def make_coin_label(korean_name, ticker):
    return f"{korean_name} ({ticker_symbol(ticker)})"


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


def add_current_price_to_history(history, current_price):
    now = pd.Timestamp.now()
    current_row = pd.DataFrame({"현재가": [current_price]}, index=[now])
    current_row.index.name = "시간"

    if history.empty:
        return current_row

    return pd.concat([history, current_row])


def update_live_price_history(ticker, current_price):
    live_prices_by_ticker = st.session_state.setdefault("live_prices_by_ticker", {})
    live_prices = live_prices_by_ticker.setdefault(ticker, [])
    live_prices.append(
        {
            "time": pd.Timestamp.now(),
            "price": current_price,
        }
    )
    live_prices_by_ticker[ticker] = live_prices[-120:]
    st.session_state.live_prices_by_ticker = live_prices_by_ticker

    live_df = pd.DataFrame(live_prices_by_ticker[ticker])
    if live_df.empty:
        return pd.DataFrame()

    live_df = live_df.set_index("time").rename(columns={"price": "실시간 현재가"})
    live_df.index.name = "시간"
    return live_df


def build_candle_chart(history, current_price, position=None):
    chart_data = history.copy()
    if chart_data.empty:
        return None

    last_index = chart_data.index[-1]
    chart_data.loc[last_index, "현재가"] = current_price
    chart_data.loc[last_index, "고가"] = max(float(chart_data.loc[last_index, "고가"]), current_price)
    chart_data.loc[last_index, "저가"] = min(float(chart_data.loc[last_index, "저가"]), current_price)

    increasing_color = "#ef4444"
    decreasing_color = "#2563eb"
    volume_colors = [
        increasing_color if close_price >= open_price else decreasing_color
        for open_price, close_price in zip(chart_data["시가"], chart_data["현재가"])
    ]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.76, 0.24],
    )
    fig.add_trace(
        go.Candlestick(
            x=chart_data.index,
            open=chart_data["시가"],
            high=chart_data["고가"],
            low=chart_data["저가"],
            close=chart_data["현재가"],
            increasing_line_color=increasing_color,
            increasing_fillcolor=increasing_color,
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=decreasing_color,
            name="가격",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=chart_data.index,
            y=chart_data["거래량"],
            marker_color=volume_colors,
            opacity=0.45,
            name="거래량",
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=current_price,
        line_dash="dot",
        line_color=increasing_color,
        annotation_text=f"현재가 {format_krw(current_price)}",
        annotation_position="right",
        row=1,
        col=1,
    )

    if position:
        line_specs = [
            ("가상 진입가", position["buy_price"], "#64748b"),
            ("목표가", position["target_price"], "#16a34a"),
            ("손절가", position["stop_price"], "#f97316"),
        ]
        for label, price, color in line_specs:
            fig.add_hline(
                y=price,
                line_dash="dash",
                line_color=color,
                annotation_text=f"{label} {format_krw(price)}",
                annotation_position="right",
                row=1,
                col=1,
            )

    fig.update_layout(
        height=560,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#e5e7eb",
        zeroline=False,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#e5e7eb",
        zeroline=False,
        tickformat=",",
        row=1,
        col=1,
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        tickformat=",.0f",
        row=2,
        col=1,
    )
    return fig


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


def clear_selected_mover():
    st.session_state.pop("selected_mover_label", None)
    st.session_state.pop("selected_mover_ticker", None)
    st.session_state.pop("selected_mover_source", None)


def get_position_prices(price, target_percent, stop_percent, direction):
    if direction == "SHORT":
        return price * (1 - target_percent / 100), price * (1 + stop_percent / 100)

    return price * (1 + target_percent / 100), price * (1 - stop_percent / 100)


def calculate_position_profit(position, current_price):
    if position.get("direction") == "SHORT":
        profit = (position["buy_price"] - current_price) * position["volume"]
        profit_rate = ((position["buy_price"] - current_price) / position["buy_price"]) * 100
        return profit, profit_rate

    profit = (current_price - position["buy_price"]) * position["volume"]
    profit_rate = ((current_price - position["buy_price"]) / position["buy_price"]) * 100
    return profit, profit_rate


def is_position_target_hit(position, current_price):
    if position.get("direction") == "SHORT":
        return current_price <= position["target_price"]

    return current_price >= position["target_price"]


def is_position_stop_hit(position, current_price):
    if position.get("direction") == "SHORT":
        return current_price >= position["stop_price"]

    return current_price <= position["stop_price"]


def open_virtual_position(ticker, price, amount, direction, target_percent, stop_percent, reason_label):
    volume = amount / price
    target_price, stop_price = get_position_prices(price, target_percent, stop_percent, direction)
    direction_label = "숏 가상" if direction == "SHORT" else "롱 가상"

    st.session_state.position = {
        "ticker": ticker,
        "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "buy_price": price,
        "amount": amount,
        "volume": volume,
        "target_percent": target_percent,
        "stop_percent": stop_percent,
        "direction": direction,
        "direction_label": direction_label,
        "target_price": target_price,
        "stop_price": stop_price,
    }
    append_trade_log(
        {
            "time": st.session_state.position["buy_time"],
            "ticker": ticker,
            "side": "SHORT" if direction == "SHORT" else "LONG",
            "reason": f"{reason_label} 진입",
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

    profit, profit_rate = calculate_position_profit(position, price)
    append_trade_log(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticker": position["ticker"],
            "side": "CLOSE_SHORT" if position.get("direction") == "SHORT" else "CLOSE_LONG",
            "reason": reason,
            "price": price,
            "amount": position["amount"] + profit,
            "volume": position["volume"],
            "profit": profit,
            "profit_rate": profit_rate,
        }
    )
    reset_position()


def show_position(current_price, ticker):
    position = st.session_state.position
    if position is None:
        st.info("아직 가상 보유 중인 코인이 없습니다.")
        return

    if position["ticker"] != ticker:
        st.info(f"다른 코인 포지션이 진행 중입니다: {position['ticker']}")
        return

    profit, profit_rate = calculate_position_profit(position, current_price)
    direction_label = position.get("direction_label", "가상 롱")

    cols = st.columns(4)
    cols[0].metric("진입 방향", direction_label)
    cols[1].metric("가상 진입가", format_krw(position["buy_price"]))
    cols[2].metric("예상 손익", format_krw(profit), format_percent(profit_rate))
    cols[3].metric("매수 시간", position["buy_time"])

    cols = st.columns(4)
    cols[0].metric("목표/손절", f"{position.get('target_percent', 0):.1f}% / {position.get('stop_percent', 0):.1f}%")
    cols[1].metric("보유 수량", f"{position['volume']:.8f}")
    cols[2].metric("목표가", format_krw(position["target_price"]))
    cols[3].metric("손절가", format_krw(position["stop_price"]))

    target_hit = is_position_target_hit(position, current_price)
    stop_hit = is_position_stop_hit(position, current_price)

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
    cols[0].write(f"목표가: **{format_krw(position['target_price'])}**")
    cols[1].write(f"손절가: **{format_krw(position['stop_price'])}**")
    cols[2].write(f"상태: **{'목표 도달' if target_hit else '손절 도달' if stop_hit else '진행 중'}**")

    if target_hit:
        sell_virtual_position(current_price, "목표가 도달")
        st.success("목표가에 도달해서 가상 청산 기록을 남겼습니다.")
        st.rerun()

    if stop_hit:
        sell_virtual_position(current_price, "손절")
        st.warning("손절가에 도달해서 가상 청산 기록을 남겼습니다.")
        st.rerun()


def show_trade_log():
    st.subheader("거래 기록")
    log = load_trade_log()
    if log.empty:
        st.caption("거래 기록이 아직 없습니다.")
        return

    view = log.tail(30).copy()
    for column in ["price", "amount", "profit"]:
        view[column] = view[column].map(lambda value: format_krw(float(value)))
    view["profit_rate"] = view["profit_rate"].map(lambda value: format_percent(float(value)))
    st.dataframe(view, use_container_width=True, hide_index=True)


def show_top_movers():
    st.subheader("전일대비 변동 TOP 3")

    try:
        gainers, losers = get_top_movers()
    except Exception as exc:
        st.warning(f"변동률 데이터를 가져오지 못했습니다: {exc}")
        return

    def show_mover_rows(title, df, key_prefix):
        st.caption(title)
        header = st.columns([2.6, 1.2, 1.1, 1.1, 0.9])
        header[0].write("코인")
        header[1].write("현재가")
        header[2].write("전일대비")
        header[3].write("변동금액")
        header[4].write("차트")

        for index, row in df.reset_index(drop=True).iterrows():
            cols = st.columns([2.6, 1.2, 1.1, 1.1, 0.9])
            cols[0].write(row["코인"])
            cols[1].write(format_krw(row["현재가"]))
            cols[2].write(format_percent(row["전일대비"]))
            cols[3].write(format_krw(row["변동금액"]))
            if cols[4].button("보기", key=f"{key_prefix}_{index}_{row['마켓']}"):
                st.session_state.selected_mover_label = row["코인"]
                st.session_state.selected_mover_ticker = row["마켓"]
                st.session_state.selected_mover_source = title
                st.rerun()

    left, right = st.columns(2)
    with left:
        show_mover_rows("상승 변동 TOP 3", gainers, "gainer")
    with right:
        show_mover_rows("하락 변동 TOP 3", losers, "loser")


def render_dashboard(
    coin_label,
    ticker,
    buy_amount,
    direction,
    target_percent,
    stop_percent,
    chart_count,
    show_movers=False,
    entry_button_label="가상 진입",
    reason_label="기본 가상매매",
    key_prefix="dashboard",
):
    try:
        current_price = get_current_price(ticker)
    except Exception as exc:
        st.error(f"가격 조회 실패: {exc}")
        return
    live_history = update_live_price_history(ticker, current_price)

    top_cols = st.columns(4)
    top_cols[0].metric("선택 코인", coin_label)
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

    if show_movers:
        st.divider()
        show_top_movers()
        st.divider()

    left, right = st.columns([2, 1])

    with left:
        st.subheader("가격 차트")
        if history.empty:
            if live_history.empty:
                st.warning("차트 데이터를 가져오지 못했습니다.")
                return
            st.line_chart(live_history)
        else:
            position = st.session_state.position
            if position and position["ticker"] != ticker:
                position = None
            candle_chart = build_candle_chart(history, current_price, position)
            if candle_chart is None:
                st.warning("차트 데이터를 가져오지 못했습니다.")
            else:
                st.plotly_chart(candle_chart, use_container_width=True)

    with right:
        st.subheader("가상 포지션")
        show_position(current_price, ticker)

        position = st.session_state.position
        buy_disabled = position is not None
        sell_disabled = position is None or position["ticker"] != ticker

        if st.button(
            entry_button_label,
            disabled=buy_disabled,
            use_container_width=True,
            key=f"{key_prefix}_entry",
        ):
            open_virtual_position(
                ticker,
                current_price,
                buy_amount,
                direction,
                target_percent,
                stop_percent,
                reason_label,
            )
            st.success("가상 진입 기록을 남겼습니다.")
            st.rerun()

        if st.button(
            "즉시 가상 청산",
            disabled=sell_disabled,
            use_container_width=True,
            key=f"{key_prefix}_close",
        ):
            sell_virtual_position(current_price, "수동청산")
            st.success("즉시 가상 청산 기록을 남겼습니다.")
            st.rerun()

    st.divider()
    show_trade_log()


def main():
    st.set_page_config(page_title="가상 자동매매 대시보드", layout="wide")
    st.title("가상 자동매매 대시보드")

    if "position" not in st.session_state:
        reset_position()

    with st.sidebar:
        st.header("설정")
        refresh_seconds = st.selectbox(
            "자동 새로고침",
            [5, 3, 10, 0],
            format_func=lambda value: "꺼짐" if value == 0 else f"{value}초",
        )

    refresh_interval = None if refresh_seconds == 0 else f"{refresh_seconds}s"

    basic_tab, mover_tab = st.tabs(["기본 가상매매", "급변동 코인"])

    with basic_tab:
        st.subheader("기본 가상매매")
        coin_label = st.selectbox("코인", list(COIN_OPTIONS.keys()), key="basic_coin")
        ticker = COIN_OPTIONS[coin_label]

        cols = st.columns(4)
        buy_amount = cols[0].number_input(
            "가상 매수 금액",
            min_value=1000,
            value=10000,
            step=1000,
            key="basic_amount",
        )
        target_percent = cols[1].number_input(
            "익절 퍼센트",
            min_value=0.1,
            value=3.0,
            step=0.1,
            key="basic_target",
        )
        stop_percent = cols[2].number_input(
            "손절 퍼센트",
            min_value=0.1,
            value=2.0,
            step=0.1,
            key="basic_stop",
        )
        chart_count = cols[3].slider(
            "차트 길이(분)",
            min_value=30,
            max_value=240,
            value=120,
            step=30,
            key="basic_chart_count",
        )

        @st.fragment(run_every=refresh_interval)
        def basic_live_area():
            render_dashboard(
                coin_label,
                ticker,
                buy_amount,
                "LONG",
                target_percent,
                stop_percent,
                chart_count,
                entry_button_label="가상 매수",
                reason_label="기본 가상매매",
                key_prefix="basic",
            )

        basic_live_area()

    with mover_tab:
        st.subheader("급변동 코인")

        @st.fragment(run_every=refresh_interval)
        def mover_list_area():
            show_top_movers()

        mover_list_area()

        selected_mover_ticker = st.session_state.get("selected_mover_ticker")
        selected_mover_label = st.session_state.get("selected_mover_label")

        if not selected_mover_ticker or not selected_mover_label:
            st.info("상승/하락 TOP 3 목록에서 차트 보기 버튼을 눌러 코인을 먼저 선택하세요.")
        else:
            st.info(f"TOP 3에서 선택됨: {selected_mover_label}")
            if st.button("TOP 3 선택 해제", use_container_width=True):
                clear_selected_mover()
                st.rerun()

            cols = st.columns(4)
            mover_amount = cols[0].number_input(
                "가상 진입 금액",
                min_value=1000,
                value=10000,
                step=1000,
                key="mover_amount",
            )
            direction_label = cols[1].selectbox(
                "가상 방향",
                ["롱 가상", "숏 가상"],
                key="mover_direction",
            )
            direction = "SHORT" if direction_label == "숏 가상" else "LONG"
            move_percent = cols[2].number_input(
                "기준 움직임 %",
                min_value=0.1,
                value=3.0,
                step=0.1,
                key="mover_move",
            )
            mover_chart_count = cols[3].slider(
                "차트 길이(분)",
                min_value=30,
                max_value=240,
                value=120,
                step=30,
                key="mover_chart_count",
            )

            @st.fragment(run_every=refresh_interval)
            def mover_live_area():
                render_dashboard(
                    selected_mover_label,
                    selected_mover_ticker,
                    mover_amount,
                    direction,
                    move_percent,
                    move_percent,
                    mover_chart_count,
                    entry_button_label="급변동 코인 가상 진입",
                    reason_label="급변동 코인",
                    key_prefix="mover",
                )

            mover_live_area()

    st.caption("이 화면은 가상매매 전용입니다. 실제 매수/매도 주문은 실행하지 않습니다.")


if __name__ == "__main__":
    main()
