from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)

TT_EMAIL = os.environ.get("TT_EMAIL", "m.poenar@me-concept.de")
TT_PASSWORD = os.environ.get("TT_PASSWORD", "")

def get_auth_header():
    credentials = f"{TT_EMAIL}:{TT_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/raw", methods=["GET"])
def get_raw():
    """Testeaza mai multe endpoint-uri si returneaza primul cu date"""
    endpoints = [
        "/api/v4/tasks",
        "/api/v4/projects", 
        "/api/v4/tasks?filter=TRACKING",
        "/api/v4/events",
        "/api/v4/accounts/657424/projects",
    ]
    results = {}
    for ep in endpoints:
        try:
            r = requests.get(
                f"https://app.trackingtime.co{ep}",
                headers=get_auth_header(),
                timeout=10
            )
            data = r.json()
            items = data.get("data") or data.get("response", {}).get("data") or []
            results[ep] = {
                "status": r.status_code,
                "items_count": len(items) if isinstance(items, list) else str(items)[:100],
                "keys": list(data.keys()),
                "first_item": items[0] if isinstance(items, list) and items else None
            }
        except Exception as e:
            results[ep] = {"error": str(e)}
    return jsonify(results)

@app.route("/hours", methods=["GET"])
def get_hours():
    """Returneaza orele lucrate per proiect"""
    try:
        # Incearca endpoint-uri multiple
        endpoints_to_try = [
            "https://app.trackingtime.co/api/v4/tasks",
            "https://app.trackingtime.co/api/v4/projects",
        ]
        
        projects_raw = []
        for url in endpoints_to_try:
            r = requests.get(url, headers=get_auth_header(), timeout=10)
            if r.ok:
                data = r.json()
                items = data.get("data", [])
                if isinstance(items, list) and items:
                    projects_raw = items
                    break
        
        result = {}
        for p in projects_raw:
            name = (p.get("name") or p.get("title") or "").strip()
            hours = float(p.get("worked_hours") or 0)
            if not hours and p.get("accumulated_time"):
                hours = float(p["accumulated_time"]) / 3600
            if name:
                result[name] = round(hours, 1)
        
        return jsonify({"projects": result, "count": len(result)})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
