from flask import Flask, jsonify
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

def tt_get(path, params=None):
    r = requests.get(
        f"https://app.trackingtime.co{path}",
        headers=get_auth_header(),
        params=params,
        timeout=15
    )
    if r.ok:
        return r.json()
    return None

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/debug", methods=["GET"])
def debug():
    """Testeaza endpoint-urile fara parametri extra"""
    results = {}
    
    # Events fara parametri
    d = tt_get("/api/v4/events")
    if d:
        items = d.get("data", [])
        results["events_no_params"] = {
            "count": len(items),
            "first": items[0] if items else None
        }
    
    # Events cu data curenta
    d = tt_get("/api/v4/events", {"from": "2026-01-01", "to": "2026-12-31"})
    if d:
        items = d.get("data", [])
        results["events_with_date"] = {"count": len(items)}

    # Events cu date diferite
    d = tt_get("/api/v4/events", {"start_date": "2026-01-01", "end_date": "2026-12-31"})
    if d:
        items = d.get("data", [])
        results["events_start_end"] = {"count": len(items)}

    # Projects fara parametri
    d = tt_get("/api/v4/projects")
    if d:
        items = d.get("data", [])
        results["projects_no_params"] = {
            "count": len(items),
            "names": [p.get("name") for p in items]
        }
    
    # Projects cu limit
    d = tt_get("/api/v4/projects", {"limit": 100})
    if d:
        items = d.get("data", [])
        results["projects_limit100"] = {"count": len(items)}

    return jsonify(results)

@app.route("/hours", methods=["GET"])
def get_hours():
    result = {}
    
    # Incearca events fara parametri
    d = tt_get("/api/v4/events")
    if d:
        items = d.get("data", [])
        for evt in items:
            name = (evt.get("c") or evt.get("p") or "").strip()
            secs = float(evt.get("d") or 0)
            if name and secs > 0:
                result[name] = result.get(name, 0) + secs / 3600

    # Fallback: projects
    if not result:
        d = tt_get("/api/v4/projects")
        if d:
            for p in d.get("data", []):
                name = (p.get("name") or "").strip()
                hours = float(p.get("worked_hours") or 0)
                if name:
                    result[name] = hours

    return jsonify({
        "projects": {k: round(v, 1) for k, v in result.items()},
        "count": len(result)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
