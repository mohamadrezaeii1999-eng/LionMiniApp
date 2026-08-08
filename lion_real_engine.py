import requests

API_KEY = "18f69147a18a4e8c9dfc6d4695c22b27"
SYMBOL = "EUR/USD"
INTERVAL = "5min"
OUTPUTSIZE = 100

def get_candles():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": OUTPUTSIZE,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params, timeout=15)
    data = r.json()

    if "values" not in data:
        raise Exception(data)

    candles = []
    for x in data["values"]:
        candles.append({
            "datetime": x["datetime"],
            "open": float(x["open"]),
            "high": float(x["high"]),
            "low": float(x["low"]),
            "close": float(x["close"])
        })

    candles.reverse()
    return candles


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(values, period=14):
    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(len(values)-period, len(values)):
        change = values[i] - values[i-1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def macd(values):
    e12 = ema(values, 12)
    e26 = ema(values, 26)

    if e12 is None or e26 is None:
        return None

    return e12 - e26


def analyze():

    candles = get_candles()
    closes = [x["close"] for x in candles]

    price = closes[-1]
    ma10 = sma(closes, 10)
    ma30 = sma(closes, 30)
    rsi_value = rsi(closes)
    macd_value = macd(closes)

    score = 50

    if ma10 > ma30:
        trend = "BULLISH"
        score += 20
    elif ma10 < ma30:
        trend = "BEARISH"
        score -= 20
    else:
        trend = "NEUTRAL"

    if rsi_value < 30:
        score += 15
    elif rsi_value > 70:
        score -= 15
    elif rsi_value > 50:
        score += 5
    else:
        score -= 5

    if macd_value > 0:
        macd_state = "POSITIVE"
        score += 15
    else:
        macd_state = "NEGATIVE"
        score -= 15

    score = max(0, min(100, score))

    if score >= 75:
        signal = "BUY"
    elif score <= 30:
        signal = "SELL"
    else:
        signal = "WAIT"

    return {
        "price": price,
        "ma10": ma10,
        "ma30": ma30,
        "rsi": rsi_value,
        "macd": macd_value,
        "trend": trend,
        "macd_state": macd_state,
        "score": score,
        "signal": signal,
        "time": candles[-1]["datetime"]
    }


result = analyze()

print()
print("🦁 Lion AI PRO — REAL MARKET ENGINE")
print("=" * 45)
print("📈 Market:", SYMBOL)
print("⏱️ Timeframe:", INTERVAL)
print("💵 Price:", round(result["price"], 5))
print("📊 MA10:", round(result["ma10"], 5))
print("📊 MA30:", round(result["ma30"], 5))
print("📉 RSI:", round(result["rsi"], 2))
print("📈 MACD:", round(result["macd"], 6))
print("🧭 Trend:", result["trend"])
print("🧠 AI Score:", result["score"], "%")
print("🤖 Signal:", result["signal"])
print("🕐 Candle:", result["time"])
print("=" * 45)
