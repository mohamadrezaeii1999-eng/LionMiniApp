const API = "/api";

async function loadData() {
    try {
        const [walletRes, signalRes, pricesRes] = await Promise.all([
            fetch(`${API}/wallet`),
            fetch(`${API}/signal`),
            fetch(`${API}/prices`)
        ]);

        const wallet = await walletRes.json();
        const signal = await signalRes.json();
        const prices = await pricesRes.json();

        const result = signal.result || {};

        const balance = document.getElementById("balance");
        if (balance) {
            balance.innerHTML =
                "💵 دلار: " + Number(wallet.usd || 0).toFixed(2) +
                "<br>📈 سود: " + Number(wallet.profit || 0).toFixed(2);
        }

        const signalEl = document.getElementById("signal");
        if (signalEl) signalEl.innerHTML = result.action || "WAIT";

        const confidence = document.getElementById("confidence");
        if (confidence) {
            confidence.innerHTML =
                "قدرت سیگنال: " + (result.confidence ?? 0) + "%";
        }

        document.querySelectorAll(".market-price")[0].innerHTML =
            "$" + (prices.BTC || "---");

        document.querySelectorAll(".market-price")[1].innerHTML =
            "$" + (prices.ETH || "---");

        document.querySelectorAll(".market-price")[2].innerHTML =
            "$" + (prices.XAU || "---");

        document.querySelectorAll(".market-price")[3].innerHTML =
            prices.EUR || "---";

    } catch (err) {
        console.error("Lion API Error:", err);
    }
}

loadData();
setInterval(loadData, 10000);
