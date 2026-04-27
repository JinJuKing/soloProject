import pandas as pd
import streamlit as st

from modules.chart import build_candle_chart
from modules.formatting import format_krw, format_percent
from modules.market import COIN_OPTIONS, get_current_price, get_price_history, get_top_movers
from modules.position import (
    build_close_log_row,
    build_open_log_row,
    build_virtual_position,
    calculate_position_profit,
    is_position_stop_hit,
    is_position_target_hit,
)
from modules.trade_log import append_trade_log, clear_trade_log, load_trade_log


def update_live_price_history(ticker, current_price):
    live_prices_by_ticker = st.session_state.setdefault("live_prices_by_ticker", {})
    live_prices = live_prices_by_ticker.setdefault(ticker, [])
    live_prices.append({"time": pd.Timestamp.now(), "price": current_price})
    live_prices_by_ticker[ticker] = live_prices[-120:]
    st.session_state.live_prices_by_ticker = live_prices_by_ticker

    live_df = pd.DataFrame(live_prices_by_ticker[ticker])
    if live_df.empty:
        return pd.DataFrame()

    live_df = live_df.set_index("time").rename(columns={"price": "실시간 현재가"})
    live_df.index.name = "시간"
    return live_df


def reset_position():
    st.session_state.position = None


def clear_selected_mover():
    st.session_state.pop("selected_mover_label", None)
    st.session_state.pop("selected_mover_ticker", None)
    st.session_state.pop("selected_mover_source", None)


def open_virtual_position(ticker, price, amount, direction, target_percent, stop_percent, reason_label):
    position = build_virtual_position(ticker, price, amount, direction, target_percent, stop_percent)
    st.session_state.position = position
    append_trade_log(build_open_log_row(position, reason_label))


def close_virtual_position(price, reason):
    position = st.session_state.position
    if position is None:
        return

    append_trade_log(build_close_log_row(position, price, reason))
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
        close_virtual_position(current_price, "목표가 도달")
        st.success("목표가에 도달해서 가상 청산 기록을 남겼습니다.")
        st.rerun()

    if stop_hit:
        close_virtual_position(current_price, "손절")
        st.warning("손절가에 도달해서 가상 청산 기록을 남겼습니다.")
        st.rerun()


def show_trade_log():
    st.subheader("거래 기록")

    with st.expander("거래 기록 관리"):
        confirm_clear = st.checkbox("거래 기록을 모두 삭제하겠습니다.", key="confirm_clear_trade_log")
        if st.button("거래 기록 초기화", disabled=not confirm_clear, key="clear_trade_log"):
            clear_trade_log()
            st.success("거래 기록을 초기화했습니다.")
            st.rerun()

    log = load_trade_log()
    if log.empty:
        st.caption("거래 기록이 아직 없습니다.")
        return

    view = log.tail(30).copy()
    for column in ["price", "amount", "profit"]:
        view[column] = view[column].map(lambda value: format_krw(float(value)))
    view["profit_rate"] = view["profit_rate"].map(lambda value: format_percent(float(value)))
    view = view.rename(
        columns={
            "time": "시간",
            "ticker": "코인",
            "side": "구분",
            "reason": "사유",
            "price": "가격",
            "amount": "금액",
            "volume": "수량",
            "profit": "손익",
            "profit_rate": "수익률",
        }
    )
    st.dataframe(view, use_container_width=True, hide_index=True)


def show_top_movers():
    st.subheader("전일대비 변동 TOP 3")

    try:
        gainers, losers = get_top_movers()
    except Exception as exc:
        st.warning(f"변동률 데이터를 가져오지 못했습니다: {exc}")
        return

    left, right = st.columns(2)
    with left:
        show_mover_rows("상승 변동 TOP 3", gainers, "gainer")
    with right:
        show_mover_rows("하락 변동 TOP 3", losers, "loser")


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


def render_dashboard(
    coin_label,
    ticker,
    buy_amount,
    direction,
    target_percent,
    stop_percent,
    chart_count,
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
    show_price_summary(coin_label, ticker, current_price, chart_count)

    left, right = st.columns([2, 1])
    with left:
        show_price_chart(ticker, current_price, chart_count, live_history)
    with right:
        show_position_controls(
            ticker,
            current_price,
            buy_amount,
            direction,
            target_percent,
            stop_percent,
            entry_button_label,
            reason_label,
            key_prefix,
        )

    st.divider()
    show_trade_log()


def show_price_summary(coin_label, ticker, current_price, chart_count):
    top_cols = st.columns(4)
    top_cols[0].metric("선택 코인", coin_label)
    top_cols[1].metric("현재가", format_krw(current_price))

    history = get_price_history(ticker, chart_count)
    if history.empty:
        top_cols[2].metric("차트 기준 변동률", "-")
        top_cols[3].metric("조회 구간", f"{chart_count}분")
        return

    open_price = float(history["현재가"].iloc[0])
    change_rate = ((current_price - open_price) / open_price) * 100
    top_cols[2].metric("차트 기준 변동률", format_percent(change_rate))
    top_cols[3].metric("조회 구간", f"{chart_count}분")


def show_price_chart(ticker, current_price, chart_count, live_history):
    st.subheader("가격 차트")
    history = get_price_history(ticker, chart_count)
    if history.empty:
        if live_history.empty:
            st.warning("차트 데이터를 가져오지 못했습니다.")
            return
        st.line_chart(live_history)
        return

    position = st.session_state.position
    if position and position["ticker"] != ticker:
        position = None

    candle_chart = build_candle_chart(history, current_price, position)
    if candle_chart is None:
        st.warning("차트 데이터를 가져오지 못했습니다.")
    else:
        st.plotly_chart(candle_chart, use_container_width=True)


def show_position_controls(
    ticker,
    current_price,
    buy_amount,
    direction,
    target_percent,
    stop_percent,
    entry_button_label,
    reason_label,
    key_prefix,
):
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
        close_virtual_position(current_price, "수동청산")
        st.success("즉시 가상 청산 기록을 남겼습니다.")
        st.rerun()


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
        show_basic_tab(refresh_interval)

    with mover_tab:
        show_mover_tab(refresh_interval)

    st.caption("이 화면은 가상매매 전용입니다. 실제 매수/매도 주문은 실행하지 않습니다.")


def show_basic_tab(refresh_interval):
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


def show_mover_tab(refresh_interval):
    st.subheader("급변동 코인")

    @st.fragment(run_every=refresh_interval)
    def mover_list_area():
        show_top_movers()

    mover_list_area()

    selected_mover_ticker = st.session_state.get("selected_mover_ticker")
    selected_mover_label = st.session_state.get("selected_mover_label")

    if not selected_mover_ticker or not selected_mover_label:
        st.info("상승/하락 TOP 3 목록에서 차트 보기 버튼을 눌러 코인을 먼저 선택하세요.")
        return

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


if __name__ == "__main__":
    main()
