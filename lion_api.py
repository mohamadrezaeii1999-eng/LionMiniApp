import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "app": "Lion AI PRO"
    })

@app.get("/signal")
def signal():
    key = os.getenv("TWELVE_DATA_API_KEY", "").strip()

    result = {
        "railway_key_loaded": bool(key),
        "key_length": len(key)
    }

    if not key:
        result["problem"] = "TWELVE_DATA_API_KEY is NOT reaching the app"
        return jsonify(result), 500

    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": "EUR/USD",
                "interval": "5min",
                "outputsize": 10,
                "apikey": key
            },
            timeout=20
        )

        data = r.json()

        result["twelvedata_status"] = data.get("status")
        result["twelvedata_message"] = data.get("message", "OK")

        if "values" in data:
            result["market_connection"] = "OK"
            result["latest_price"] = data["values"][0]["close"]
        else:
            result["market_connection"] = "FAILED"

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "railway_key_loaded": True,
            "problem": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
