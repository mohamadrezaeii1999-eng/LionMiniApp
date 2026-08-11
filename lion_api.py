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


@app.get("/scan")
def scan():
    results = []
    errors = []

    for symbol in FOREX_PAIRS:
        try:
            result = analyze(symbol)

            if not isinstance(result, dict):
                errors.append({
                    "symbol": symbol,
                    "error": "Invalid analysis response"
                })
                continue

            if result.get("status") == "error":
                errors.append({
                    "symbol": symbol,
                    "error": result.get("error", "Analysis error")
                })
                continue

            signal_value = result.get("signal", "WAIT")

            try:
                score_num = float(result.get("score", 0))
            except (TypeError, ValueError):
                score_num = 0

            try:
                confidence_num = float(result.get("confidence", 0))
            except (TypeError, ValueError):
                confidence_num = 0

            results.append({
                "symbol": symbol,
                "signal": signal_value,
                "score": score_num,
                "confidence": confidence_num,
                "price": result.get("price"),
                "analysis": result.get("analysis", ""),
                "reasons": result.get("reasons", [])
            })

        except Exception as exc:
            print(f"SCAN ERROR {symbol}: {exc}")

            errors.append({
                "symbol": symbol,
                "error": str(exc)
            })

    opportunities = [
        item for item in results
        if item["signal"] in ("BUY", "SELL")
    ]

    opportunities.sort(
        key=lambda item: (
            abs(item["score"]),
            item["confidence"]
        ),
        reverse=True
    )

    return jsonify({
        "status": "ok",
        "engine": "Lion AI PRO V3.7",
        "scanned": len(FOREX_PAIRS),
        "successful": len(results),
        "failed": len(errors),
        "opportunities": opportunities[:10],
        "errors": errors
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )
