import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from lion_real_engine import analyze, FOREX_PAIRS, DEFAULT_SYMBOL

app = Flask(__name__)
CORS(app)


@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "app": "Lion AI PRO",
        "engine": "real",
        "markets": FOREX_PAIRS
    })


@app.get("/markets")
def markets():
    return jsonify({
        "status": "ok",
        "markets": FOREX_PAIRS
    })


@app.get("/signal")
def signal():
    symbol = request.args.get("symbol", DEFAULT_SYMBOL).strip().upper()

    if symbol not in FOREX_PAIRS:
        return jsonify({
            "status": "error",
            "message": "Unsupported market",
            "symbol": symbol,
            "supported_pairs": FOREX_PAIRS
        }), 400

    return jsonify(analyze(symbol))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
