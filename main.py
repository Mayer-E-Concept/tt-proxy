from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)

USERS = [
    {"name": "Marius Poenar",  "email": os.environ.get("TT_EMAIL",   "m.poenar@me-concept.de"), "password": os.environ.get("TT_PASSWORD",   "")},
    {"name": "Ioan Chindea",   "email": os.environ.get("TT_EMAIL_2", "i.chindea@me-concept.de"), "password": os.environ.get("TT_PASSWORD_2", "")},
    {"name": "Stefan Picu",    "email": os.environ.get("TT_EMAIL_3", "s.picu@me-concept.de"),    "password": os.environ.get("TT_PASSWORD_3", "")},
    {"name": "Martin Mayer",   "email": os.environ.get("TT_EMAIL_4", "m.mayer@me-concept.de"),   "password": os.environ.get("TT_PASSWORD_4", "")},
    {"name": "Vadim Rosca",    "email": os.environ.get("TT_EMAIL_5", "v.rosca@me-concept.de"),   "password": os.environ.get("TT_PASSWORD_5", "")},
]

def get_auth_header(email, password):
    encoded = base64.b64encode(f"{email}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}

def tt_get(path, email, password, params=None):
    r = requests.get(
        f"https://app.trackingtime.co{path}",
        headers=get_auth_header(email, password),
        params=params,
        timeout=15
    )
    if r.ok:
        return r.json()
    return None

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/debug_tracking")
def debug_tracking():
    """Verifica timerul activ pentru fiecare user"""
    results = {}
    for user in USERS:
        if not user["password"]:
            continue
        d = tt_get("/api/v4/tracking", user["email"], user["password"])
        results[user["name"]] = {
            "raw": d,
            "has_active": bool(d and d.get("data"))
        }
    return jsonify(results)

@app.route("/debug_vadim_projects")
def debug_vadim_projects():
    user = USERS[4]  # Vadim
    results = {}
    for path in ["/api/v4/projects", "/api/v4/tasks"]:
        d = tt_get(path, user["email"], user["password"])
        if d:
            items = d.get("data", [])
            results[path] = {
                "count": len(items),
                "items": [{"name": p.get("name"), "worked_hours": p.get("worked_hours"), "accumulated_time": p.get("accumulated_time")} for p in items]
            }
        else:
            results[path] = {"error": "no response"}
    return jsonify(results)

@app.route("/hours/alltime")
def get_hours():
    result = {}
    user_stats = []

    for user in USERS:
        if not user["password"]:
            continue
        count = 0

        # 1. Events finalizate
        d = tt_get("/api/v4/events", user["email"], user["password"])
        if d:
            for evt in d.get("data", []):
                name = (evt.get("p") or evt.get("c") or "").strip()
                secs = float(evt.get("d") or 0)
                if name and secs > 0:
                    result[name] = result.get(name, 0) + secs / 3600
                    count += 1

        # 2. Timer activ curent (sesiune neincisa)
        t = tt_get("/api/v4/tracking", user["email"], user["password"])
        if t:
            td = t.get("data")
            if isinstance(td, list) and td:
                td = td[0]
            if isinstance(td, dict):
                name = (td.get("p") or td.get("c") or "").strip()
                secs = float(td.get("d") or td.get("duration") or 0)
                if name and secs > 0:
                    result[name] = result.get(name, 0) + secs / 3600
                    count += 1

        user_stats.append({"user": user["name"], "events": count})

    return jsonify({
        "projects": {k: round(v, 4) for k, v in result.items()},
        "count": len(result),
        "users": user_stats
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
