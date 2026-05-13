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

def fetch_events(email, password, date_from=None, date_to=None):
    """Preia events cu paginare corecta (page incepe de la 0)"""
    all_events = []
    page = 0
    today = datetime.now().strftime("%Y-%m-%d")
    
    while True:
        params = {"page": page}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to or today
            
        r = requests.get(
            "https://app.trackingtime.co/api/v4/events",
            headers=get_auth_header(email, password),
            params=params,
            timeout=30
        )
        if not r.ok:
            break
        
        items = r.json().get("data", [])
        if not items:
            break
        
        # Evita duplicatele verificand ID-ul
        existing_ids = {e.get("id") for e in all_events}
        new_items = [i for i in items if i.get("id") not in existing_ids]
        if not new_items:
            break
            
        all_events.extend(new_items)
        
        # Daca pagina curenta are mai putine decat precedenta, am terminat
        if len(items) < 10:
            break
            
        page += 1
        if page > 30:
            break
    
    return all_events

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/debug_vadim", methods=["GET"])
def debug_vadim():
    user = USERS[4]  # Vadim
    r = requests.get(
        "https://app.trackingtime.co/api/v4/events",
        headers=get_auth_header(user["email"], user["password"]),
        timeout=15
    )
    if not r.ok:
        return jsonify({"error": r.status_code})
    items = r.json().get("data", [])
    return jsonify({
        "count": len(items),
        "total_hours": round(sum(float(e.get("d", 0)) for e in items) / 3600, 2),
        "by_project": {
            name: round(sum(float(e.get("d", 0)) for e in items if (e.get("p") or "") == name) / 3600, 2)
            for name in set(e.get("p", "") for e in items)
        },
        "events_summary": [{"project": e.get("p"), "date": e.get("s", "")[:10], "hours": round(float(e.get("d", 0))/3600, 2)} for e in items]
    })


def get_hours():
    """Sync standard - ultimele 12 luni"""
    date_from = "2025-01-01"
    date_to = datetime.now().strftime("%Y-%m-%d")
    return _get_hours(date_from, date_to)

@app.route("/hours/alltime", methods=["GET"])
def get_hours_alltime():
    """Sync complet - din 2020"""
    return _get_hours("2020-01-01", datetime.now().strftime("%Y-%m-%d"))

def _get_hours(date_from, date_to):
    result = {}
    user_stats = []

    for user in USERS:
        if not user["password"]:
            continue
        count = 0

        # Strategia principala: /projects cu worked_hours (total acurat)
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

        # Fallback pe events daca projects nu are date
        if count == 0:
            events = fetch_events(user["email"], user["password"], date_from, date_to)
            for evt in events:
                name = (evt.get("p") or evt.get("c") or "").strip()
                secs = float(evt.get("d") or 0)
                if name and secs > 0:
                    result[name] = result.get(name, 0) + secs / 3600
                    count += 1

        user_stats.append({"user": user["name"], "events": count})

    return jsonify({
        "projects": {k: round(v, 4) for k, v in result.items()},
        "count": len(result),
        "users": user_stats,
        "range": "all time (via projects)"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
