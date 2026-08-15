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


@app.get("/candles")
def candles():
    symbol = request.args.get("symbol", "EUR/USD").upper().strip()
    interval = request.args.get("interval", "5min")

    if interval not in ("5min", "15min", "1h"):
        return jsonify({
            "status": "error",
            "message": "تایم‌فریم نامعتبر است"
        }), 400

    try:
        from lion_engine_v37 import get_data

        data, error = get_data(
            symbol,
            interval,
            outputsize=120
        )

        if error or not data:
            return jsonify({
                "status": "error",
                "symbol": symbol,
                "interval": interval,
                "message": error or "داده کندل در دسترس نیست",
                "candles": []
            })

        return jsonify({
            "status": "ok",
            "engine": "Lion AI PRO V3.7",
            "symbol": symbol,
            "interval": interval,
            "count": len(data),
            "candles": data
        })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "symbol": symbol,
            "interval": interval,
            "message": str(exc),
            "candles": []
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

SCAN_BATCH_SIZE = 4

# حداکثر عمر نتیجه اسکن برای Auto Paper Trading
SCAN_RESULT_MAX_AGE = 900

SCAN_INDEX = 0
SCAN_RESULTS = {}
SCAN_ERRORS = {}
LAST_SCAN_SYMBOL = None
LAST_SCAN_TIME = None
AUTO_SCANNER_STATUS = "starting"


@app.get("/paper/auto/status")
def auto_scanner_status():
    return jsonify({
        "status": "ok",
        "scanner": {
            "enabled": AUTO_SCAN_ENABLED if "AUTO_SCAN_ENABLED" in globals() else False,
            "worker_status": AUTO_SCANNER_STATUS,
            "batch_size": SCAN_BATCH_SIZE,
            "total_markets": len(FOREX_PAIRS),
            "scanned_results": len(SCAN_RESULTS),
            "errors": len(SCAN_ERRORS),
            "last_symbol": LAST_SCAN_SYMBOL,
            "last_scan_time": LAST_SCAN_TIME
        },
        "results": list(SCAN_RESULTS.values()),
        "errors": SCAN_ERRORS
    })



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
    batch_successful = 0

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

                # نتیجه قبلی این نماد دیگر معتبر نیست
                SCAN_RESULTS.pop(symbol, None)

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
                "reasons": result.get("reasons", []),
                "scanned_at": time.time()
            }

            SCAN_ERRORS.pop(symbol, None)
            batch_successful += 1

        except Exception as exc:
            print(f"SCAN ERROR {symbol}: {exc}")
            SCAN_ERRORS[symbol] = str(exc)

            # جلوگیری از استفاده از سیگنال قدیمی
            SCAN_RESULTS.pop(symbol, None)

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
        "successful": batch_successful,
        "failed": sum(1 for symbol in batch if symbol in SCAN_ERRORS),
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
    now = time.time()

    opportunities = [
        x for x in SCAN_RESULTS.values()
        if x.get("signal") in ("BUY", "SELL")
        and x.get("price") is not None
        and x.get("scanned_at") is not None
        and now - float(x.get("scanned_at", 0)) <= SCAN_RESULT_MAX_AGE
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

    if abs(score) < 45 or confidence < 55:
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

    # --------------------------------------------------------
    # Fresh Data Guard
    # معامله خودکار فقط با داده تازه مجاز است.
    # --------------------------------------------------------
    try:
        from lion_engine_v37 import get_data_freshness

        freshness = get_data_freshness(symbol)

        if not freshness.get("fresh", False):
            return jsonify({
                "status": "ok",
                "mode": "auto_paper",
                "action": "WAIT",
                "message": "داده بازار برای معامله خودکار به اندازه کافی تازه نیست",
                "candidate": best,
                "freshness": freshness,
                "wallet": wallet,
                "closed": check.get("closed", [])
            })

    except Exception as exc:
        return jsonify({
            "status": "ok",
            "mode": "auto_paper",
            "action": "WAIT",
            "message": "Fresh Data Guard فعال نشد؛ معامله متوقف شد",
            "error": str(exc),
            "candidate": best,
            "wallet": wallet,
            "closed": check.get("closed", [])
        })

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




# ============================================================
# REAL AUTO SCANNER + PAPER TRADING WORKER
# ============================================================

import threading
import time

AUTO_SCAN_INTERVAL = 600
AUTO_SCAN_ENABLED = True


def auto_scanner_worker():
    print("AUTO SCANNER WORKER STARTED")

    global LAST_SCAN_SYMBOL, LAST_SCAN_TIME, AUTO_SCANNER_STATUS

    while AUTO_SCAN_ENABLED:
        try:
            with app.test_request_context():
                scan_response = scan()
                scan_data = scan_response.get_json() or {}

                batch = scan_data.get("batch", [])
                errors = scan_data.get("errors", {})
                successful = int(scan_data.get("successful", 0))

                LAST_SCAN_SYMBOL = batch[-1] if batch else None
                LAST_SCAN_TIME = time.time()

                # اگر Twelve Data سهمیه‌اش تمام شده، Worker وارد Standby شود
                error_text = " ".join(
                    str(v) for v in errors.values()
                ).lower()

                quota_error = (
                    "quota" in error_text
                    or "credits" in error_text
                    or "run out" in error_text
                    or "daily limit" in error_text
                )

                if quota_error and successful == 0:
                    AUTO_SCANNER_STATUS = "quota_standby"

                    print(
                        "AUTO SCANNER: QUOTA STANDBY",
                        "errors=", len(errors)
                    )

                    time.sleep(3600)
                    continue

                AUTO_SCANNER_STATUS = "running"

                print(
                    "SCANNED:",
                    batch,
                    "successful=",
                    successful,
                    "errors=",
                    scan_data.get("failed", 0)
                )

                # فقط وقتی نتیجه معتبر داریم Paper Trading اجرا شود
                if successful > 0:
                    result = paper_auto()

                    try:
                        data = result.get_json() or {}
                        print(
                            "AUTO PAPER:",
                            data.get("action"),
                            data.get("message", ""),
                            data.get("wallet", {})
                        )
                    except Exception:
                        print("AUTO PAPER COMPLETED")
                else:
                    print("AUTO PAPER: SKIPPED - NO VALID MARKET DATA")

        except Exception as exc:
            AUTO_SCANNER_STATUS = "error"
            print(f"AUTO SCANNER ERROR: {exc}")

        time.sleep(AUTO_SCAN_INTERVAL)


threading.Thread(
    target=auto_scanner_worker,
    daemon=True,
    name="auto-paper-scanner"
).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )

# ============================================================
# 🦁 LION AI PRO — MINI APP FULL API CONNECT
# ============================================================

from flask import jsonify, request

# ------------------------------------------------------------
# WALLET
# ------------------------------------------------------------

@app.get("/wallet")
def miniapp_wallet():
    try:
        # اول Paper Wallet
        try:
            from paper_trading import get_wallet
            wallet = get_wallet()

            return jsonify({
                "status": "ok",
                "mode": "paper",
                "wallet": wallet
            })
        except Exception:
            pass

        # سپس Wallet Engine واقعی، اگر موجود بود
        try:
            import wallet_engine

            return jsonify({
                "status": "ok",
                "mode": "real",
                "toman": wallet_engine.wallet.get("toman", 0),
                "usd": wallet_engine.wallet.get("usd", 0),
                "crypto": wallet_engine.wallet.get("crypto", {}),
                "history": wallet_engine.wallet.get("history", [])
            })
        except Exception as exc:
            return jsonify({
                "status": "ok",
                "mode": "paper",
                "wallet": {},
                "message": "Wallet engine در Railway فعال نیست",
                "error": str(exc)
            })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# HISTORY
# ------------------------------------------------------------

@app.get("/history")
def miniapp_history():
    try:
        import os
        import json

        possible_files = [
            "trade_history.json",
            "paper_history.json",
            "paper_wallet.json"
        ]

        for filename in possible_files:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    return jsonify({
                        "status": "ok",
                        "file": filename,
                        "history": data
                    })
                except Exception:
                    continue

        # اگر paper_trading تاریخچه دارد
        try:
            from paper_trading import get_wallet

            wallet = get_wallet()

            return jsonify({
                "status": "ok",
                "history": wallet.get("history", []),
                "trades": wallet.get("trades", [])
            })
        except Exception:
            pass

        return jsonify({
            "status": "ok",
            "history": [],
            "trades": []
        })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
            "history": []
        }), 500


# ------------------------------------------------------------
# PAPER STATUS
# ------------------------------------------------------------

@app.get("/paper/status")
def miniapp_paper_status():
    try:
        # سیستم paper_trading اصلی
        try:
            from paper_trading import get_wallet

            wallet = get_wallet()

            enabled = bool(
                wallet.get("enabled", False)
                or wallet.get("running", False)
                or wallet.get("auto_trading", False)
            )

            return jsonify({
                "status": "ok",
                "enabled": enabled,
                "mode": "PAPER",
                "wallet": wallet
            })

        except Exception:
            pass

        # auto scanner
        enabled = globals().get(
            "AUTO_SCAN_ENABLED",
            False
        )

        return jsonify({
            "status": "ok",
            "enabled": bool(enabled),
            "mode": "PAPER",
            "wallet": {}
        })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "enabled": False,
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# PAPER START
# ------------------------------------------------------------

@app.post("/paper/start")
def miniapp_paper_start():
    try:

        # اگر paper_trading start داشته باشد
        try:
            import paper_trading

            if hasattr(paper_trading, "start"):
                result = paper_trading.start()

                return jsonify({
                    "ok": True,
                    "status": "ok",
                    "enabled": True,
                    "mode": "PAPER",
                    "state": result
                })
        except Exception as exc:
            print("paper_trading.start:", exc)

        # Auto scanner را روشن کن
        global AUTO_SCAN_ENABLED

        AUTO_SCAN_ENABLED = True

        return jsonify({
            "ok": True,
            "status": "ok",
            "enabled": True,
            "mode": "PAPER",
            "message": "Paper Trading فعال شد"
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "status": "error",
            "enabled": False,
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# PAPER STOP
# ------------------------------------------------------------

@app.post("/paper/stop")
def miniapp_paper_stop():
    try:

        # اگر paper_trading stop داشته باشد
        try:
            import paper_trading

            if hasattr(paper_trading, "stop"):
                result = paper_trading.stop()

                return jsonify({
                    "ok": True,
                    "status": "ok",
                    "enabled": False,
                    "mode": "PAPER",
                    "state": result
                })
        except Exception as exc:
            print("paper_trading.stop:", exc)

        # Auto scanner را خاموش کن
        global AUTO_SCAN_ENABLED

        AUTO_SCAN_ENABLED = False

        return jsonify({
            "ok": True,
            "status": "ok",
            "enabled": False,
            "mode": "PAPER",
            "message": "Paper Trading متوقف شد"
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "status": "error",
            "enabled": False,
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# PAPER WALLET
# ------------------------------------------------------------

@app.get("/paper/wallet")
def miniapp_paper_wallet():
    try:
        from paper_trading import get_wallet

        return jsonify({
            "status": "ok",
            **get_wallet()
        })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# PAPER RESET
# ------------------------------------------------------------

@app.post("/paper/reset")
def miniapp_paper_reset():
    try:
        from paper_trading import reset_wallet

        return jsonify(reset_wallet())

    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# MINI APP HEALTH
# ------------------------------------------------------------

@app.get("/miniapp/status")
def miniapp_status():
    return jsonify({
        "status": "ok",
        "app": "Lion AI PRO",
        "engine": "Lion AI PRO V3.7",
        "mini_app": True,
        "markets": len(FOREX_PAIRS)
    })


print("🦁 LION AI PRO FULL MINI APP API READY")

