import pandas as pd


def get_closed_trades(log):
    if log is None or log.empty or "side" not in log.columns:
        return pd.DataFrame()

    closed = log[log["side"].astype(str).str.startswith("CLOSE")].copy()
    if closed.empty:
        return closed

    closed["profit"] = pd.to_numeric(closed.get("profit"), errors="coerce").fillna(0)
    closed["profit_rate"] = pd.to_numeric(closed.get("profit_rate"), errors="coerce").fillna(0)
    closed["time"] = pd.to_datetime(closed.get("time"), errors="coerce")
    closed["trade_date"] = closed["time"].dt.date
    return closed


def build_performance_summary(log):
    closed = get_closed_trades(log)
    if closed.empty:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "today_profit": 0.0,
            "average_profit_rate": 0.0,
            "max_loss": 0.0,
        }

    today = pd.Timestamp.now().date()
    wins = int((closed["profit"] > 0).sum())
    losses = int((closed["profit"] < 0).sum())
    total_trades = len(closed)
    win_rate = wins / total_trades * 100 if total_trades else 0.0
    today_profit = closed.loc[closed["trade_date"] == today, "profit"].sum()

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": float(win_rate),
        "total_profit": float(closed["profit"].sum()),
        "today_profit": float(today_profit),
        "average_profit_rate": float(closed["profit_rate"].mean()),
        "max_loss": float(closed["profit"].min()),
    }
