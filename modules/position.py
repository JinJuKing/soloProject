from datetime import datetime


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


def build_virtual_position(ticker, price, amount, direction, target_percent, stop_percent):
    volume = amount / price
    target_price, stop_price = get_position_prices(price, target_percent, stop_percent, direction)
    direction_label = "숏 가상" if direction == "SHORT" else "롱 가상"

    return {
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


def build_open_log_row(position, reason_label):
    return {
        "time": position["buy_time"],
        "ticker": position["ticker"],
        "side": "SHORT" if position["direction"] == "SHORT" else "LONG",
        "reason": f"{reason_label} 진입",
        "price": position["buy_price"],
        "amount": position["amount"],
        "volume": position["volume"],
        "profit": 0,
        "profit_rate": 0,
    }


def build_close_log_row(position, price, reason):
    profit, profit_rate = calculate_position_profit(position, price)
    return {
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
