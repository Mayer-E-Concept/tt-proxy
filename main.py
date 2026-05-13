from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)

# Credentiale admin (Marius) - suficient pentru toti userii
ADMIN_EMAIL = os.environ.get("TT_EMAIL", "m.poenar@me-concept.de")
ADMIN_PASSWORD = os.environ.get("TT_PASSWORD", "")

def get_auth_header():
    credentials = f"{ADMIN_EMAIL}:{ADMIN_PASSWORD}"
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

@app.route("/hours", methods=["GET"])
def get_hours():
    """Preia orele pentru toti userii din cont folosind credentiale admin"""
    result = {}
    user_stats = []

    # Pasul 1: Obtine lista de useri (merge cu admin)
    users_data = tt_get("/api/v4/users")
    if not users_data:
        return jsonify({"error": "Nu pot obtine lista de useri", "projects": {}, "count": 0})

    users = users_data.get("data", [])

    # Pasul 2: Pentru fiecare user, preia evenimentele
    for user in users:
        uid = user.get("id")
        uname = f"{user.get('name', '')} {user.get('surname', '')}".strip()
        
        if not uid:
            continue

        count = 0
        # Incearca sa preia evenimentele pentru acest user
        d = tt_get("/api/v4/events", {"user_id": uid})
        if d:
            for evt in d.get("data", []):
                name = (evt.get("p") or evt.get("c") or "").strip()
                secs = float(evt.get("d") or 0)
                if name and secs > 0:
                    result[name] = result.get(name, 0) + secs / 3600
                    count += 1

        # Fallback: projects per user
        if count == 0:
            d = tt_get("/api/v4/projects", {"user_id": uid})
            if d:
                for p in d.get("data", []):
                    name = (p.get("name") or "").strip()
                    hours = float(p.get("worked_hours") or 0)
                    if not hours and p.get("accumulated_time"):
                        hours = float(p["accumulated_time"]) / 3600
                    if name and hours > 0:
                        result[name] = result.get(name, 0) + hours
                        count += 1

        user_stats.append({"user": uname, "id": uid, "events": count})

    return jsonify({
        "projects": {k: round(v, 1) for k, v in result.items()},
        "count": len(result),
        "users": user_stats
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
