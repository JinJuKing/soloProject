import pandas as pd
import streamlit as st

from modules.live_trade import calculate_recommendation
from modules.market import get_price_history, get_top_movers


def _score_coin(row, history):
    close = history["현재가"]
    volume = history["거래량"]
    current_price = float(close.iloc[-1])
    ma5 = float(close.tail(5).mean())
    ma20 = float(close.tail(20).mean())
    recent_change = ((current_price - float(close.iloc[-10])) / float(close.iloc[-10])) * 100
    volatility = float(close.pct_change().dropna().tail(30).abs().mean() * 100)

    recent_volume = float(volume.tail(10).mean())
    base_volume = float(volume.tail(40).head(30).mean())
    volume_ratio = recent_volume / base_volume if base_volume > 0 else 1

    recent_high = float(history["고가"].tail(30).max())
    high_distance = ((current_price - recent_high) / recent_high) * 100 if recent_high > 0 else 0

    score = 50
    reasons = []

    if current_price > ma5 > ma20:
        score += 18
        reasons.append("단기 이동평균이 중기 이동평균 위에 있어 상승 흐름이 있습니다.")
    elif current_price > ma20:
        score += 8
        reasons.append("현재가가 중기 이동평균 위에 있습니다.")
    else:
        score -= 8
        reasons.append("현재가가 중기 이동평균 아래에 있어 추세 확인이 필요합니다.")

    if volume_ratio >= 1.8:
        score += 18
        reasons.append("최근 거래량이 평소보다 크게 증가했습니다.")
    elif volume_ratio >= 1.2:
        score += 10
        reasons.append("최근 거래량이 증가했습니다.")
    else:
        score -= 4
        reasons.append("거래량 증가가 뚜렷하지 않습니다.")

    if 0.2 <= recent_change <= 4:
        score += 12
        reasons.append("단기 상승률이 과열권 전에는 머물러 있습니다.")
    elif recent_change > 8:
        score -= 12
        reasons.append("단기 급등폭이 커서 추격 매수 위험이 있습니다.")
    elif recent_change < -2:
        score -= 10
        reasons.append("단기 하락 흐름이 강합니다.")

    if high_distance >= -1.5:
        score += 8
        reasons.append("최근 고점 근처에서 거래되고 있습니다.")

    if volatility > 1.5:
        score -= 8
        risk = "높음"
    elif volatility > 0.8:
        risk = "중간"
    else:
        risk = "낮음"

    target_percent, stop_percent, _ = calculate_recommendation(history)
    score = max(0, min(round(score), 100))

    if score >= 75:
        opinion = "매수 후보"
    elif score >= 60:
        opinion = "관찰 후보"
    else:
        opinion = "보류"

    return {
        "코인": row["코인"],
        "마켓": row["마켓"],
        "현재가": row["현재가"],
        "점수": score,
        "판단": opinion,
        "위험도": risk,
        "추천 익절": target_percent,
        "추천 손절": stop_percent,
        "추천 이유": " ".join(reasons[:3]),
    }


@st.cache_data(ttl=30)
def get_rule_based_recommendations(limit=5):
    gainers, losers = get_top_movers(limit=limit)
    candidates = pd.concat([gainers, losers], ignore_index=True)
    candidates = candidates.drop_duplicates(subset=["마켓"]).head(limit * 2)

    recommendations = []
    for _, row in candidates.iterrows():
        history = get_price_history(row["마켓"], 60)
        if history is None or history.empty or len(history) < 20:
            continue
        recommendations.append(_score_coin(row, history))

    if not recommendations:
        return pd.DataFrame()

    return pd.DataFrame(recommendations).sort_values("점수", ascending=False).head(limit)
