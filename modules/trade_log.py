from pathlib import Path

import pandas as pd


TRADE_LOG_PATH = Path("data/trades.csv")
TRADE_LOG_COLUMNS = [
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


def ensure_trade_log():
    TRADE_LOG_PATH.parent.mkdir(exist_ok=True)
    if not TRADE_LOG_PATH.exists():
        pd.DataFrame(columns=TRADE_LOG_COLUMNS).to_csv(
            TRADE_LOG_PATH,
            index=False,
            encoding="utf-8-sig",
        )


def load_trade_log():
    ensure_trade_log()
    return pd.read_csv(TRADE_LOG_PATH)


def append_trade_log(row):
    ensure_trade_log()
    log = load_trade_log()
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    log.to_csv(TRADE_LOG_PATH, index=False, encoding="utf-8-sig")


def clear_trade_log():
    TRADE_LOG_PATH.parent.mkdir(exist_ok=True)
    pd.DataFrame(columns=TRADE_LOG_COLUMNS).to_csv(
        TRADE_LOG_PATH,
        index=False,
        encoding="utf-8-sig",
    )
