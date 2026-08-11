import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, request
from flask_cors import CORS

from lion_engine_v37 import analyze

app = Flask(__name__)
CORS(app)

# تمام جفت‌های اصلی Forex
FOREX_PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "USD/CAD",
    "AUD/USD",
    "NZD/USD",

    "EUR/GBP",
    "EUR/JPY",
    "EUR/CHF",
    "EUR/AUD",
    "EUR/CAD",
    "EUR/NZD",

    "GBP/JPY",
    "GBP/CHF",
    "GBP/AUD",
    "GBP/CAD",
    "GBP/NZD",

    "AUD/JPY",
    "AUD/CHF",
    "AUD/CAD",
    "AUD/NZD",

    "CAD/JPY",
    "CAD/CHF",

    "CHF/JPY",

    "NZD/JPY",
    "NZD/CHF",
    "NZD/CAD"
]

DEFAULT_SYMBOL = "EUR/USD"


@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "app": "Lion AI PRO",
        "engine": "Lion AI PRO V3.7",
        "markets": FOREX_PAIRS
    })


@app.get("/markets")
def markets():
    return jsonify({
        "status": "ok",
        "count": len(FOREX_PAIRS),
        "markets": FOREX_PAIRS
    })


@app.get("/signal")
def signal():
    symbol = request.args.get(
        "symbol",
        DEFAULT_SYMBOL
    ).strip().upper()

    if symbol not in FOREX_PAIRS:
        return jsonify({
            "status": "error",
            "message": "Unsupported market",
            "symbol": symbol,
            "supported_pairs": FOREX_PAIRS
        }), 400

    try:
        result = analyze(symbol)

        # اطمینان از اینکه نسخه واقعی API مشخص باشد
        result["api_engine"] = "Lion AI PRO V3.7"

        return jsonify(result)

    except Exception as exc:
        return jsonify({
            "status": "error",
            "symbol": symbol,
            "error": str(exc)
        }), 500



# ------------------------------------------------------------
# Lion AI PRO V3.7 - Batch Forex Scanner
# هر بار فقط 2 بازار تحلیل می‌شود تا API محدود نشود.
# ------------------------------------------------------------

SCAN_BATCH_SIZE = 2
SCAN_INDEX = 0
SCAN_RESULTS = {}
SCAN_ERRORS = {}


@app.get("/scan")
def scan():
    global SCAN_INDEX

    total_markets = len(FOREX_PAIRS)

    if total_markets == 0:
        return jsonify({
            "status": "ok",
            "engine": "Lion AI PRO V3.7",
            "scanned": 0,
            "batch_size": 0,
            "batch": [],
            "successful": 0,
            "failed": 0,
            "cached_results": 0,
            "results": [],
            "opportunities": []
        })

    batch = []

    for _ in range(min(SCAN_BATCH_SIZE, total_markets)):
        symbol = FOREX_PAIRS[SCAN_INDEX]
        batch.append(symbol)
        SCAN_INDEX = (SCAN_INDEX + 1) % total_markets

    for symbol in batch:
        try:
            result = analyze(symbol)

            if not isinstance(result, dict):
                SCAN_ERRORS[symbol] = "Invalid analysis response"
                continue

            if result.get("status") == "error":
                SCAN_ERRORS[symbol] = result.get(
                    "message",
                    result.get("error", "Analysis error")
                )
                continue

            try:
                score = float(result.get("score", 0))
            except (TypeError, ValueError):
                score = 0.0

            try:
                confidence = float(result.get("confidence", 0))
            except (TypeError, ValueError):
                confidence = 0.0

            signal = str(result.get("signal", "WAIT")).upper()

            SCAN_RESULTS[symbol] = {
                "symbol": symbol,
                "signal": signal,
                "score": score,
                "confidence": confidence,
                "price": result.get("price"),
                "analysis": result.get("analysis", ""),
                "reasons": result.get("reasons", [])
            }

            SCAN_ERRORS.pop(symbol, None)

        except Exception as exc:
            print(f"SCAN ERROR {symbol}: {exc}")
            SCAN_ERRORS[symbol] = str(exc)

    opportunities = [
        item for item in SCAN_RESULTS.values()
        if item.get("signal") in ("BUY", "SELL")
    ]

    opportunities.sort(
        key=lambda item: (
            abs(float(item.get("score", 0))),
            float(item.get("confidence", 0))
        ),
        reverse=True
    )

    all_results = list(SCAN_RESULTS.values())

    all_results.sort(
        key=lambda item: (
            abs(float(item.get("score", 0))),
            float(item.get("confidence", 0))
        ),
        reverse=True
    )

    return jsonify({
        "status": "ok",
        "engine": "Lion AI PRO V3.7",
        "scanned": total_markets,
        "batch_size": len(batch),
        "batch": batch,
        "successful": len(SCAN_RESULTS),
        "failed": len(SCAN_ERRORS),
        "cached_results": len(SCAN_RESULTS),
        "errors": SCAN_ERRORS,
        "results": all_results,
        "opportunities": opportunities[:10]
    })


from paper_trading import get_wallet, open_trade, check_positions, reset_wallet

@app.route("/paper/wallet")
def paper_wallet():
    return jsonify(get_wallet())

@app.route("/paper/open", methods=["POST"])
def paper_open():
    d = request.get_json() or {}
    return jsonify(open_trade(d["symbol"], d["signal"], d["entry"], d["stop_loss"], d["take_profit"]))

@app.route("/paper/check", methods=["POST"])
def paper_check():
    d = request.get_json() or {}
    return jsonify(check_positions(d.get("prices", {})))

@app.route("/paper/reset", methods=["POST"])
def paper_reset():
    return jsonify(reset_wallet())


# ============================================================
# AUTO PAPER TRADING
# ============================================================

from paper_trading import get_wallet, open_trade, check_positions, reset_wallet

@app.route("/paper/auto")
def paper_auto():
    global SCAN_INDEX

    wallet = get_wallet()

    # اول پوزیشن‌های قبلی را با قیمت‌های موجود بررسی کن
    prices = {
        symbol: item.get("price")
        for symbol, item in SCAN_RESULTS.items()
        if item.get("price") is not None
    }

    check = check_positions(prices)
    wallet = get_wallet()

    # اگر معامله باز داریم، معامله جدید باز نکن
    if wallet.get("open_positions", 0) > 0:
        return jsonify({
            "status": "ok",
            "mode": "auto_paper",
            "action": "HOLD",
            "message": "یک معامله Paper باز است",
            "wallet": wallet,
            "closed": check.get("closed", [])
        })

    # فقط سیگنال‌های واقعی BUY/SELL
    opportunities = [
        x for x in SCAN_RESULTS.values()
        if x.get("signal") in ("BUY", "SELL")
        and x.get("price") is not None
    ]

    opportunities.sort(
        key=lambda x: (
            abs(float(x.get("score", 0))),
            float(x.get("confidence", 0))
        ),
        reverse=True
    )

    if not opportunities:
        return jsonify({
            "status": "ok",
            "mode": "auto_paper",
            "action": "WAIT",
            "message": "فعلاً فرصت مناسب پیدا نشد",
            "wallet": wallet,
            "closed": check.get("closed", [])
        })

    best = opportunities[0]

    # برای امنیت Paper Trading فقط وقتی قدرت سیگنال کافی است
    score = float(best.get("score", 0))
    confidence = float(best.get("confidence", 0))

    if abs(score) < 65 or confidence < 65:
        return jsonify({
            "status": "ok",
            "mode": "auto_paper",
            "action": "WAIT",
            "message": "سیگنال هنوز قدرت کافی ندارد",
            "candidate": best,
            "wallet": wallet,
            "closed": check.get("closed", [])
        })

    symbol = best["symbol"]
    signal = best["signal"]
    entry = float(best["price"])

    # چون بعضی نتایج اسکن ممکن است SL/TP نداشته باشند،
    # برای Paper از ATR استفاده می‌کنیم.
    atr = float(best.get("atr") or entry * 0.0005)

    if signal == "BUY":
        stop_loss = entry - atr * 1.5
        take_profit = entry + atr * 2.25
    else:
        stop_loss = entry + atr * 1.5
        take_profit = entry - atr * 2.25

    trade = open_trade(
        symbol,
        signal,
        entry,
        stop_loss,
        take_profit,
        amount=2.0
    )

    return jsonify({
        "status": "ok",
        "mode": "auto_paper",
        "action": "OPEN" if trade.get("status") == "ok" else "ERROR",
        "trade": trade,
        "wallet": get_wallet(),
        "closed": check.get("closed", [])
    })



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )
