def get_live_trade_block_reasons(
    buy_amount,
    krw_balance,
    max_order_amount,
    daily_loss_limit,
    today_profit,
):
    reasons = []

    if buy_amount > krw_balance:
        reasons.append("매수 금액이 보유 원화보다 큽니다.")

    if max_order_amount > 0 and buy_amount > max_order_amount:
        reasons.append(f"1회 최대 매수 금액 {max_order_amount:,.0f}원을 초과했습니다.")

    if daily_loss_limit > 0 and today_profit <= -daily_loss_limit:
        reasons.append(f"오늘 실현 손실이 제한값 {daily_loss_limit:,.0f}원에 도달했습니다.")

    return reasons
