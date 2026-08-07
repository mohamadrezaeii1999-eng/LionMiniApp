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


let prices = {
BTC:"64250",
ETH:"3150",
XAU:"2385",
EUR:"1.09"
};

setInterval(()=>{

document.querySelectorAll(".market-price")[0].innerHTML="$"+prices.BTC;
document.querySelectorAll(".market-price")[1].innerHTML="$"+prices.ETH;
document.querySelectorAll(".market-price")[2].innerHTML="$"+prices.XAU;
document.querySelectorAll(".market-price")[3].innerHTML=prices.EUR;

},1000);

