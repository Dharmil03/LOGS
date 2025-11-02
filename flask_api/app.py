from flask import Flask, jsonify, request
import requests, os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100") 

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ✅ Example Prometheus metrics
@app.route("/metrics", methods=["GET"])
def metrics():
    return jsonify({"cpu_usage": 72, "memory_usage": 63, "containers_running": 5})


@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        params = {
            "query": '{job="fake_logs"}',
            "limit": 30
        }
        response = requests.get(f"{LOKI_URL}/loki/api/v1/query_range", params=params)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze", methods=["POST"])
def analyze():
    logs = request.json.get("logs", "")
    prompt = f"Analyze these logs and provide insights: {logs}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # ✅ Bind to all interfaces so Docker/React can reach it
    app.run(host="0.0.0.0", port=5000)


