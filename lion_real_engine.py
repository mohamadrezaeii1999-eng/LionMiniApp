import os
import requests
import pandas as pd
import numpy as np

API_URL = "https://api.twelvedata.com/time_series"
DEFAULT_SYMBOL = "EUR/USD"
INTERVAL = "5min"


# تمام بازارهای فارکس Lion AI PRO
FOREX_PAIRS = [
    # Majors
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",

    # Minors
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

    # Exotics
    "USD/TRY",
    "USD/ZAR",
    "USD/MXN",
    "USD/SGD",
    "USD/HKD",
    "USD/NOK",
    "USD/SEK",
    "USD/DKK",
    "EUR/TRY",
    "EUR/SEK",
    "EUR/NOK",
    "GBP/TRY",
]


def get_data(symbol=DEFAULT_SYMBOL):
    key = os.getenv("TWELVE_DATA_API_KEY")

    if not key:
        return None, {
            "status": "error",
            "message": "API key missing"
        }

    try:
        r = requests.get(
            API_URL,
            params={
                "symbol": symbol,
                "interval": INTERVAL,
                "outputsize": 150,
                "apikey": key
            },
            timeout=25
        )

        data = r.json()

    except Exception as e:
        return None, {
            "status": "error",
            "message": str(e)
        }

    if "values" not in data:
        return None, {
            "status": "error",
            "message": data.get(
                "message",
                "Market data error"
            )
        }

    df = pd.DataFrame(data["values"])

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.sort_values(
        "datetime"
    ).reset_index(drop=True)

    df = df.dropna(
        subset=["close"]
    )

    if len(df) < 40:
        return None, {
            "status": "error",
            "message": "Not enough market data"
        }

    return df, None


def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


def analyze(symbol=DEFAULT_SYMBOL):

    symbol = symbol.upper().strip()

    if symbol not in FOREX_PAIRS:
        return {
            "status": "error",
            "message": "Unsupported forex pair",
            "symbol": symbol,
            "supported_pairs": FOREX_PAIRS
        }

    df, error = get_data(symbol)

    if error:
        return error

    close = df["close"]

    # Moving averages
    df["ma10"] = close.rolling(10).mean()
    df["ma30"] = close.rolling(30).mean()

    # RSI
    df["rsi"] = calculate_rsi(close)

    # MACD
    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    df["macd"] = ema12 - ema26

    df["signal_line"] = df["macd"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["histogram"] = (
        df["macd"] -
        df["signal_line"]
    )

    # Support / Resistance
    recent = df.tail(30)

    support = recent["low"].min()
    resistance = recent["high"].max()

    last = df.iloc[-1]

    price = float(last["close"])
    ma10 = float(last["ma10"])
    ma30 = float(last["ma30"])
    rsi = float(last["rsi"])
    macd = float(last["macd"])
    macd_signal = float(last["signal_line"])
    histogram = float(last["histogram"])

    score = 0
    reasons = []

    # Trend
    if ma10 > ma30:
        score += 25
        reasons.append(
            "روند کوتاه‌مدت صعودی"
        )

    elif ma10 < ma30:
        score -= 25
        reasons.append(
            "روند کوتاه‌مدت نزولی"
        )

    else:
        reasons.append(
            "روند خنثی"
        )

    # Price vs MA10
    if price > ma10:
        score += 15
        reasons.append(
            "قیمت بالای MA10"
        )

    else:
        score -= 15
        reasons.append(
            "قیمت پایین MA10"
        )

    # RSI
    if 50 <= rsi < 70:
        score += 20
        reasons.append(
            "RSI مومنتوم صعودی مناسب"
        )

    elif 30 < rsi < 50:
        score -= 20
        reasons.append(
            "RSI مومنتوم نزولی"
        )

    elif rsi >= 70:
        reasons.append(
            "RSI وارد ناحیه اشباع خرید شده"
        )

    elif rsi <= 30:
        reasons.append(
            "RSI وارد ناحیه اشباع فروش شده"
        )

    # MACD
    if (
        macd > macd_signal
        and histogram > 0
    ):
        score += 25
        reasons.append(
            "MACD صعودی"
        )

    elif (
        macd < macd_signal
        and histogram < 0
    ):
        score -= 25
        reasons.append(
            "MACD نزولی"
        )

    else:
        reasons.append(
            "MACD بدون تأیید قوی"
        )

    # Support / Resistance
    if price > resistance * 0.9995:
        score += 5
        reasons.append(
            "قیمت نزدیک مقاومت"
        )

    elif price < support * 1.0005:
        score -= 5
        reasons.append(
            "قیمت نزدیک حمایت"
        )

    # Final signal
    if score >= 45:
        signal = "BUY"

    elif score <= -45:
        signal = "SELL"

    else:
        signal = "WAIT"

    confidence = min(
        95,
        max(
            50,
            50 + abs(score) / 2
        )
    )

    return {
        "status": "ok",
        "symbol": symbol,
        "interval": INTERVAL,
        "price": round(price, 5),
        "ma10": round(ma10, 5),
        "ma30": round(ma30, 5),
        "rsi": round(rsi, 2),
        "macd": round(macd, 6),
        "macd_signal": round(
            macd_signal,
            6
        ),
        "support": round(
            float(support),
            5
        ),
        "resistance": round(
            float(resistance),
            5
        ),
        "score": round(score, 1),
        "confidence": round(
            confidence,
            1
        ),
        "signal": signal,
        "reasons": reasons,
        "analysis": " | ".join(
            reasons
        )
    }
