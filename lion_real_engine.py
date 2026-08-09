import requests
import pandas as pd

TWELVE_DATA_API_KEY = __import__("os").environ.get("TWELVE_DATA_API_KEY", "")

def get_signal():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "EUR/USD",
        "interval": "5min",
        "outputsize": 100,
        "apikey": TWELVE_DATA_API_KEY
    }

    r = requests.get(url, params=params, timeout=15)
    data = r.json()

    if "values" not in data:
        return {
            "status": "error",
            "signal": "WAIT",
            "message": data.get("message", "Market data error")
        }

    df = pd.DataFrame(data["values"])
    df["close"] = pd.to_numeric(df["close"])
    df = df.sort_values("datetime")

    df["ma10"] = df["close"].rolling(10).mean()
    df["ma30"] = df["close"].rolling(30).mean()

    price = df["close"].iloc[-1]
    ma10 = df["ma10"].iloc[-1]
    ma30 = df["ma30"].iloc[-1]

    if ma10 > ma30 and price > ma10:
        signal = "BUY"
    elif ma10 < ma30 and price < ma10:
        signal = "SELL"
    else:
        signal = "WAIT"

    return {
        "status": "ok",
        "symbol": "EUR/USD",
        "price": round(float(price), 5),
        "ma10": round(float(ma10), 5),
        "ma30": round(float(ma30), 5),
        "signal": signal
    }
