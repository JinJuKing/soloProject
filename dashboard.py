import pandas as pd
import streamlit as st

from modules.chart import build_candle_chart
from modules.ai_advisor import get_rule_based_recommendations
from modules.formatting import format_krw, format_percent
from modules.market import COIN_OPTIONS, get_current_price, get_price_history, get_top_movers
from modules.live_trade import (
    build_live_position,
    calculate_recommendation,
    get_account_snapshot,
    get_upbit_client,
    place_market_buy,
    place_market_sell,
)
from modules.position import (
    build_close_log_row,
    build_open_log_row,
    build_virtual_position,
    calculate_position_profit,
    is_position_stop_hit,
    is_position_target_hit,
)
from modules.performance import build_performance_summary
from modules.risk import get_live_trade_block_reasons
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


def clear_selected_ai_coin():
    st.session_state.pop("selected_ai_label", None)
    st.session_state.pop("selected_ai_ticker", None)
    st.session_state.pop("selected_ai_target", None)
    st.session_state.pop("selected_ai_stop", None)


def get_live_client_from_inputs():
    access_key = st.session_state.get("live_access_key")
    secret_key = st.session_state.get("live_secret_key")
    return get_upbit_client(access_key, secret_key)


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


def close_live_position(upbit, price, reason):
    position = st.session_state.position
    if position is None:
        return
    if upbit is None:
        st.error("실제 매도를 위해 API 키를 다시 입력해주세요.")
        return
    if st.session_state.get("order_in_progress"):
        st.warning("주문 처리 중입니다. 잠시만 기다려주세요.")
        return

    st.session_state.order_in_progress = True
    try:
        result = place_market_sell(upbit, position["ticker"], position["volume"])
        if isinstance(result, dict) and "error" in result:
            st.error(f"실제 매도 실패: {result['error'].get('message')}")
            return

        append_trade_log(build_close_log_row(position, price, f"실거래 {reason}"))
        reset_position()
        st.success("실제 시장가 매도 주문을 실행했습니다.")
    finally:
        st.session_state.order_in_progress = False


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
        if position.get("mode") == "LIVE":
            upbit = get_live_client_from_inputs()
            close_live_position(upbit, current_price, "목표가 도달")
        else:
            close_virtual_position(current_price, "목표가 도달")
            st.success("목표가에 도달해서 가상 청산 기록을 남겼습니다.")
        st.rerun()

    if stop_hit:
        if position.get("mode") == "LIVE":
            upbit = get_live_client_from_inputs()
            close_live_position(upbit, current_price, "손절")
        else:
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

    show_performance_summary(log)

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


def show_performance_summary(log):
    summary = build_performance_summary(log)
    if summary["total_trades"] == 0:
        st.caption("청산된 거래가 생기면 승률과 손익 요약이 표시됩니다.")
        return

    st.caption("청산 기준 거래 성과")
    cols = st.columns(6)
    cols[0].metric("청산 거래", f"{summary['total_trades']}회")
    cols[1].metric("승률", format_percent(summary["win_rate"]))
    cols[2].metric("총 손익", format_krw(summary["total_profit"]))
    cols[3].metric("오늘 손익", format_krw(summary["today_profit"]))
    cols[4].metric("평균 수익률", format_percent(summary["average_profit_rate"]))
    cols[5].metric("최대 손실", format_krw(summary["max_loss"]))


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


def render_live_dashboard(
    coin_label,
    ticker,
    buy_amount,
    target_percent,
    stop_percent,
    chart_count,
    live_enabled,
    access_key,
    secret_key,
    max_order_amount,
    daily_loss_limit,
    live_reason_label="실거래 기본매매",
    live_buy_key="basic_live_buy",
    live_sell_key="basic_live_sell",
):
    try:
        current_price = get_current_price(ticker)
    except Exception as exc:
        st.error(f"가격 조회 실패: {exc}")
        return

    live_history = update_live_price_history(ticker, current_price)
    show_price_summary(coin_label, ticker, current_price, chart_count)

    if not live_enabled:
        st.info("실거래 활성화를 체크하면 API 키 입력창과 실제 주문 버튼이 열립니다.")
        show_price_chart(ticker, current_price, chart_count, live_history)
        return

    upbit = get_upbit_client(access_key, secret_key)
    if upbit is None:
        st.error("실거래를 사용하려면 업비트 Access Key와 Secret Key를 입력해주세요.")
        show_price_chart(ticker, current_price, chart_count, live_history)
        return

    try:
        account = get_account_snapshot(upbit, ticker)
    except Exception as exc:
        st.error(f"API 키 확인 또는 잔고 조회에 실패했습니다: {exc}")
        show_price_chart(ticker, current_price, chart_count, live_history)
        return

    account_cols = st.columns(3)
    account_cols[0].metric("보유 원화", format_krw(account["krw"]))
    account_cols[1].metric(f"보유 {account['currency']}", f"{account['coin']:.8f}")
    account_cols[2].metric("실거래 상태", "활성화" if live_enabled else "잠김")
    performance_summary = build_performance_summary(load_trade_log())

    left, right = st.columns([2, 1])
    with left:
        show_price_chart(ticker, current_price, chart_count, live_history)
    with right:
        show_live_position_controls(
            upbit,
            ticker,
            current_price,
            buy_amount,
            target_percent,
            stop_percent,
            live_enabled,
            account["krw"],
            max_order_amount,
            daily_loss_limit,
            performance_summary["today_profit"],
            live_reason_label,
            live_buy_key,
            live_sell_key,
        )

    st.divider()
    show_trade_log()


def show_live_position_controls(
    upbit,
    ticker,
    current_price,
    buy_amount,
    target_percent,
    stop_percent,
    live_enabled,
    krw_balance,
    max_order_amount,
    daily_loss_limit,
    today_profit,
    live_reason_label,
    live_buy_key,
    live_sell_key,
):
    st.subheader("실거래 포지션")
    show_position(current_price, ticker)

    position = st.session_state.position
    has_any_position = position is not None
    has_this_position = position is not None and position["ticker"] == ticker
    api_ready = get_live_client_from_inputs() is not None
    risk_reasons = get_live_trade_block_reasons(
        buy_amount,
        krw_balance,
        max_order_amount,
        daily_loss_limit,
        today_profit,
    )
    order_in_progress = st.session_state.get("order_in_progress", False)
    ready_to_trade = live_enabled and api_ready and not risk_reasons and not order_in_progress

    if live_enabled and not api_ready:
        st.warning("실거래를 하려면 API 키를 입력해주세요.")

    for reason in risk_reasons:
        st.warning(reason)

    if order_in_progress:
        st.info("주문 처리 중입니다. 잠시만 기다려주세요.")

    if st.button(
        "실제 시장가 매수",
        disabled=has_any_position or not ready_to_trade,
        use_container_width=True,
        key=live_buy_key,
    ):
        st.session_state.order_in_progress = True
        try:
            result, bought_volume = place_market_buy(upbit, ticker, buy_amount)
            if isinstance(result, dict) and "error" in result:
                st.error(f"실제 매수 실패: {result['error'].get('message')}")
                return

            if bought_volume <= 0:
                bought_volume = buy_amount / current_price
                st.warning("매수 수량 확인이 늦어져 현재가 기준 추정 수량으로 포지션을 기록했습니다.")

            position = build_live_position(
                ticker,
                current_price,
                buy_amount,
                bought_volume,
                target_percent,
                stop_percent,
            )
            st.session_state.position = position
            append_trade_log(build_open_log_row(position, live_reason_label))
            st.success("실제 시장가 매수 주문을 실행했습니다.")
        finally:
            st.session_state.order_in_progress = False
        st.rerun()

    if st.button(
        "즉시 실제 시장가 매도",
        disabled=not has_this_position or order_in_progress,
        use_container_width=True,
        key=live_sell_key,
    ):
        close_live_position(upbit, current_price, "수동청산")
        st.rerun()


def main():
    st.set_page_config(page_title="가상 자동매매 대시보드", layout="wide")
    st.title("가상 자동매매 대시보드")

    if "position" not in st.session_state:
        reset_position()
    if "order_in_progress" not in st.session_state:
        st.session_state.order_in_progress = False

    with st.sidebar:
        st.header("설정")
        refresh_seconds = st.selectbox(
            "자동 새로고침",
            [5, 3, 10, 0],
            format_func=lambda value: "꺼짐" if value == 0 else f"{value}초",
        )
        live_enabled = st.checkbox("실거래 활성화", key="live_enabled")
        access_key = ""
        secret_key = ""
        max_order_amount = 0
        daily_loss_limit = 0
        if live_enabled:
            access_key = st.text_input(
                "Upbit Access Key",
                value="",
                key="live_access_key",
                type="password",
            )
            secret_key = st.text_input(
                "Upbit Secret Key",
                value="",
                key="live_secret_key",
                type="password",
            )
            max_order_amount = st.number_input(
                "1회 최대 매수 금액",
                min_value=0,
                value=10000,
                step=1000,
                help="0원으로 두면 1회 매수 금액 제한을 사용하지 않습니다.",
            )
            daily_loss_limit = st.number_input(
                "하루 최대 실현 손실",
                min_value=0,
                value=10000,
                step=1000,
                help="0원으로 두면 하루 손실 제한을 사용하지 않습니다.",
            )
            st.caption("API 키는 현재 Streamlit 세션에서만 사용하고 파일/GitHub에 저장하지 않습니다.")

    refresh_interval = None if refresh_seconds == 0 else f"{refresh_seconds}s"
    basic_tab, mover_tab, ai_tab = st.tabs(["기본 실거래", "급변동 코인", "AI 추천"])

    with basic_tab:
        show_basic_tab(refresh_interval, live_enabled, access_key, secret_key, max_order_amount, daily_loss_limit)

    with mover_tab:
        show_mover_tab(refresh_interval, live_enabled, access_key, secret_key, max_order_amount, daily_loss_limit)

    with ai_tab:
        show_ai_tab(refresh_interval, live_enabled, access_key, secret_key, max_order_amount, daily_loss_limit)

    st.caption("실거래 활성화와 API 키 확인 후 기본 실거래/급변동 코인 탭에서 실제 현물 시장가 주문을 실행할 수 있습니다.")


def show_basic_tab(refresh_interval, live_enabled, access_key, secret_key, max_order_amount, daily_loss_limit):
    st.subheader("기본 실거래 매매")
    coin_label = st.selectbox("코인", list(COIN_OPTIONS.keys()), key="basic_coin")
    ticker = COIN_OPTIONS[coin_label]
    recommendation_history = get_price_history(ticker, 60)
    recommended_target, recommended_stop, recommendation_message = calculate_recommendation(recommendation_history)

    st.warning("이 탭은 실제 업비트 시장가 주문을 실행할 수 있습니다. 소액으로 테스트하고, 수익은 보장되지 않습니다.")
    st.info(
        f"추천 참고값: 익절 {recommended_target:.2f}% / 손절 {recommended_stop:.2f}% - "
        f"{recommendation_message}"
    )

    cols = st.columns(4)
    buy_amount = cols[0].number_input(
        "실제 매수 금액",
        min_value=1000,
        value=10000,
        step=1000,
        key="basic_amount",
    )
    target_percent = cols[1].number_input(
        "익절 퍼센트",
        min_value=0.1,
        value=float(recommended_target),
        step=0.1,
        key="basic_target",
    )
    stop_percent = cols[2].number_input(
        "손절 퍼센트",
        min_value=0.1,
        value=float(recommended_stop),
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
        render_live_dashboard(
            coin_label,
            ticker,
            buy_amount,
            target_percent,
            stop_percent,
            chart_count,
            live_enabled,
            access_key,
            secret_key,
            max_order_amount,
            daily_loss_limit,
        )

    basic_live_area()


def show_mover_tab(refresh_interval, live_enabled, access_key, secret_key, max_order_amount, daily_loss_limit):
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

    recommendation_history = get_price_history(selected_mover_ticker, 60)
    recommended_target, recommended_stop, recommendation_message = calculate_recommendation(recommendation_history)
    st.info(
        f"추천 참고값: 익절 {recommended_target:.2f}% / 손절 {recommended_stop:.2f}% - "
        f"{recommendation_message}"
    )

    cols = st.columns(4)
    mover_amount = cols[0].number_input(
        "매수 금액",
        min_value=1000,
        value=10000,
        step=1000,
        key="mover_amount",
    )
    target_percent = cols[1].number_input(
        "익절 퍼센트",
        min_value=0.1,
        value=float(recommended_target),
        step=0.1,
        key="mover_target",
    )
    stop_percent = cols[2].number_input(
        "손절 퍼센트",
        min_value=0.1,
        value=float(recommended_stop),
        step=0.1,
        key="mover_stop",
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
        render_live_dashboard(
            selected_mover_label,
            selected_mover_ticker,
            mover_amount,
            target_percent,
            stop_percent,
            mover_chart_count,
            live_enabled,
            access_key,
            secret_key,
            max_order_amount,
            daily_loss_limit,
            live_reason_label="실거래 급변동 코인",
            live_buy_key="mover_live_buy",
            live_sell_key="mover_live_sell",
        )

    mover_live_area()


def show_ai_recommendation_rows(recommendations):
    header = st.columns([1.8, 0.7, 0.9, 0.9, 0.9, 1.1, 3.2, 0.8])
    header[0].write("코인")
    header[1].write("점수")
    header[2].write("판단")
    header[3].write("위험도")
    header[4].write("현재가")
    header[5].write("익절/손절")
    header[6].write("추천 이유")
    header[7].write("선택")

    for index, row in recommendations.reset_index(drop=True).iterrows():
        cols = st.columns([1.8, 0.7, 0.9, 0.9, 0.9, 1.1, 3.2, 0.8])
        cols[0].write(row["코인"])
        cols[1].write(f"{int(row['점수'])}점")
        cols[2].write(row["판단"])
        cols[3].write(row["위험도"])
        cols[4].write(format_krw(row["현재가"]))
        cols[5].write(f"{row['추천 익절']:.2f}% / {row['추천 손절']:.2f}%")
        cols[6].write(row["추천 이유"])
        if cols[7].button("선택", key=f"ai_pick_{index}_{row['마켓']}"):
            st.session_state.selected_ai_label = row["코인"]
            st.session_state.selected_ai_ticker = row["마켓"]
            st.session_state.selected_ai_target = float(row["추천 익절"])
            st.session_state.selected_ai_stop = float(row["추천 손절"])
            st.rerun()


def show_ai_tab(refresh_interval, live_enabled, access_key, secret_key, max_order_amount, daily_loss_limit):
    st.subheader("AI 추천")
    st.caption("외부 유료 AI API를 쓰지 않고, 이동평균/거래량/변동성/단기 추세를 점수화하는 무료 규칙 기반 추천입니다.")

    @st.fragment(run_every=refresh_interval)
    def ai_recommendation_area():
        try:
            recommendations = get_rule_based_recommendations(limit=5)
        except Exception as exc:
            st.warning(f"AI 추천 데이터를 계산하지 못했습니다: {exc}")
            return

        if recommendations.empty:
            st.info("추천 후보가 아직 없습니다.")
            return

        show_ai_recommendation_rows(recommendations)

    ai_recommendation_area()

    selected_ai_ticker = st.session_state.get("selected_ai_ticker")
    selected_ai_label = st.session_state.get("selected_ai_label")
    if not selected_ai_ticker or not selected_ai_label:
        st.info("AI 추천 목록에서 선택 버튼을 눌러 코인을 먼저 선택하세요.")
        return

    st.info(f"AI 추천에서 선택됨: {selected_ai_label}")
    if st.button("AI 추천 선택 해제", use_container_width=True):
        clear_selected_ai_coin()
        st.rerun()

    target_default = float(st.session_state.get("selected_ai_target", 1.0))
    stop_default = float(st.session_state.get("selected_ai_stop", 0.7))

    cols = st.columns(4)
    buy_amount = cols[0].number_input(
        "매수 금액",
        min_value=1000,
        value=10000,
        step=1000,
        key="ai_amount",
    )
    target_percent = cols[1].number_input(
        "익절 퍼센트",
        min_value=0.1,
        value=target_default,
        step=0.1,
        key="ai_target",
    )
    stop_percent = cols[2].number_input(
        "손절 퍼센트",
        min_value=0.1,
        value=stop_default,
        step=0.1,
        key="ai_stop",
    )
    chart_count = cols[3].slider(
        "차트 길이(분)",
        min_value=30,
        max_value=240,
        value=120,
        step=30,
        key="ai_chart_count",
    )

    @st.fragment(run_every=refresh_interval)
    def ai_live_area():
        render_live_dashboard(
            selected_ai_label,
            selected_ai_ticker,
            buy_amount,
            target_percent,
            stop_percent,
            chart_count,
            live_enabled,
            access_key,
            secret_key,
            max_order_amount,
            daily_loss_limit,
            live_reason_label="실거래 AI 추천",
            live_buy_key="ai_live_buy",
            live_sell_key="ai_live_sell",
        )

    ai_live_area()


if __name__ == "__main__":
    main()
