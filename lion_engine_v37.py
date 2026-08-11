import os
import time
import requests

API_URL = "https://api.twelvedata.com/time_series"

DEFAULT_SYMBOL = "EUR/USD"

# ------------------------------------------------------------
# Lion AI PRO V3.7 - Market Data Cache
# جلوگیری از درخواست‌های تکراری به Twelve Data
# ------------------------------------------------------------
DATA_CACHE = {}
CACHE_TTL = 20

TIMEFRAMES = {
    "5min": "5min",
    "15min": "15min",
    "1h": "1h"
}


def get_data(symbol, interval, outputsize=200):
    key = os.getenv("TWELVE_DATA_API_KEY")

    if not key:
        return None, "API key missing"

    symbol = symbol.upper().strip()

    cache_key = (symbol, interval, outputsize)
    now = time.time()

    # Cache duration based on timeframe
    cache_ttl = {
        "5min": 60,
        "15min": 180,
        "1h": 300
    }.get(interval, CACHE_TTL)

    # Return cached data if still fresh
    cached = DATA_CACHE.get(cache_key)

    if cached:
        cached_time, cached_data = cached

        if now - cached_time < cache_ttl:
            return cached_data, None

    try:
        response = requests.get(
            API_URL,
            params={
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": key
            },
            timeout=25
        )

        data = response.json()

        if "values" not in data:
            return None, data.get(
                "message",
                "Market data error"
            )

        candles = []

        for item in reversed(data["values"]):
            try:
                candles.append({
                    "datetime": item["datetime"],
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"])
                })
            except (KeyError, ValueError, TypeError):
                continue

        if len(candles) < 60:
            return None, "Not enough candles"

        # Save successful request in cache
        DATA_CACHE[cache_key] = (
            now,
            candles
        )

        return candles, None

    except Exception as exc:
        return None, str(exc)

def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for value in values[period:]:
        result = (value - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(candles, period=14):
    if len(candles) <= period:
        return None

    true_ranges = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        previous_close = candles[i - 1]["close"]

        true_range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )

        true_ranges.append(true_range)

    return sum(true_ranges[-period:]) / period


def bollinger(values, period=20, multiplier=2):
    if len(values) < period:
        return None, None, None

    middle = sma(values, period)
    window = values[-period:]

    variance = sum(
        (value - middle) ** 2
        for value in window
    ) / period

    std = variance ** 0.5

    return (
        middle - multiplier * std,
        middle,
        middle + multiplier * std
    )


def analyze_timeframe(candles):

    closes = [c["close"] for c in candles]

    price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    ma20 = sma(closes, 20)
    ma50 = sma(closes, 50)

    rsi_value = rsi(closes)
    atr_value = atr(candles)

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)

    macd_value = ema12 - ema26

    macd_history = []

    for i in range(26, len(closes)):
        fast = ema(closes[:i + 1], 12)
        slow = ema(closes[:i + 1], 26)

        if fast is not None and slow is not None:
            macd_history.append(fast - slow)

    macd_signal = ema(macd_history, 9)

    if macd_signal is None:
        macd_signal = macd_value

    macd_hist = macd_value - macd_signal

    lower_band, middle_band, upper_band = bollinger(closes)

    support = min(c["low"] for c in candles[-40:])
    resistance = max(c["high"] for c in candles[-40:])

    previous_high = max(
        c["high"] for c in candles[-21:-1]
    )

    previous_low = min(
        c["low"] for c in candles[-21:-1]
    )

    breakout_up = price > previous_high
    breakout_down = price < previous_low

    score = 0
    reasons = []

    # EMA trend
    if ema9 > ema21 > ema50:
        score += 25
        trend = "BULLISH"
        reasons.append("EMA trend bullish")

    elif ema9 < ema21 < ema50:
        score -= 25
        trend = "BEARISH"
        reasons.append("EMA trend bearish")

    else:
        trend = "NEUTRAL"
        reasons.append("EMA trend neutral")

    # MA structure
    if ma20 > ma50:
        score += 10
        reasons.append("MA20 above MA50")

    elif ma20 < ma50:
        score -= 10
        reasons.append("MA20 below MA50")

    # Price vs EMA21
    if price > ema21:
        score += 10
        reasons.append("Price above EMA21")
    else:
        score -= 10
        reasons.append("Price below EMA21")

    # RSI
    if rsi_value is not None:

        if 52 <= rsi_value < 68:
            score += 15
            reasons.append("RSI bullish momentum")

        elif 32 < rsi_value <= 48:
            score -= 15
            reasons.append("RSI bearish momentum")

        elif rsi_value >= 70:
            score -= 8
            reasons.append("RSI overbought")

        elif rsi_value <= 30:
            score += 8
            reasons.append("RSI oversold")

    # MACD line + histogram
    if macd_value > macd_signal and macd_hist > 0:
        score += 15
        reasons.append("MACD bullish")

    elif macd_value < macd_signal and macd_hist < 0:
        score -= 15
        reasons.append("MACD bearish")

    # Bollinger
    if (
        lower_band is not None
        and upper_band is not None
        and upper_band > lower_band
    ):

        position = (
            price - lower_band
        ) / (upper_band - lower_band)

        if position < 0.15:
            score += 5
            reasons.append("Price near lower Bollinger")

        elif position > 0.85:
            score -= 5
            reasons.append("Price near upper Bollinger")

    # Breakout
    if breakout_up:
        score += 12
        reasons.append("Bullish breakout")

    elif breakout_down:
        score -= 12
        reasons.append("Bearish breakout")

    # Support / resistance proximity
    support_distance = abs(price - support) / price
    resistance_distance = abs(resistance - price) / price

    if support_distance < 0.001:
        score += 5
        reasons.append("Near support")

    if resistance_distance < 0.001:
        score -= 8
        reasons.append("Near resistance")

    # Volatility
    if atr_value is not None and price != 0:
        atr_percent = (atr_value / price) * 100

        if atr_percent < 0.02:
            volatility = "LOW"
        elif atr_percent < 0.08:
            volatility = "NORMAL"
        else:
            volatility = "HIGH"
    else:
        volatility = "UNKNOWN"

    return {
        "price": price,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "ma20": ma20,
        "ma50": ma50,
        "rsi": rsi_value,
        "macd": macd_value,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "atr": atr_value,
        "support": support,
        "resistance": resistance,
        "bollinger_lower": lower_band,
        "bollinger_middle": middle_band,
        "bollinger_upper": upper_band,
        "breakout_up": breakout_up,
        "breakout_down": breakout_down,
        "volatility": volatility,
        "trend": trend,
        "score": score,
        "reasons": reasons
    }


def analyze(symbol=DEFAULT_SYMBOL):

    symbol = symbol.upper().strip()

    results = {}

    for name, interval in TIMEFRAMES.items():

        candles, error = get_data(
            symbol,
            interval
        )

        if error:
            return {
                "status": "error",
                "engine": "Lion AI PRO V3.4",
                "symbol": symbol,
                "timeframe": name,
                "message": error
            }

        results[name] = analyze_timeframe(candles)

    five = results["5min"]
    fifteen = results["15min"]
    one_hour = results["1h"]

    # Multi-timeframe weighted score
    raw_score = (
        five["score"] * 0.40
        + fifteen["score"] * 0.35
        + one_hour["score"] * 0.25
    )

    bullish = sum(
        x["trend"] == "BULLISH"
        for x in [five, fifteen, one_hour]
    )

    bearish = sum(
        x["trend"] == "BEARISH"
        for x in [five, fifteen, one_hour]
    )

    reasons = []

    if bullish == 3:
        raw_score += 15
        reasons.append("تمام تایم‌فریم‌ها صعودی هستند")

    elif bearish == 3:
        raw_score -= 15
        reasons.append("تمام تایم‌فریم‌ها نزولی هستند")

    elif bullish > bearish:
        reasons.append("برتری روند صعودی")

    elif bearish > bullish:
        reasons.append("برتری روند نزولی")

    else:
        reasons.append("تایم‌فریم‌ها هم‌جهت نیستند")

    # Momentum agreement
    bullish_momentum = sum(
        x["macd_hist"] > 0 and x["rsi"] >= 50
        for x in [five, fifteen, one_hour]
    )

    bearish_momentum = sum(
        x["macd_hist"] < 0 and x["rsi"] <= 50
        for x in [five, fifteen, one_hour]
    )

    if bullish_momentum == 3:
        raw_score += 10
        reasons.append("مومنتوم هر سه تایم‌فریم صعودی است")

    elif bearish_momentum == 3:
        raw_score -= 10
        reasons.append("مومنتوم هر سه تایم‌فریم نزولی است")

    # Conflict penalty
    if bullish > 0 and bearish > 0:
        raw_score *= 0.75
        reasons.append("فیلتر تضاد تایم‌فریم فعال شد")

    final_score = max(
        -100,
        min(100, round(raw_score))
    )

    # ============================================================
    # Lion AI PRO - Smart Signal Decision
    # ============================================================

    entry = five["price"]

    # فاصله نرمال‌شده تا حمایت و مقاومت
    atr = max(float(five.get("atr", 0)), entry * 0.0001)

    resistance_distance = max(
        0,
        five["resistance"] - entry
    )

    support_distance = max(
        0,
        entry - five["support"]
    )

    # فاصله نسبت به ATR
    resistance_atr = resistance_distance / atr
    support_atr = support_distance / atr

    # ============================================================
    # Signal candidates
    # ============================================================

    buy_candidate = (
        final_score >= 65
        and bullish >= 2
    )

    sell_candidate = (
        final_score <= -65
        and bearish >= 2
    )

    signal = "WAIT"

    # ============================================================
    # BUY
    # ============================================================


    # ============================================================
    # Confidence
    # ============================================================

    confidence = min(
        95,
        round(50 + abs(final_score) * 0.45, 1)
    )

    # کاهش اعتماد فقط زمانی که تایم‌فریم‌ها واقعاً اختلاف دارند
    if bullish > 0 and bearish > 0:
        confidence = max(
            50,
            round(confidence - 7.5, 1)
        )

    # ============================================================
    # Smart Support / Resistance Filter
    # ============================================================

    # سیگنال‌های خیلی قوی اجازه ورود با فاصله کمتر را دارند،
    # ولی اگر قیمت واقعاً به سطح چسبیده باشد، ورود ممنوع است.
    strong_buy = (
        final_score >= 80
        and bullish == 3
        and confidence >= 80
    )

    strong_sell = (
        final_score <= -80
        and bearish == 3
        and confidence >= 80
    )

    if buy_candidate:

        # سیگنال معمولی: حداقل 0.35 ATR فاصله
        # سیگنال خیلی قوی: حداقل 0.15 ATR فاصله
        minimum_resistance_atr = 0.15 if strong_buy else 0.35

        if resistance_atr < minimum_resistance_atr:
            reasons.append("مقاومت بیش از حد نزدیک است")
            signal = "WAIT"
        else:
            signal = "BUY"

    # ============================================================
    # SELL
    # ============================================================

    elif sell_candidate:

        # سیگنال معمولی: حداقل 0.35 ATR فاصله
        # سیگنال خیلی قوی: حداقل 0.15 ATR فاصله
        minimum_support_atr = 0.15 if strong_sell else 0.35

        if support_atr < minimum_support_atr:
            reasons.append("حمایت بیش از حد نزدیک است")
            signal = "WAIT"
        else:
            signal = "SELL"

    # ============================================================
    # Trade levels
    # ============================================================

    stop_loss = None
    take_profit_1 = None
    take_profit_2 = None
    risk_reward = 0

    if signal == "BUY":

        stop_loss = min(
            entry - atr * 1.5,
            five["support"]
        )

        risk = entry - stop_loss

        if risk > 0:
            take_profit_1 = entry + risk * 1.5
            take_profit_2 = entry + risk * 2.5
            risk_reward = 1.5

    elif signal == "SELL":

        stop_loss = max(
            entry + atr * 1.5,
            five["resistance"]
        )

        risk = stop_loss - entry

        if risk > 0:
            take_profit_1 = entry - risk * 1.5
            take_profit_2 = entry - risk * 2.5
            risk_reward = 1.5

    reasons.extend(five["reasons"])

    return {
        "status": "ok",
        "engine": "Lion AI PRO V3.4",
        "symbol": symbol,
        "signal": signal,
        "score": final_score,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit_1": take_profit_1,
        "take_profit_2": take_profit_2,
        "risk_reward": risk_reward,
        "price": five["price"],
        "rsi": five["rsi"],
        "atr": five["atr"],
        "support": five["support"],
        "resistance": five["resistance"],
        "timeframes": {
            "5min": five,
            "15min": fifteen,
            "1h": one_hour
        },
        "reasons": reasons,
        "analysis": " | ".join(reasons)
    }


# ============================================================
# LION AI PRO V3.6 UPGRADE MODULE
# Trend Strength + Momentum Confirmation + Entry Quality
# ============================================================

def calculate_trend_strength(tf):
    """
    محاسبه قدرت روند از 0 تا 100
    """
    score = 0

    ema9 = tf.get("ema9")
    ema21 = tf.get("ema21")
    ema50 = tf.get("ema50")
    price = tf.get("price")

    if not all(v is not None for v in [ema9, ema21, ema50, price]):
        return 0

    # ترتیب EMAها
    if ema9 > ema21 > ema50:
        score += 45
    elif ema9 < ema21 < ema50:
        score += 45
    else:
        score += 15

    # فاصله قیمت از EMA21
    distance = abs(price - ema21) / price * 100

    if distance > 0.03:
        score += 25
    elif distance > 0.015:
        score += 18
    elif distance > 0.005:
        score += 10

    # امتیاز روند داخلی
    internal_score = abs(tf.get("score", 0))

    score += min(30, internal_score * 0.30)

    return round(min(100, score), 1)


def calculate_momentum_confirmation(tf):
    """
    بررسی تأیید مومنتوم
    خروجی بین -100 تا +100
    """
    momentum = 0

    rsi_value = tf.get("rsi")
    macd = tf.get("macd")
    macd_hist = tf.get("macd_hist")

    if rsi_value is not None:

        if 52 <= rsi_value <= 65:
            momentum += 30

        elif 65 < rsi_value < 70:
            momentum += 15

        elif 48 <= rsi_value < 52:
            momentum += 5

        elif 35 <= rsi_value < 48:
            momentum -= 20

        elif rsi_value < 35:
            momentum -= 10

        elif rsi_value >= 70:
            momentum -= 20

    if macd is not None:

        if macd > 0:
            momentum += 20
        else:
            momentum -= 20

    if macd_hist is not None:

        if macd_hist > 0:
            momentum += 30
        elif macd_hist < 0:
            momentum -= 30

    return max(-100, min(100, momentum))


def calculate_entry_quality(tf, direction):
    """
    کیفیت ورود بین 0 تا 100
    """
    price = tf.get("price")
    support = tf.get("support")
    resistance = tf.get("resistance")
    atr_value = tf.get("atr")

    if not all(
        v is not None
        for v in [price, support, resistance, atr_value]
    ):
        return 0

    quality = 50

    if direction == "BUY":

        distance_resistance = (
            resistance - price
        ) / price * 100

        if distance_resistance > 0.15:
            quality += 30

        elif distance_resistance > 0.08:
            quality += 15

        elif distance_resistance < 0.03:
            quality -= 35

        elif distance_resistance < 0.06:
            quality -= 20

    elif direction == "SELL":

        distance_support = (
            price - support
        ) / price * 100

        if distance_support > 0.15:
            quality += 30

        elif distance_support > 0.08:
            quality += 15

        elif distance_support < 0.03:
            quality -= 35

        elif distance_support < 0.06:
            quality -= 20

    # ATR خیلی پایین = حرکت ناکافی
    if atr_value / price * 100 < 0.01:
        quality -= 10

    return round(max(0, min(100, quality)), 1)


print("🦁 Lion AI PRO V3.6 Upgrade Module Loaded")
