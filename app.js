const API = "https://lionminiapp-production.up.railway.app";

let selectedSymbol = "EUR/USD";

function selectMarket(symbol) {
    selectedSymbol = symbol;

    const selected = document.getElementById("selectedMarket");
    if (selected) {
        selected.textContent = symbol;
    }

    loadData();
}

async function loadData() {
    try {
        const url = `${API}/signal?symbol=${encodeURIComponent(selectedSymbol)}`;

        const response = await fetch(url);
        const data = await response.json();

        console.log("🦁 Lion AI:", selectedSymbol, data);

        const signalEl = document.getElementById("signal");
        if (signalEl) {
            const signals = {
                BUY: "خرید",
                SELL: "فروش",
                WAIT: "انتظار"
            };

            signalEl.textContent = signals[data.signal] || data.signal || "انتظار";
        }

        const confidence = document.getElementById("confidence");
        if (confidence) {
            confidence.textContent =
                "قدرت سیگنال: " + (data.confidence ?? 0) + "%";
        }

        const balance = document.getElementById("balance");
        if (balance) {
            balance.innerHTML =
                "💵 قیمت: " + (data.price ?? "---") +
                "<br>📊 امتیاز: " + (data.score ?? 0);
        }

        const analysis = document.getElementById("analysis");
        if (analysis) {
            analysis.textContent = data.analysis || "---";
        }

        const reasons = document.getElementById("reasons");
        if (reasons) {
            if (Array.isArray(data.reasons)) {
                reasons.innerHTML = data.reasons
                    .map(reason => "• " + reason)
                    .join("<br>");
            } else {
                reasons.textContent = data.analysis || "---";
            }
        }

        const price = document.getElementById("price");
        if (price) {
            price.textContent = data.price ?? "---";
        }

        const rsi = document.getElementById("rsi");
        if (rsi) {
            rsi.textContent = data.rsi ?? "---";
        }

        const ma10 = document.getElementById("ma10");
        if (ma10) {
            ma10.textContent = data.ma10 ?? "---";
        }

        const ma30 = document.getElementById("ma30");
        if (ma30) {
            ma30.textContent = data.ma30 ?? "---";
        }

        const support = document.getElementById("support");
        if (support) {
            support.textContent = data.support ?? "---";
        }

        const resistance = document.getElementById("resistance");
        if (resistance) {
            resistance.textContent = data.resistance ?? "---";
        }

    } catch (err) {
        console.error("Lion API Error:", err);

        const signalEl = document.getElementById("signal");
        if (signalEl) {
            signalEl.textContent = "آفلاین";
        }
    }
}

loadData();
setInterval(loadData, 10000);
