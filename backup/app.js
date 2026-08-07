// 🦁 Lion AI PRO Mini App

fetch("http://127.0.0.1:5000/wallet")
.then(res => res.json())
.then(data => {

    document.getElementById("balance").innerHTML =
    "💵 تومان: " + data.toman +
    "<br>💲 دلار: " + data.usd;

});


fetch("http://127.0.0.1:5000/signal")
.then(res => res.json())
.then(data => {

    let result = data.result;

    document.getElementById("signal").innerHTML =
    result.action;

    document.getElementById("confidence").innerHTML =
    "قدرت سیگنال: " + result.confidence + "%";

    document.getElementById("trade").innerHTML =
    "بازار: " + data.symbol +
    "<br>ورود: " + result.entry +
    "<br>TP1: " + result.tp1 +
    "<br>TP2: " + result.tp2 +
    "<br>SL: " + result.sl;

});
