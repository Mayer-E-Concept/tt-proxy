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

@app.route("/hours")
@app.route("/hours/alltime")
def get_hours():
    """
    Agregate proiecte de la toti userii.
    Deduplicam dupa nume de proiect si luam valoarea MAXIMA (= totalul echipei).
    Astfel, chiar daca un proiect e vazut de mai multi useri, luam totalul corect.
    Si daca un proiect e vazut doar de un singur user, tot il includem.
    """
    all_projects = {}  # {project_name: max_worked_hours}
    user_stats = []

    for user in USERS:
        if not user["password"]:
            continue
        d = tt_get("/api/v4/projects", user["email"], user["password"])
        count = 0
        if d:
            items = d.get("data", [])
            for p in items:
                name = (p.get("name") or "").strip()
                hours = float(p.get("worked_hours") or 0)
                if name:
                    # Luam maximul - totalul echipei e intotdeauna >= totalul individual
                    if name not in all_projects or hours > all_projects[name]:
                        all_projects[name] = hours
                    count += 1
        user_stats.append({"user": user["name"], "projects_visible": count})

    # Filtreaza proiectele cu 0 ore
    result = {k: round(v, 4) for k, v in all_projects.items() if v > 0}

    return jsonify({
        "projects": result,
        "count": len(result),
        "users": user_stats
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
