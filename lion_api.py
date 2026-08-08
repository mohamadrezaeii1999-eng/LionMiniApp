from flask import Flask, jsonify
from flask_cors import CORS
import lion_real_engine
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

WALLET_FILE = Path.home() / "lion_wallet_v13.json"


def get_wallet():
    try:
        return json.loads(WALLET_FILE.read_text(encoding="utf-8"))
    except:
        return {
            "usd": 166.67,
            "profit": 0,
            "trades": 0,
            "wins": 0,
            "losses": 0
        }


@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "name": "Lion AI PRO"
    })


@app.get("/signal")
def signal():
    try:
        result = lion_real_engine.analyze()

        return jsonify({
            "status": "ok",
            "symbol": "EUR/USD",
            "result": {
                "action": result["signal"],
                "confidence": result["score"],
                "entry": result["price"],
                "ma10": result["ma10"],
                "ma30": result["ma30"],
                "rsi": result["rsi"],
                "macd": result["macd"],
                "trend": result["trend"],
                "time": result["time"]
            }
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.get("/wallet")
def wallet():
    return jsonify(get_wallet())


@app.get("/prices")
def prices():
    return jsonify({
        "BTC": price("BTC/USD"),
        "ETH": price("ETH/USD"),
        "XAU": price("XAU/USD"),
        "EUR": price("EUR/USD")
    })


def price(symbol):
    import requests

    try:
        r = requests.get(
            "https://api.twelvedata.com/price",
            params={
                "symbol": symbol,
                "apikey": lion_real_engine.API_KEY
            },
            timeout=10
        )

        data = r.json()
        return data.get("price", "ناموجود")

    except:
        return "خطا"


app.run(
    host="0.0.0.0",
    port=5000,
    debug=False
)
