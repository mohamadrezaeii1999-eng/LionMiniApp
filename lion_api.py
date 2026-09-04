import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, request, redirect
import requests
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
            "enabled": get_paper_enabled(),
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

    while True:
        try:
            # فقط کنترل داخل Mini App
            if not get_paper_enabled():
                AUTO_SCANNER_STATUS = "disabled"
                time.sleep(5)
                continue
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
PAPER_TRADING_ENABLED = False
# ------------------------------------------------------------


PAPER_STATE_FILE = "paper_state.json"

def get_paper_enabled():
    try:
        import json
        with open(PAPER_STATE_FILE, "r") as f:
            return bool(json.load(f).get("enabled", False))
    except Exception:
        return False

def set_paper_enabled(value):
    import json
    with open(PAPER_STATE_FILE, "w") as f:
        json.dump({"enabled": bool(value)}, f)

@app.get("/paper/status")
def miniapp_paper_status():
    try:
        wallet = {}

        try:
            from paper_trading import get_wallet
            wallet = get_wallet() or {}
        except Exception:
            wallet = {}

        return jsonify({
            "status": "ok",
            "enabled": get_paper_enabled(),
            "mode": "PAPER",
            "wallet": wallet
        })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "enabled": get_paper_enabled(),
            "mode": "PAPER",
            "error": str(exc)
        }), 500


@app.post("/paper/start")
def miniapp_paper_start():
    try:
        set_paper_enabled(True)

        try:
            import paper_trading
            if hasattr(paper_trading, "start"):
                paper_trading.start()
        except Exception as exc:
            print("PAPER START INTERNAL:", exc)

        return jsonify({
            "ok": True,
            "status": "ok",
            "enabled": True,
            "mode": "PAPER",
            "message": "Paper Trading فعال شد"
        })

    except Exception as exc:
        set_paper_enabled(False)

        return jsonify({
            "ok": False,
            "status": "error",
            "enabled": False,
            "mode": "PAPER",
            "error": str(exc)
        }), 500


@app.post("/paper/stop")
def miniapp_paper_stop():
    try:
        set_paper_enabled(False)

        try:
            import paper_trading
            if hasattr(paper_trading, "stop"):
                paper_trading.stop()
        except Exception as exc:
            print("PAPER STOP INTERNAL:", exc)

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
            "mode": "PAPER",
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



# ------------------------------------------------------------
# cTrader - DEMO ACCOUNT INFO (READ ONLY)
# ------------------------------------------------------------
@app.get("/ctrader/account")
def ctrader_account():
    import os
    import requests

    token = os.getenv("CTRADER_ACCESS_TOKEN")
    account_id = "48501253"

    if not token:
        return jsonify({
            "ok": False,
            "error": "CTRADER_ACCESS_TOKEN is not configured"
        }), 500

    if not account_id:
        return jsonify({
            "ok": False,
            "error": "CTRADER_ACCOUNT_ID is not configured"
        }), 500

    try:
        r = requests.get(
            "https://api.spotware.com/connect/tradingaccounts",
            params={"oauth_token": token},
            timeout=15
        )

        return jsonify({
            "ok": r.ok,
            "http_status": r.status_code,
            "account_id": account_id,
            "data": r.json()
        }), r.status_code

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 500



@app.get("/ctrader/sdk-test")
def ctrader_sdk_test():
    try:
        import ctrader_open_api
        return jsonify({
            "ok": True,
            "sdk": "ctrader-open-api",
            "message": "CTRADER SDK OK"
        })
    except Exception as exc:
        return jsonify({
            "ok": False,
            "sdk": "ctrader-open-api",
            "error": str(exc)
        }), 500

print("🦁 LION AI PRO FULL MINI APP API READY")


# ------------------------------------------------------------
# cTrader Open API - CONNECTION TEST
# ------------------------------------------------------------

@app.get("/ctrader/connection-test")
def ctrader_connection_test():
    import os

    return jsonify({
        "ok": True,
        "ctrader": True,
        "environment": "demo",
        "account_id": os.getenv("CTRADER_ACCOUNT_ID"),
        "access_token_configured": bool(
            os.getenv("CTRADER_ACCESS_TOKEN")
        ),
        "client_id_configured": bool(
            os.getenv("CTRADER_CLIENT_ID")
        ),
        "client_secret_configured": bool(
            os.getenv("CTRADER_CLIENT_SECRET")
        ),
        "endpoint": "demo.ctraderapi.com:5035"
    }), 200


@app.get("/ctrader/trading-ready")
def ctrader_trading_ready():
    import os

    token = os.getenv("CTRADER_ACCESS_TOKEN")
    account_id = "48501253"
    client_id = os.getenv("CTRADER_CLIENT_ID")
    client_secret = os.getenv("CTRADER_CLIENT_SECRET")

    missing = []

    if not token:
        missing.append("CTRADER_ACCESS_TOKEN")

    if not account_id:
        missing.append("CTRADER_ACCOUNT_ID")

    if not client_id:
        missing.append("CTRADER_CLIENT_ID")

    if not client_secret:
        missing.append("CTRADER_CLIENT_SECRET")

    if missing:
        return jsonify({
            "ok": False,
            "trading_ready": False,
            "missing": missing
        }), 400

    return jsonify({
        "ok": True,
        "trading_ready": True,
        "environment": "demo",
        "account_id": account_id,
        "message": "cTrader credentials are configured"
    }), 200


# ------------------------------------------------------------
# cTrader - DEMO TRADE TEST
# ------------------------------------------------------------

@app.get("/ctrader/trade-test")
def ctrader_trade_test():
    import os

    token = os.getenv("CTRADER_ACCESS_TOKEN")
    account_id = "48501253"
    client_id = os.getenv("CTRADER_CLIENT_ID")
    client_secret = os.getenv("CTRADER_CLIENT_SECRET")

    if not all([token, account_id, client_id, client_secret]):
        return jsonify({
            "ok": False,
            "trade_test": False,
            "error": "cTrader credentials are incomplete"
        }), 400

    try:
        from ctrader_open_api import Client, TcpProtocol

        client = Client(
            "demo.ctraderapi.com",
            5035,
            TcpProtocol
        )

        return jsonify({
            "ok": True,
            "trade_test": True,
            "environment": "demo",
            "account_id": account_id,
            "connection": "SDK initialized",
            "endpoint": "demo.ctraderapi.com:5035",
            "message": "Ready for symbol lookup. NO ORDER SENT."
        }), 200

    except Exception as exc:
        return jsonify({
            "ok": False,
            "trade_test": False,
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# cTrader - EUR/USD SYMBOL LOOKUP
# NO ORDER IS SENT
# ------------------------------------------------------------




@app.get("/ctrader/network-test")
def ctrader_network_test():
    import socket
    import ssl
    import time

    host = "demo.ctraderapi.com"
    port = 5035

    result = {
        "ok": False,
        "host": host,
        "port": port,
        "tcp": False,
        "tls": False
    }

    sock = None

    try:
        sock = socket.create_connection((host, port), timeout=10)
        result["tcp"] = True

        context = ssl.create_default_context()

        tls_sock = context.wrap_socket(sock, server_hostname=host)
        result["tls"] = True
        result["message"] = "TCP + TLS connection to cTrader Demo succeeded."

        tls_sock.close()
        result["ok"] = True
        return jsonify(result), 200

    except Exception as exc:
        result["error"] = str(exc)
        return jsonify(result), 500

    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass

@app.get("/ctrader/symbol-lookup")
def ctrader_symbol_lookup():
    import os
    import threading

    token = os.getenv("CTRADER_ACCESS_TOKEN")
    account_id = "48501253"
    client_id = os.getenv("CTRADER_CLIENT_ID")
    client_secret = os.getenv("CTRADER_CLIENT_SECRET")

    if not all([token, account_id, client_id, client_secret]):
        return jsonify({
            "ok": False,
            "symbol_lookup": False,
            "error": "cTrader credentials are incomplete"
        }), 400

    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq,
            ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,
            ProtoOAAccountAuthRes,
            ProtoOASymbolsListReq,
            ProtoOASymbolsListRes
        )
        from twisted.internet import reactor

        result = {
            "ok": False,
            "symbol_lookup": False,
            "environment": "demo",
            "account_id": account_id,
            "symbols": []
        }

        client = Client(
            "demo.ctraderapi.com",
            5035,
            TcpProtocol
        )

        def on_error(failure):
            result["error"] = str(failure)

        def on_message(client_obj, message):
            try:
                payload = Protobuf.extract(message)

                if isinstance(payload, ProtoOAApplicationAuthRes):
                    req = ProtoOAAccountAuthReq()
                    req.ctidTraderAccountId = int(account_id)
                    req.accessToken = token
                    client_obj.send(req).addErrback(on_error)

                elif isinstance(payload, ProtoOAAccountAuthRes):
                    req = ProtoOASymbolsListReq()
                    req.ctidTraderAccountId = int(account_id)
                    req.includeArchivedSymbols = False
                    client_obj.send(req).addErrback(on_error)

                elif isinstance(payload, ProtoOASymbolsListRes):
                    for symbol in payload.symbol:
                        name = getattr(symbol, "symbolName", "")
                        clean = name.upper().replace(" ", "")

                        if clean in ("EUR/USD", "EURUSD"):
                            result["symbols"].append({
                                "symbol_id": int(symbol.symbolId),
                                "symbol_name": name
                            })

                    result["ok"] = True
                    result["symbol_lookup"] = True
                    result["message"] = "EUR/USD lookup completed. NO ORDER SENT."

                    reactor.callFromThread(client_obj.stopService)

            except Exception as exc:
                result["error"] = str(exc)

        def connected(client_obj):
            req = ProtoOAApplicationAuthReq()
            req.clientId = client_id
            req.clientSecret = client_secret
            client_obj.send(req).addErrback(on_error)

        client.setConnectedCallback(connected)
        client.setMessageReceivedCallback(on_message)

        client.startService()

        thread = threading.Thread(
            target=reactor.run,
            kwargs={"installSignalHandlers": False},
            daemon=True
        )
        thread.start()

        # Wait for result
        import time
        deadline = time.time() + 15

        while time.time() < deadline:
            if result["ok"] or "error" in result:
                break
            time.sleep(0.1)

        if not result["ok"]:
            if "error" not in result:
                result["error"] = "No response from cTrader within 15 seconds"
            return jsonify(result), 500

        return jsonify(result), 200

    except Exception as exc:
        return jsonify({
            "ok": False,
            "symbol_lookup": False,
            "environment": "demo",
            "error": str(exc)
        }), 500

@app.get("/ctrader/callback")
def ctrader_callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return jsonify({"ok": False, "error": error}), 400

    if not code:
        return jsonify({
            "ok": False,
            "error": "Authorization code not found"
        }), 400

    client_id = os.getenv("CTRADER_CLIENT_ID")
    client_secret = os.getenv("CTRADER_CLIENT_SECRET")

    if not client_id or not client_secret:
        return jsonify({
            "ok": False,
            "error": "cTrader credentials are missing in Railway Variables"
        }), 500

    redirect_uri = "https://lionminiapp-production-a934.up.railway.app/ctrader/callback"

    try:
        response = requests.get(
            "https://openapi.ctrader.com/apps/token",
            params={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret
            },
            timeout=20
        )

        data = response.json()

        if not data.get("accessToken"):
            return jsonify({
                "ok": False,
                "error": data.get("errorCode") or "Token exchange failed",
                "description": data.get("description")
            }), 400

        return jsonify({
            "ok": True,
            "message": "cTrader connected successfully",
            "token_received": True,
            "expires_in": data.get("expiresIn"),
            "refresh_token_received": bool(data.get("refreshToken"))
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 500


@app.get("/ctrader/connect")
def ctrader_connect():
    client_id = os.getenv("CTRADER_CLIENT_ID")

    if not client_id:
        return {"ok": False, "error": "CTRADER_CLIENT_ID is missing"}, 500

    redirect_uri = "https://lionminiapp-production-a934.up.railway.app/ctrader/callback"

    oauth_url = (
        "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
        "?client_id=" + client_id +
        "&redirect_uri=" + redirect_uri +
        "&scope=trading" +
        "&product=web"
    )

    return redirect(oauth_url)

# cTrader - SMALL DEMO ORDER
@app.get("/ctrader/small-order")
def ctrader_small_order():
    token = os.getenv("CTRADER_ACCESS_TOKEN")
    account_id = "48501253"
    client_id = os.getenv("CTRADER_CLIENT_ID")
    client_secret = os.getenv("CTRADER_CLIENT_SECRET")

    if not all([token, account_id, client_id, client_secret]):
        return {
            "ok": False,
            "error": "cTrader credentials are incomplete"
        }, 400

    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq,
            ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,
            ProtoOAAccountAuthRes,
            ProtoOANewOrderReq,
            ProtoOAExecutionEvent,
            ProtoOAOrderErrorEvent
        )

        client = Client(
            "demo.ctraderapi.com",
            5035,
            TcpProtocol
        )

        result = {
            "ok": False,
            "account_id": account_id,
            "symbol": "EURUSD",
            "volume": 1000
        }

        def on_message(payload):
            if isinstance(payload, ProtoOAApplicationAuthRes):
                req = ProtoOAAccountAuthReq()
                req.ctidTraderAccountId = int(account_id)
                req.accessToken = token
                client.send(req)

            elif isinstance(payload, ProtoOAAccountAuthRes):
                req = ProtoOANewOrderReq()
                req.ctidTraderAccountId = int(account_id)
                req.symbolId = 1
                req.orderType = 1
                req.tradeSide = 1
                req.volume = 1000
                client.send(req)

            elif isinstance(payload, ProtoOAExecutionEvent):
                if payload.HasField("order"):
                    result["ok"] = True
                    result["order_id"] = str(payload.order.orderId)
                    result["execution_type"] = str(payload.executionType)
                elif payload.HasField("errorCode"):
                    result["error"] = str(payload.errorCode)

            elif isinstance(payload, ProtoOAOrderErrorEvent):
                result["error"] = str(payload.errorCode)
                if payload.HasField("description"):
                    result["description"] = str(payload.description)

        client.setMessageReceivedCallback(on_message)

        auth = ProtoOAApplicationAuthReq()
        auth.clientId = client_id
        auth.clientSecret = client_secret
        client.send(auth)

        import time
        for _ in range(50):
            if result["ok"]:
                break
            time.sleep(0.1)

        client.stopService()

        return result

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }, 500

