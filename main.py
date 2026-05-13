from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os
from datetime import datetime

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

def get_user_hours(email, password):
    """Preia orele per proiect pentru un user via /projects (worked_hours = all time total)"""
    result = {}
    count = 0
    
    r = requests.get(
        "https://app.trackingtime.co/api/v4/projects",
        headers=get_auth_header(email, password),
        timeout=15
    )
    if r.ok:
        for p in r.json().get("data", []):
            name = (p.get("name") or "").strip()
            hours = float(p.get("worked_hours") or 0)
            if not hours and p.get("accumulated_time"):
                hours = float(p["accumulated_time"]) / 3600
            if name and hours > 0:
                result[name] = hours
                count += 1
    
    # Fallback pe events daca projects nu returneaza nimic
    if count == 0:
        r = requests.get(
            "https://app.trackingtime.co/api/v4/events",
            headers=get_auth_header(email, password),
            timeout=15
        )
        if r.ok:
            for evt in r.json().get("data", []):
                name = (evt.get("p") or evt.get("c") or "").strip()
                secs = float(evt.get("d") or 0)
                if name and secs > 0:
                    result[name] = result.get(name, 0) + secs / 3600
                    count += 1
    
    return result, count

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/hours", methods=["GET"])
def get_hours():
    """Returneaza orele per proiect pentru toti userii (all time via /projects)"""
    combined = {}
    user_stats = []

    for user in USERS:
        if not user["password"]:
            continue
        
        user_hours, count = get_user_hours(user["email"], user["password"])
        for name, hours in user_hours.items():
            combined[name] = combined.get(name, 0) + hours
        
        user_stats.append({"user": user["name"], "events": count})

    return jsonify({
        "projects": {k: round(v, 4) for k, v in combined.items()},
        "count": len(combined),
        "users": user_stats
    })

@app.route("/hours/alltime", methods=["GET"])
def get_hours_alltime():
    """Alias pentru /hours - toate orele via /projects sunt deja all time"""
    return get_hours()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
