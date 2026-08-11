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
