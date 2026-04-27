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
