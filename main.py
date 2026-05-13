from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)

TT_EMAIL = os.environ.get("TT_EMAIL", "m.poenar@me-concept.de")
TT_PASSWORD = os.environ.get("TT_PASSWORD", "")
ACCOUNT_ID = 657481  # Din raspunsul API

def get_auth_header():
    credentials = f"{TT_EMAIL}:{TT_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}

def tt_get(path, params=None):
    r = requests.get(
        f"https://app.trackingtime.co{path}",
        headers=get_auth_header(),
        params=params,
        timeout=15
    )
    return {"status": r.status_code, "data": r.json() if r.ok else r.text[:200]}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/debug", methods=["GET"])
def debug():
    results = {}
    
    # Testeaza cu account_id corect (657481)
    paths = [
        f"/api/v4/accounts/{ACCOUNT_ID}/users",
        f"/api/v4/accounts/{ACCOUNT_ID}/projects",
        f"/api/v4/accounts/{ACCOUNT_ID}/tasks",
        f"/api/v4/accounts/{ACCOUNT_ID}/events",
        "/api/v4/reports/time",
        "/api/v4/reports",
        "/api/v4/projects?include_archived=true",
        "/api/v4/projects?all=true",
    ]
    
    for path in paths:
        d = tt_get(path)
        if d["status"] == 200:
            data = d["data"]
            items = data.get("data", [])
            results[path] = {
                "ok": True,
                "count": len(items) if isinstance(items, list) else "N/A",
                "keys": list(data.keys()) if isinstance(data, dict) else [],
                "sample": items[0] if isinstance(items, list) and items else None
            }
        else:
            results[path] = {"ok": False, "status": d["status"]}
    
    return jsonify(results)

@app.route("/hours", methods=["GET"])
def get_hours():
    result = {}
    d = tt_get("/api/v4/events")
    if d["status"] == 200:
        for evt in d["data"].get("data", []):
            name = (evt.get("c") or evt.get("p") or "").strip()
            secs = float(evt.get("d") or 0)
            if name and secs > 0:
                result[name] = result.get(name, 0) + secs / 3600
    if not result:
        d = tt_get("/api/v4/projects")
        if d["status"] == 200:
            for p in d["data"].get("data", []):
                name = (p.get("name") or "").strip()
                hours = float(p.get("worked_hours") or 0)
                if name:
                    result[name] = hours
    return jsonify({"projects": {k: round(v, 1) for k, v in result.items()}, "count": len(result)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
