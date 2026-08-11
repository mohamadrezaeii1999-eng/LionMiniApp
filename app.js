const API = "https://lionminiapp-production.up.railway.app";

let selectedSymbol = "EUR/USD";
let lastData = null;

const SIGNAL_TEXT = {
    BUY: "خرید",
    SELL: "فروش",
    WAIT: "انتظار"
};

const SIGNAL_CLASS = {
    BUY: "buy",
    SELL: "sell",
    WAIT: "wait"
};


function showPage(id, button) {
    document.querySelectorAll(".page").forEach(function(page) {
        page.classList.remove("active");
    });

    const target = document.getElementById(id);

    if (target) {
        target.classList.add("active");
    }

    document.querySelectorAll(".nav button").forEach(function(btn) {
        btn.classList.remove("active");
    });

    if (button) {
        button.classList.add("active");
    }
}


async function loadMarkets() {
    const container = document.getElementById("marketsList");

    if (!container) return;

    container.innerHTML =
        '<div class="market-loading">در حال دریافت  بازارهای Forex...</div>';

    try {
        const response = await fetch(`${API}/markets`, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("خطا در دریافت بازارها");
        }

        const data = await response.json();

        if (
            data.status !== "ok" ||
            !Array.isArray(data.markets)
        ) {
            throw new Error("فرمت بازارها نامعتبر است");
        }

        container.innerHTML = "";

        data.markets.forEach(function(symbol) {
            const market = document.createElement("div");
            market.className = "market";

            const name = document.createElement("span");
            name.textContent = symbol;

            const button = document.createElement("button");
            button.textContent = "انتخاب";
            button.type = "button";

            button.addEventListener("click", function() {
                selectMarket(symbol);
            });

            market.appendChild(name);
            market.appendChild(button);
            container.appendChild(market);
        });

        console.log(
            "🦁 Lion AI Markets:",
            data.markets.length,
            data.markets
        );

    } catch (error) {
        console.error("🦁 Markets Error:", error);

        container.innerHTML =
            '<div class="market-loading">🔴 دریافت بازارها ناموفق بود</div>';
    }
}

async function loadSignal() {
    const status = document.getElementById("globalStatus");

    if (status) {
        status.textContent = "در حال دریافت تحلیل واقعی بازار...";
    }

    try {
        const response = await fetch(
            `${API}/signal?symbol=${encodeURIComponent(selectedSymbol)}`,
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        console.log("🦁 Lion AI:", selectedSymbol, data);

        if (!response.ok || data.status !== "ok") {
            throw new Error(data.message || data.error || "خطای تحلیل");
        }

        lastData = data;

        setText("selectedMarket", data.symbol || selectedSymbol);
        setText("price", data.price ?? "---");
        setText("aPrice", data.price ?? "---");
        setText("score", data.score ?? "---");
        setText("aScore", data.score ?? "---");
        setText("confidence", data.confidence != null ? data.confidence + "%" : "---");
        setText("rsi", data.rsi ?? "---");
        setText("ma10", data.ma10 ?? "---");
        setText("ma30", data.ma30 ?? "---");
        setText("macd", data.macd ?? "---");
        setText("support", data.support ?? "---");
        setText("resistance", data.resistance ?? "---");

        const signal = document.getElementById("signal");

        if (signal) {
            signal.textContent =
                SIGNAL_TEXT[data.signal] || data.signal || "انتظار";

            signal.className =
                "signal " +
                (SIGNAL_CLASS[data.signal] || "wait");
        }

        const analysis = document.getElementById("analysis");

        if (analysis) {
            analysis.textContent =
                data.analysis ||
                "تحلیل چند تایم‌فریمی بازار آماده است.";
        }

        const reasons = document.getElementById("reasons");

        if (reasons) {
            if (Array.isArray(data.reasons) && data.reasons.length) {
                reasons.innerHTML = data.reasons
                    .map(reason => `• ${escapeHtml(reason)}`)
                    .join("<br>");
            } else {
                reasons.textContent = "دلیل خاصی ثبت نشده است.";
            }
        }

        setText("connection", "🟢 متصل و فعال");

        if (status) {
            status.textContent =
                "🟢 تحلیل واقعی بازار با موفقیت دریافت شد";
        }

    } catch (error) {

        console.error("🦁 Lion API Error:", error);

        setText("connection", "🔴 قطع");

        if (status) {
            status.textContent =
                "🔴 اتصال به موتور تحلیل برقرار نشد";
        }

        const signal = document.getElementById("signal");

        if (signal) {
            signal.textContent = "آفلاین";
            signal.className = "signal wait";
        }
    }
}


function selectMarket(symbol) {
    selectedSymbol = symbol;

    const selected = document.getElementById("selectedMarket");
    if (selected) {
        selected.textContent = symbol;
    }

    const analysisPage = document.getElementById("analysisPage");
    if (analysisPage) {
        document.querySelectorAll(".page").forEach(page => {
            page.classList.remove("active");
        });
        analysisPage.classList.add("active");
    }

    loadSignal();
}

function refreshAll() {
    loadSignal();
}


function setText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


document.addEventListener("DOMContentLoaded", () => {

    loadSignal();

    setInterval(loadSignal, 30000);

});


window.selectMarket = selectMarket;
window.refreshAll = refreshAll;
window.loadSignal = loadSignal;


document.addEventListener("DOMContentLoaded", function() {
    loadMarkets();
    loadSignal();
});


async function scanMarkets() {
    const status = document.getElementById("opportunitiesStatus");
    const list = document.getElementById("opportunitiesList");
    const button = document.getElementById("scanButton");

    if (status) {
        status.textContent = "🦁 در حال اسکن بازارها...";
    }

    if (button) {
        button.disabled = true;
        button.textContent = "⏳ در حال اسکن...";
    }

    try {
        const response = await fetch(
            `${API}/scan`,
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok || data.status !== "ok") {
            throw new Error(
                data.message ||
                data.error ||
                "خطای اسکن بازارها"
            );
        }

        if (status) {
            status.textContent =
                `🟢 ${data.successful} بازار بررسی شده`;
        }

        if (!list) {
            return;
        }

        const opportunities = data.opportunities || [];

        if (!opportunities.length) {
            list.innerHTML =
                '<div class="muted">⏳ هنوز سیگنال خرید یا فروش قوی پیدا نشده است.</div>';
            return;
        }

        list.innerHTML = opportunities.map(item => {
            const signal = item.signal || "WAIT";

            const signalText = {
                BUY: "خرید",
                SELL: "فروش",
                WAIT: "انتظار"
            }[signal] || signal;

            const signalClass = {
                BUY: "buy",
                SELL: "sell",
                WAIT: "wait"
            }[signal] || "wait";

            return `
                <div
                    class="opportunity ${signalClass}"
                    onclick="selectMarket('${item.symbol}')">

                    <div>
                        <strong>🦁 ${item.symbol}</strong>
                        <div class="muted">
                            ${signalText}
                        </div>
                    </div>

                    <div class="opportunity-data">
                        <strong>${item.confidence}%</strong>
                        <span>اطمینان</span>
                    </div>

                    <div class="opportunity-data">
                        <strong>${item.score}</strong>
                        <span>قدرت</span>
                    </div>
                </div>
            `;
        }).join("");

    } catch (error) {
        console.error("SCAN ERROR:", error);

        if (status) {
            status.textContent =
                "🔴 خطا در اسکن بازارها";
        }

        if (list) {
            list.innerHTML =
                '<div class="muted">اتصال به موتور اسکن برقرار نشد.</div>';
        }

    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "🔄 اسکن بازارها";
        }
    }
}


// ------------------------------------------------------------
// Lion AI PRO - Auto Forex Scanner
// ------------------------------------------------------------

let autoScanTimer = null;
let autoScanRunning = false;

async function autoScanOnce() {
    if (autoScanRunning) {
        return;
    }

    autoScanRunning = true;

    try {
        await scanMarkets();
    } catch (error) {
        console.error("AUTO SCAN ERROR:", error);
    } finally {
        autoScanRunning = false;
    }
}

function updateAutoScanButton() {
    const button =
        document.getElementById("autoScanButton");

    if (!button) {
        return;
    }

    if (autoScanTimer) {
        button.textContent =
            "🟢 توقف اسکن خودکار";
    } else {
        button.textContent =
            "🔴 شروع اسکن خودکار";
    }
}

function startAutoScan() {
    if (autoScanTimer) {
        updateAutoScanButton();
        return;
    }

    console.log("🦁 Lion Auto Scanner Started");

    autoScanOnce();

    autoScanTimer = setInterval(
        autoScanOnce,
        70000
    );

    updateAutoScanButton();
}

function stopAutoScan() {
    if (autoScanTimer) {
        clearInterval(autoScanTimer);
        autoScanTimer = null;
    }

    console.log("🦁 Lion Auto Scanner Stopped");

    updateAutoScanButton();
}

function toggleAutoScan() {
    if (autoScanTimer) {
        stopAutoScan();
    } else {
        startAutoScan();
    }
}

window.startAutoScan = startAutoScan;
window.stopAutoScan = stopAutoScan;
window.toggleAutoScan = toggleAutoScan;
window.scanMarkets = scanMarkets;

document.addEventListener("DOMContentLoaded", () => {
    updateAutoScanButton();
});

