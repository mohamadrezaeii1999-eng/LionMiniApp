import os
from flask import Flask, jsonify
from flask_cors import CORS
from lion_real_engine import get_signal

app = Flask(__name__)
CORS(app)

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "app": "Lion AI PRO"
    })

@app.get("/signal")
def signal():
    return jsonify(get_signal())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
