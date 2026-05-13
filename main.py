from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)

USERS = [
    {
        "name": "Marius Poenar",
        "email": os.environ.get("TT_EMAIL", "m.poenar@me-concept.de"),
        "password": os.environ.get("TT_PASSWORD", "")
    },
    {
        "name": "Ioan Chindea",
        "email": os.environ.get("TT_EMAIL_2", "i.chindea@me-concept.de"),
        "password": os.environ.get("TT_PASSWORD_2", "")
    },
    {
        "name": "Stefan Picu",
        "email": os.environ.get("TT_EMAIL_3", "s.picu@me-concept.de"),
        "password": os.environ.get("TT_PASSWORD_3", "")
    },
    {
        "name": "Martin Mayer",
        "email": os.environ.get("TT_EMAIL_4", "m.mayer@me-concept.de"),
        "password": os.environ.get("TT_PASSWORD_4", "")
    },
]

def get_auth_header(email, password):
    credentials = f"{email}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
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

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/hours", methods=["GET"])
def get_hours():
    """Agregate ore per proiect (campul 'p') pentru toti userii"""
    result = {}
    user_stats = []

    for user in USERS:
        if not user["password"]:
            continue

        count = 0
        d = tt_get("/api/v4/events", user["email"], user["password"])
        if d:
            for evt in d.get("data", []):
                # Campul "p" = project name in TrackingTime
                name = (evt.get("p") or evt.get("c") or "").strip()
                secs = float(evt.get("d") or 0)
                if name and secs > 0:
                    result[name] = result.get(name, 0) + secs / 3600
                    count += 1

        # Fallback pe projects daca events e gol
        if count == 0:
            d = tt_get("/api/v4/projects", user["email"], user["password"])
            if d:
                for p in d.get("data", []):
                    name = (p.get("name") or "").strip()
                    hours = float(p.get("worked_hours") or 0)
                    if not hours and p.get("accumulated_time"):
                        hours = float(p["accumulated_time"]) / 3600
                    if name and hours > 0:
                        result[name] = result.get(name, 0) + hours
                        count += 1

        user_stats.append({"user": user["name"], "events": count})

    return jsonify({
        "projects": {k: round(v, 1) for k, v in result.items()},
        "count": len(result),
        "users": user_stats
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
