const API = "https://lionminiapp-production-a934.up.railway.app";

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
    try {
        const pages = document.querySelectorAll(".page");

        pages.forEach(function(page) {
            page.classList.remove("active");
            page.style.display = "none";
        });

        const target = document.getElementById(id);

        if (!target) {
            console.error("Lion AI page not found:", id);
            return false;
        }

        target.classList.add("active");
        target.style.display = "block";

        document.querySelectorAll(".nav-inner button").forEach(function(btn) {
            btn.classList.remove("active");
        });

        if (button) {
            button.classList.add("active");
        }

        if (id === "analysisPage" && typeof loadRealChart === "function") {
            setTimeout(loadRealChart, 100);
        }

        if (id === "markets" && typeof loadMarkets === "function") {
            setTimeout(loadMarkets, 100);
        }

        if (id === "wallet" && typeof loadLionWallet === "function") {
            setTimeout(loadLionWallet, 100);
        }

        window.scrollTo(0, 0);
        return false;
    } catch (error) {
        console.error("SHOW PAGE ERROR:", error);
        return false;
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
        const requestStarted = performance.now();

        const response = await fetch(
            `${API}/signal?symbol=${encodeURIComponent(selectedSymbol)}`,
            {
                cache: "no-store"
            }
        );

        const requestLatency = Math.round(performance.now() - requestStarted);

        const latencyEl = document.getElementById("systemLatency");
        if (latencyEl) {
            latencyEl.textContent = requestLatency + " ms";
        }

        const statusEl = document.getElementById("systemStatus");
        const dotEl = document.getElementById("systemDot");

        const data = await response.json();

        console.log("🦁 Lion AI:", selectedSymbol, data);

        if (data.status !== "ok") {
            const apiMessage = data.message || data.error || "خطای تحلیل";

            const statusEl = document.getElementById("systemStatus");
            const dotEl = document.getElementById("systemDot");

            if (statusEl && apiMessage.toLowerCase().includes("quota")) {
                statusEl.textContent = "سهمیه داده بازار موقتاً تمام شده";
            } else if (statusEl) {
                statusEl.textContent = apiMessage;
            }

            if (dotEl) {
                dotEl.className =
                    "system-dot " +
                    (apiMessage.toLowerCase().includes("quota")
                        ? "warning"
                        : "offline");
            }

            setText("price", "---");
            setText("score", "---");
            setText("confidence", "---");
            setText("rsi", "---");
            setText("ma10", "---");
            setText("ma30", "---");
            setText("macd", "---");
            setText("support", "---");
            setText("resistance", "---");

            const signalEl = document.getElementById("signal");
            if (signalEl) {
                signalEl.textContent = "داده جدید در دسترس نیست";
                signalEl.className = "signal wait";
            }

            const priceChangeEl = document.getElementById("priceChange");
            if (priceChangeEl) {
                priceChangeEl.textContent = "منتظر دریافت داده بازار";
                priceChangeEl.style.color = "#8996a6";
            }

            throw new Error(apiMessage);
        }

        lastData = data;

        setText("selectedMarket", data.symbol || selectedSymbol);
        const currentPrice = Number(data.price);
        const previousPrice = Number(lastData && lastData.price);

        setText("price", data.price ?? "---");

        const priceChangeEl = document.getElementById("priceChange");

        if (priceChangeEl && Number.isFinite(currentPrice) && Number.isFinite(previousPrice)) {
            const diff = currentPrice - previousPrice;
            const percent = previousPrice !== 0
                ? (diff / previousPrice) * 100
                : 0;

            if (diff > 0) {
                priceChangeEl.textContent =
                    "▲ +" + diff.toFixed(5) + "  (+" + percent.toFixed(3) + "%)";
                priceChangeEl.style.color = "#36e39d";
            } else if (diff < 0) {
                priceChangeEl.textContent =
                    "▼ " + diff.toFixed(5) + "  (" + percent.toFixed(3) + "%)";
                priceChangeEl.style.color = "#ff6875";
            } else {
                priceChangeEl.textContent = "● بدون تغییر";
                priceChangeEl.style.color = "#8996a6";
            }
        } else if (priceChangeEl) {
            priceChangeEl.textContent = "در انتظار قیمت بعدی";
            priceChangeEl.style.color = "#8996a6";
        }
        setText("aPrice", data.price ?? "---");
        setText("score", data.score ?? "---");
        setText("aScore", data.score ?? "---");
        setText("confidence", data.confidence != null ? data.confidence + "%" : "---");

        const scoreBar = document.getElementById("scoreBar");
        const confidenceBar = document.getElementById("confidenceBar");

        if (scoreBar) {
            const scoreValue = Number(data.score);
            const scorePercent = Number.isFinite(scoreValue)
                ? Math.min(100, Math.max(0, Math.abs(scoreValue)))
                : 0;
            scoreBar.style.width = scorePercent + "%";
        }

        if (confidenceBar) {
            const confidenceValue = Number(data.confidence);
            const confidencePercent = Number.isFinite(confidenceValue)
                ? Math.min(100, Math.max(0, confidenceValue))
                : 0;
            confidenceBar.style.width = confidencePercent + "%";
        }
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

            const signalHint = document.getElementById("signalHint");
            const signalTime = document.getElementById("signalTime");

            if (signalHint) {
                const hints = {
                    BUY: "شرایط فعلی به نفع ورود خرید است",
                    SELL: "شرایط فعلی به نفع ورود فروش است",
                    WAIT: "شرایط کافی برای ورود مطمئن وجود ندارد"
                };

                signalHint.textContent =
                    hints[data.signal] || "در انتظار تحلیل واقعی بازار";
            }

            if (signalTime) {
                signalTime.textContent =
                    new Date().toLocaleTimeString("fa-IR", {
                        hour: "2-digit",
                        minute: "2-digit"
                    });
            }
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


function renderScanResults(data) {
    const status = document.getElementById("opportunitiesStatus");
    const list = document.getElementById("opportunitiesList");

    if (!list) return;

    const results = data.opportunities || [];

    if (status) {
        status.textContent =
            `🟢 اسکن شد: ${data.successful || 0} بازار | فرصت‌ها: ${results.length}`;
    }

    if (!results.length) {
        list.innerHTML = `
            <div class="muted">
                ⏳ فعلاً سیگنال BUY یا SELL قوی پیدا نشد.
            </div>
        `;
        return;
    }

    list.innerHTML = results.map(item => {
        const signal = item.signal || "WAIT";

        const signalText = {
            BUY: "🟢 خرید",
            SELL: "🔴 فروش",
            WAIT: "🟡 انتظار"
        }[signal] || signal;

        const signalClass = {
            BUY: "buy",
            SELL: "sell",
            WAIT: "wait"
        }[signal] || "wait";

        const confidence = Number(item.confidence || 0).toFixed(1);
        const score = Number(item.score || 0).toFixed(1);
        const price =
            item.price !== null && item.price !== undefined
                ? item.price
                : "---";

        return `
            <div
                class="opportunity ${signalClass}"
                onclick="selectMarket('${item.symbol}')"
            >
                <div>
                    <strong>🦁 ${item.symbol}</strong>
                    <div class="muted">
                        ${signalText}
                    </div>
                </div>

                <div class="opportunity-data">
                    <strong>${confidence}%</strong>
                    <span>اطمینان</span>
                </div>

                <div class="opportunity-data">
                    <strong>${score}</strong>
                    <span>قدرت</span>
                </div>

                <div class="opportunity-data">
                    <strong>${price}</strong>
                    <span>قیمت</span>
                </div>
            </div>
        `;
    }).join("");
}


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
            `${API}/scan?t=${Date.now()}`,
            {
                method: "GET",
                cache: "no-store"
            }
        );

        const text = await response.text();

        let data;

        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error("پاسخ API قابل خواندن نیست");
        }

        console.log("🦁 SCAN RESPONSE:", data);

        if (!response.ok || data.status !== "ok") {
            throw new Error(
                data.message ||
                data.error ||
                "خطای موتور اسکن"
            );
        }

        const successful = Number(data.successful || 0);
        const failed = Number(data.failed || 0);
        const scanned = Number(data.scanned || 0);

        if (status) {
            status.textContent =
                `🟢 اسکن انجام شد | ${successful} بازار موفق | ${failed} خطا | از ${scanned} بازار`;
        }

        if (!list) {
            return;
        }

        /*
         * اول نتایج واقعی results را می‌گیریم.
         * اگر نبود، opportunities را استفاده می‌کنیم.
         */
        let results = Array.isArray(data.results)
            ? data.results
            : [];

        if (!results.length && Array.isArray(data.opportunities)) {
            results = data.opportunities;
        }

        // نمایش بهترین نتیجه در کارت مخصوص
        renderBestOpportunity(results);

        /*
         * مرتب‌سازی:
         * قوی‌ترین امتیازها اول
         */
        results.sort((a, b) => {
            const scoreA = Math.abs(Number(a.score || 0));
            const scoreB = Math.abs(Number(b.score || 0));

            if (scoreB !== scoreA) {
                return scoreB - scoreA;
            }

            return Number(b.confidence || 0) -
                   Number(a.confidence || 0);
        });

        /*
         * فقط 10 نتیجه برتر نمایش داده شود
         */
        results = results.slice(0, 10);

        if (!results.length) {
            list.innerHTML = `
                <div class="muted" style="padding:12px;">
                    ⏳ هنوز نتیجه‌ای برای نمایش وجود ندارد.
                </div>
            `;
            return;
        }

        list.innerHTML = results.map(item => {

            const signal = item.signal || "WAIT";

            const signalText = {
                BUY: "خرید 🟢",
                SELL: "فروش 🔴",
                WAIT: "انتظار 🟡"
            }[signal] || signal;

            const signalClass = {
                BUY: "buy",
                SELL: "sell",
                WAIT: "wait"
            }[signal] || "wait";

            const confidence =
                item.confidence != null
                    ? Number(item.confidence).toFixed(1)
                    : "—";

            const score =
                item.score != null
                    ? Number(item.score).toFixed(1)
                    : "—";

            const price =
                item.price != null
                    ? item.price
                    : "—";

            return `
                <div
                    class="opportunity ${signalClass}"
                    onclick="selectMarket('${item.symbol}')"
                    style="cursor:pointer;"
                >

                    <div>
                        <strong>🦁 ${item.symbol}</strong>

                        <div class="muted">
                            ${signalText}
                        </div>

                        <div class="muted">
                            قیمت: ${price}
                        </div>
                    </div>

                    <div class="opportunity-data">
                        <strong>${confidence}%</strong>
                        <span>اطمینان</span>
                    </div>

                    <div class="opportunity-data">
                        <strong>${score}</strong>
                        <span>قدرت</span>
                    </div>

                </div>
            `;

        }).join("");

    } catch (error) {

        console.error("🦁 SCAN ERROR:", error);

        if (status) {
            status.textContent =
                "🔴 خطا در اتصال به موتور اسکن";
        }

        if (list) {
            list.innerHTML = `
                <div class="muted" style="padding:12px;">
                    🔴 خطا در دریافت نتیجه اسکن
                </div>

                <div
                    class="muted"
                    style="padding:8px 12px;font-size:12px;direction:ltr;text-align:left;"
                >
                    ${String(error.message || error)}
                </div>

                <button
                    class="scan-button"
                    onclick="scanMarkets()"
                    style="margin-top:10px;"
                >
                    🔄 تلاش دوباره
                </button>
            `;
        }

    } finally {

        if (button) {
            button.disabled = false;
            button.textContent = "🔄 اسکن بازارها";
        }
    }
}

// ------------------------------------------------------------
// Lion AI PRO - Best Current Opportunity
// ------------------------------------------------------------

function renderBestOpportunity(results) {

    const box = document.getElementById("bestOpportunity");

    if (!box) {
        return;
    }

    if (!Array.isArray(results) || !results.length) {

        box.innerHTML = `
            <div class="muted" style="padding:12px;">
                ⏳ هنوز نتیجه‌ای برای نمایش وجود ندارد.
            </div>
        `;

        return;
    }

    const sorted = [...results].sort((a, b) => {

        const scoreA = Math.abs(Number(a.score || 0));
        const scoreB = Math.abs(Number(b.score || 0));

        if (scoreB !== scoreA) {
            return scoreB - scoreA;
        }

        return Number(b.confidence || 0) -
               Number(a.confidence || 0);
    });

    const best = sorted[0];

    const signal = best.signal || "WAIT";

    const signalText = {
        BUY: "خرید 🟢",
        SELL: "فروش 🔴",
        WAIT: "انتظار 🟡"
    }[signal] || signal;

    const confidence =
        best.confidence != null
            ? Number(best.confidence).toFixed(1)
            : "—";

    const score =
        best.score != null
            ? Number(best.score).toFixed(1)
            : "—";

    const price =
        best.price != null
            ? best.price
            : "—";

    const reasons = Array.isArray(best.reasons)
        ? best.reasons.slice(0, 4)
        : [];

    const reasonsHtml = reasons.length
        ? reasons.map(reason => `
            <div class="muted" style="margin-top:4px;">
                • ${reason}
            </div>
        `).join("")
        : "";

    let tradeInfo = "";

    if (signal === "BUY" || signal === "SELL") {

        tradeInfo = `
            <div style="
                margin-top:12px;
                padding:10px;
                border-radius:10px;
                background:rgba(255,255,255,0.05);
            ">
                <strong>
                    🟢 سیگنال معاملاتی فعال است
                </strong>

                <div class="muted" style="margin-top:5px;">
                    جزئیات ورود، حد ضرر و حد سود از موتور معاملاتی نمایش داده می‌شود.
                </div>
            </div>
        `;

    } else {

        tradeInfo = `
            <div style="
                margin-top:12px;
                padding:10px;
                border-radius:10px;
                background:rgba(255,255,255,0.05);
            ">
                <strong>⏳ فعلاً ورود مناسب نیست</strong>

                <div class="muted" style="margin-top:5px;">
                    قدرت تحلیل بالاست، اما موتور هنوز BUY/SELL تأییدشده نداده است.
                </div>
            </div>
        `;
    }

    box.innerHTML = `

        <div
            class="opportunity ${signal === "BUY" ? "buy" : signal === "SELL" ? "sell" : "wait"}"
            onclick="selectMarket('${best.symbol}')"
            style="
                cursor:pointer;
                display:flex;
                flex-direction:column;
                gap:10px;
            "
        >

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
            ">

                <strong style="font-size:18px;">
                    🦁 ${best.symbol}
                </strong>

                <strong>
                    ${signalText}
                </strong>

            </div>

            <div style="
                display:flex;
                gap:18px;
                flex-wrap:wrap;
            ">

                <div class="opportunity-data">
                    <strong>${confidence}%</strong>
                    <span>اطمینان</span>
                </div>

                <div class="opportunity-data">
                    <strong>${score}</strong>
                    <span>قدرت</span>
                </div>

                <div class="opportunity-data">
                    <strong>${price}</strong>
                    <span>قیمت</span>
                </div>

            </div>

            ${reasonsHtml}

            ${tradeInfo}

        </div>
    `;
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


window.scanMarkets = scanMarkets;
window.startAutoScan = startAutoScan;
window.stopAutoScan = stopAutoScan;
window.toggleAutoScan = toggleAutoScan;

console.log("🦁 Auto Scanner controls connected");

/* ============================================================
   REAL MARKET CANDLE CHART
   ============================================================ */

async function loadRealChart() {
    const canvas = document.getElementById("realChart");
    const status = document.getElementById("chartStatus");

    if (!canvas) return;

    try {
        const response = await fetch(
            `${API}/candles?symbol=${encodeURIComponent(selectedSymbol)}&interval=5min&t=${Date.now()}`,
            { cache: "no-store" }
        );

        const data = await response.json();

        if (!response.ok || data.status !== "ok" || !Array.isArray(data.candles) || !data.candles.length) {
            if (status) {
                status.textContent =
                    data.message || "فعلاً داده واقعی نمودار در دسترس نیست";
            }
            return;
        }

        const candles = data.candles.slice(-60);

        const ctx = canvas.getContext("2d");
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const width = rect.width;
        const height = rect.height;

        ctx.clearRect(0, 0, width, height);

        /* ===== UI 10.18 CHART GRID ===== */
        ctx.save();

        const gridLines = 5;
        ctx.strokeStyle = "rgba(137,150,166,.12)";
        ctx.lineWidth = 1;
        ctx.font = "10px Tahoma, Arial";
        ctx.fillStyle = "#687687";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";

        for (let g = 0; g <= gridLines; g++) {
            const gy = 20 + (height - 40) * (g / gridLines);

            ctx.beginPath();
            ctx.moveTo(8, gy);
            ctx.lineTo(width - 8, gy);
            ctx.stroke();
        }

        ctx.restore();

        const highs = candles.map(c => Number(c.high));
        const lows = candles.map(c => Number(c.low));

        const max = Math.max(...highs);
        const min = Math.min(...lows);
        const range = max - min || 0.0001;

        const pad = 20;
        const chartHeight = height - pad * 2;
        const candleWidth = Math.max(4, (width - 20) / candles.length * 0.65);

        function y(price) {
            return pad + ((max - price) / range) * chartHeight;
        }

        /* قیمت‌های محور راست */
        ctx.save();
        ctx.font = "10px Tahoma, Arial";
        ctx.fillStyle = "#687687";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";

        for (let g = 0; g <= 4; g++) {
            const priceLevel = max - (range * g / 4);
            const gy = y(priceLevel);

            ctx.fillText(
                priceLevel.toFixed(5),
                width - 5,
                gy
            );
        }

        ctx.restore();

        candles.forEach((candle, i) => {
            const open = Number(candle.open);
            const close = Number(candle.close);
            const high = Number(candle.high);
            const low = Number(candle.low);

            const x = 10 + (i + 0.5) * ((width - 20) / candles.length);

            const bullish = close >= open;

            ctx.beginPath();
            ctx.moveTo(x, y(high));
            ctx.lineTo(x, y(low));
            ctx.lineWidth = 1;
            ctx.strokeStyle = bullish ? "#31e69c" : "#ff5b69";
            ctx.stroke();

            const bodyTop = y(Math.max(open, close));
            const bodyBottom = y(Math.min(open, close));
            const bodyHeight = Math.max(2, bodyBottom - bodyTop);

            ctx.fillStyle = bullish ? "#31e69c" : "#ff5b69";
            ctx.fillRect(
                x - candleWidth / 2,
                bodyTop,
                candleWidth,
                bodyHeight
            );
        });

        const last = candles[candles.length - 1];

        /* ===== UI 10.19 LAST PRICE LINE ===== */
        const lastPrice = Number(last.close);

        if (Number.isFinite(lastPrice)) {
            const lastY = y(lastPrice);

            ctx.save();

            ctx.beginPath();
            ctx.setLineDash([5, 4]);
            ctx.moveTo(8, lastY);
            ctx.lineTo(width - 8, lastY);
            ctx.lineWidth = 1;
            ctx.strokeStyle = "#dca51c";
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.font = "bold 10px Tahoma, Arial";
            ctx.textAlign = "right";
            ctx.textBaseline = "middle";

            const labelWidth = 68;
            const labelHeight = 20;
            const labelX = width - labelWidth - 4;
            const labelY = Math.max(
                2,
                Math.min(height - labelHeight - 2, lastY - labelHeight / 2)
            );

            ctx.fillStyle = "#dca51c";
            ctx.fillRect(
                labelX,
                labelY,
                labelWidth,
                labelHeight
            );

            ctx.fillStyle = "#080b10";
            ctx.fillText(
                lastPrice.toFixed(5),
                width - 8,
                labelY + labelHeight / 2
            );

            ctx.restore();
        }

        const lowEl = document.getElementById("chartLow");
        const highEl = document.getElementById("chartHigh");
        const timeEl = document.getElementById("chartTime");

        if (lowEl) lowEl.textContent = `کف: ${min.toFixed(5)}`;
        if (highEl) highEl.textContent = `سقف: ${max.toFixed(5)}`;
        if (timeEl) timeEl.textContent = last.datetime || "--";

        if (status) status.style.display = "none";

    } catch (error) {
        console.error("REAL CHART ERROR:", error);

        if (status) {
            status.style.display = "flex";
            status.textContent = "خطا در دریافت داده نمودار";
        }
    }
}

window.loadRealChart = loadRealChart;

// اجرای نمودار هنگام ورود و بعد از تغییر جفت‌ارز
document.addEventListener("DOMContentLoaded", () => {
    loadRealChart();
    setInterval(loadRealChart, 30000);
});

// وقتی بازار عوض شد، نمودار همان بازار را بگیر
const _oldSelectMarket = window.selectMarket;

if (typeof _oldSelectMarket === "function") {
    window.selectMarket = function(symbol) {
        const result = _oldSelectMarket.apply(this, arguments);
        setTimeout(loadRealChart, 300);
        return result;
    };
}


/* ===== LION BUTTONS SAFE FIX ===== */

function clearHistory() {
    try {
        localStorage.removeItem("lionTradeHistory");
        localStorage.removeItem("tradeHistory");

        const history = document.getElementById("history");
        if (history) {
            history.innerHTML =
                '<div class="muted">تاریخچه پاک شد</div>';
        }
    } catch (error) {
        console.error("CLEAR HISTORY ERROR:", error);
    }
}

function showInfo() {
    alert(
        "🦁 LION AI PRO\n\n" +
        "هوش مصنوعی معامله‌گر\n" +
        "تحلیل بازار با داده واقعی\n" +
        "نسخه Engine V3.7"
    );
}

/* اتصال توابع به دکمه‌های HTML */

window.showPage = showPage;
window.clearHistory = clearHistory;
window.showInfo = showInfo;
window.scanMarkets = scanMarkets;
window.startAutoScan = startAutoScan;
window.stopAutoScan = stopAutoScan;
window.toggleAutoScan = toggleAutoScan;



/* ===== LION AI PRO — DIRECT NAV EVENTS ===== */

document.addEventListener("DOMContentLoaded", function(){

    document.querySelectorAll(".nav-inner button").forEach(function(button){

        button.addEventListener("click", function(event){

            event.preventDefault();
            event.stopPropagation();

            switch(button.id){

                case "nav-dashboard":
                    showPage("dashboard", button);
                    break;

                case "nav-analysis":
                    showPage("analysisPage", button);
                    break;

                case "nav-markets":
                    showPage("markets", button);
                    break;

                case "nav-history":
                    showPage("history", button);
                    break;

                case "nav-settings":
                    showPage("settings", button);
                    break;
            }

        }, true);

    });

});




/* ============================================================
   🦁 LION AI PRO — PAPER TRADING — SINGLE CONTROLLER
   Mini App Live Auto Trading Controller
   ============================================================ */
(function () {

    const LION_PAPER_API =
        "https://lionminiapp-production-a934.up.railway.app";

    let paperPollingStarted = false;

    function paperStatus(text) {
        const el = document.getElementById("autoStatus");
        if (el) el.textContent = text;
    }

    function paperMode(text) {
        const el = document.getElementById("autoMode");
        if (el) el.textContent = text;
    }

    function paperMarket(text) {
        const el = document.getElementById("autoMarket");
        if (el && text) el.textContent = text;
    }

    function paperConfidence(value) {
        const el = document.getElementById("autoConfidence");
        if (!el) return;

        const n = Number(value);

        if (Number.isFinite(n)) {
            el.textContent = Math.round(n) + "%";
        }
    }

    window.lionStartPaper = async function (event) {

        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        paperStatus("⏳ در حال اجرا...");

        try {

            const response = await fetch(
                LION_PAPER_API + "/paper/start?t=" + Date.now(),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    cache: "no-store"
                }
            );

            const data = await response.json();

            console.log("🦁 PAPER START:", response.status, data);

            if (!response.ok || data.ok !== true) {
                throw new Error(
                    data.error ||
                    data.message ||
                    "Paper Trading start failed"
                );
            }

            paperStatus("🟢 در حال اجرا");
            paperMode("PAPER • ON");

            await window.lionLoadPaperStatus();

        } catch (error) {

            console.error("🦁 PAPER START ERROR:", error);

            paperStatus("🔴 خطا");
            paperMode("PAPER • OFF");
        }

        return false;
    };


    window.lionStopPaper = async function (event) {

        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        paperStatus("⏳ در حال توقف...");

        try {

            const response = await fetch(
                LION_PAPER_API + "/paper/stop?t=" + Date.now(),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    cache: "no-store"
                }
            );

            const data = await response.json();

            console.log("🦁 PAPER STOP:", response.status, data);

            if (!response.ok || data.ok !== true) {
                throw new Error(
                    data.error ||
                    data.message ||
                    "Paper Trading stop failed"
                );
            }

            paperStatus("⚪ متوقف");
            paperMode("PAPER • OFF");

            await window.lionLoadPaperStatus();

        } catch (error) {

            console.error("🦁 PAPER STOP ERROR:", error);

            paperStatus("🔴 خطا");
        }

        return false;
    };


    window.lionLoadPaperStatus = async function () {

        try {

            const response = await fetch(
                LION_PAPER_API +
                "/paper/status?t=" +
                Date.now(),
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

            const data = await response.json();

            console.log("🦁 PAPER STATUS:", response.status, data);

            if (data.enabled === true) {

                paperStatus("🟢 در حال اجرا");
                paperMode("PAPER • ON");

            } else {

                paperStatus("⚪ آماده");
                paperMode("PAPER • OFF");
            }

            if (data.wallet) {
                console.log(
                    "🦁 PAPER WALLET:",
                    data.wallet
                );
            }

        } catch (error) {

            console.error(
                "🦁 PAPER STATUS ERROR:",
                error
            );
        }
    };


    window.lionLoadAutoStatus = async function () {

        try {

            const response = await fetch(
                LION_PAPER_API +
                "/paper/auto/status?t=" +
                Date.now(),
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

            const data = await response.json();

            console.log(
                "🦁 AUTO STATUS:",
                response.status,
                data
            );

            const scanner = data.scanner || {};

            /*
             * اگر Paper خاموش باشد،
             * پنل هم خاموش نشان داده می‌شود.
             */
            if (scanner.enabled === false) {

                paperMode("PAPER • OFF");

                if (scanner.worker_status === "disabled") {
                    paperStatus("⚪ آماده");
                }

                return;
            }

            /*
             * Worker روشن است.
             */
            if (
                scanner.worker_status === "running" ||
                scanner.enabled === true
            ) {
                paperMode("PAPER • ON");
            }

            /*
             * بهترین فرصت معتبر را پیدا می‌کنیم.
             */
            const results = Array.isArray(data.results)
                ? data.results
                : [];

            const opportunities = results
                .filter(function (x) {
                    return (
                        x &&
                        (
                            x.signal === "BUY" ||
                            x.signal === "SELL"
                        )
                    );
                })
                .sort(function (a, b) {

                    const sa =
                        Math.abs(Number(a.score || 0));

                    const sb =
                        Math.abs(Number(b.score || 0));

                    if (sb !== sa) {
                        return sb - sa;
                    }

                    return (
                        Number(b.confidence || 0) -
                        Number(a.confidence || 0)
                    );
                });

            if (opportunities.length > 0) {

                const best = opportunities[0];

                if (best.symbol) {
                    paperMarket(best.symbol);
                }

                if (best.confidence !== undefined) {
                    paperConfidence(best.confidence);
                }

                paperStatus(
                    best.signal === "BUY"
                        ? "🟢 BUY • خودکار"
                        : "🔴 SELL • خودکار"
                );

            } else {

                paperStatus("🟢 فعال • منتظر فرصت");
            }

        } catch (error) {

            console.error(
                "🦁 AUTO STATUS ERROR:",
                error
            );
        }
    };


    async function lionRefreshAutoPanel() {

        await window.lionLoadPaperStatus();
        await window.lionLoadAutoStatus();
    }


    function startPaperPolling() {

        if (paperPollingStarted) {
            return;
        }

        paperPollingStarted = true;

        /*
         * اولین بار بلافاصله اجرا شود.
         */
        lionRefreshAutoPanel();

        /*
         * هر 5 ثانیه وضعیت Mini App
         * از Railway خوانده می‌شود.
         */
        setInterval(
            lionRefreshAutoPanel,
            5000
        );
    }


    /*
     * وقتی صفحه کامل آماده شد، Polling شروع می‌شود.
     */
    if (document.readyState === "loading") {

        document.addEventListener(
            "DOMContentLoaded",
            startPaperPolling,
            { once: true }
        );

    } else {

        startPaperPolling();
    }

})();

async function loadCTraderAccount() {
  try {
    const r = await fetch(`${API}/ctrader/account`);
    const j = await r.json();
    console.log("cTrader:", j);
    if (j.ok && j.data?.data?.[0]) {
      const a = j.data.data[0];
      console.log("cTrader Account:", a.accountNumber, "Balance:", a.balance, a.depositCurrency);
    }
  } catch (e) {
    console.error("cTrader connection error:", e);
  }
}

loadCTraderAccount();
