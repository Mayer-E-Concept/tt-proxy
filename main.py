from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import base64
import os
from datetime import datetime, timedelta

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

def fetch_all_events(email, password, date_from, date_to):
    all_events = []
    page = 1
    while True:
        r = requests.get(
            "https://app.trackingtime.co/api/v4/events",
            headers=get_auth_header(email, password),
            params={"from": date_from, "to": date_to, "page": page},
            timeout=30
        )
        if not r.ok:
            break
        items = r.json().get("data", [])
        if not items:
            break
        all_events.extend(items)
        if len(items) < 50:  # TT default page size
            break
        page += 1
        if page > 50:
            break
    return all_events

def aggregate_hours(date_from, date_to):
    result = {}
    user_stats = []
    for user in USERS:
        if not user["password"]:
            continue
        count = 0
        events = fetch_all_events(user["email"], user["password"], date_from, date_to)
        for evt in events:
            name = (evt.get("p") or evt.get("c") or "").strip()
            secs = float(evt.get("d") or 0)
            if name and secs > 0:
                result[name] = result.get(name, 0) + secs / 3600
                count += 1
        if count == 0:
            r = requests.get(
                "https://app.trackingtime.co/api/v4/projects",
                headers=get_auth_header(user["email"], user["password"]),
                timeout=15
            )
            if r.ok:
                for p in r.json().get("data", []):
                    name = (p.get("name") or "").strip()
                    hours = float(p.get("worked_hours") or 0)
                    if not hours and p.get("accumulated_time"):
                        hours = float(p["accumulated_time"]) / 3600
                    if name and hours > 0:
                        result[name] = result.get(name, 0) + hours
                        count += 1
        user_stats.append({"user": user["name"], "events": count})
    return result, user_stats

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/hours", methods=["GET"])
def get_hours():
    """Sync standard - ultimele 12 luni (rapid)"""
    date_from = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")
    result, user_stats = aggregate_hours(date_from, date_to)
    return jsonify({
        "projects": {k: round(v, 4) for k, v in result.items()},
        "count": len(result),
        "users": user_stats,
        "range": f"{date_from} → {date_to}"
    })

@app.route("/hours/alltime", methods=["GET"])
def get_hours_alltime():
    """Sync complet - din 2020 pana azi (mai lent, pentru istoric complet)"""
    date_from = "2020-01-01"
    date_to = datetime.now().strftime("%Y-%m-%d")
    result, user_stats = aggregate_hours(date_from, date_to)
    return jsonify({
        "projects": {k: round(v, 4) for k, v in result.items()},
        "count": len(result),
        "users": user_stats,
        "range": f"{date_from} → {date_to}"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
