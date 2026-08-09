const API = "https://lionminiapp-production.up.railway.app";

async function loadData() {
    try {
        const response = await fetch(`${API}/signal`);
        const data = await response.json();

        console.log("Lion AI:", data);

        const signalEl = document.getElementById("signal");
        if (signalEl) {
            signalEl.textContent = data.signal || "WAIT";
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

    } catch (err) {
        console.error("Lion API Error:", err);

        const signalEl = document.getElementById("signal");
        if (signalEl) signalEl.textContent = "OFFLINE";
    }
}

loadData();
setInterval(loadData, 10000);
