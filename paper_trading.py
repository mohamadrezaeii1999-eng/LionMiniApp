import json
import os
from datetime import datetime, timezone

DATA_FILE = "paper_wallet.json"
START_BALANCE = 2.0


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "balance": START_BALANCE,
            "equity": START_BALANCE,
            "trades": [],
            "open_positions": []
        }

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_wallet():
    data = load_data()

    floating_pnl = 0.0

    for position in data["open_positions"]:
        floating_pnl += float(position.get("pnl", 0))

    return {
        "balance": round(data["balance"], 2),
        "equity": round(data["balance"] + floating_pnl, 2),
        "open_positions": len(data["open_positions"]),
        "total_trades": len(data["trades"]),
        "positions": data["open_positions"]
    }


def open_trade(
    symbol,
    signal,
    entry,
    stop_loss,
    take_profit,
    amount=2.0
):
    data = load_data()

    amount = float(amount)

    if amount <= 0:
        return {
            "status": "error",
            "message": "مبلغ معامله باید بیشتر از صفر باشد"
        }

    if amount > data["balance"]:
        return {
            "status": "error",
            "message": "موجودی کافی نیست"
        }

    entry = float(entry)

    position = {
        "id": len(data["trades"]) + len(data["open_positions"]) + 1,
        "symbol": symbol,
        "signal": signal,
        "entry": entry,
        "stop_loss": float(stop_loss),
        "take_profit": float(take_profit),
        "amount": amount,
        "pnl": 0.0,
        "opened_at": datetime.now(timezone.utc).isoformat()
    }

    data["open_positions"].append(position)

    save_data(data)

    return {
        "status": "ok",
        "message": "Paper Trade باز شد",
        "position": position
    }


def close_trade(position, exit_price):
    entry = float(position["entry"])
    exit_price = float(exit_price)
    amount = float(position.get("amount", 2.0))

    if position["signal"] == "BUY":
        price_change = exit_price - entry
    else:
        price_change = entry - exit_price

    # درصد تغییر قیمت × مبلغ معامله
    pnl = (price_change / entry) * amount

    data = load_data()

    data["balance"] += pnl
    data["equity"] = data["balance"]

    trade = {
        **position,
        "exit": exit_price,
        "pnl": round(pnl, 6),
        "closed_at": datetime.now(timezone.utc).isoformat()
    }

    data["trades"].append(trade)

    data["open_positions"] = [
        p for p in data["open_positions"]
        if p["id"] != position["id"]
    ]

    save_data(data)

    return trade


def check_positions(prices):
    data = load_data()
    closed = []

    for position in list(data["open_positions"]):
        symbol = position["symbol"]

        if symbol not in prices:
            continue

        price = float(prices[symbol])

        if position["signal"] == "BUY":

            if price <= position["stop_loss"]:
                closed.append(
                    close_trade(
                        position,
                        position["stop_loss"]
                    )
                )

            elif price >= position["take_profit"]:
                closed.append(
                    close_trade(
                        position,
                        position["take_profit"]
                    )
                )

        elif position["signal"] == "SELL":

            if price >= position["stop_loss"]:
                closed.append(
                    close_trade(
                        position,
                        position["stop_loss"]
                    )
                )

            elif price <= position["take_profit"]:
                closed.append(
                    close_trade(
                        position,
                        position["take_profit"]
                    )
                )

    return {
        "status": "ok",
        "closed": closed,
        "wallet": get_wallet()
    }


def reset_wallet():
    data = {
        "balance": START_BALANCE,
        "equity": START_BALANCE,
        "trades": [],
        "open_positions": []
    }

    save_data(data)

    return {
        "status": "ok",
        "message": "Paper Wallet ریست شد",
        "wallet": get_wallet()
    }

