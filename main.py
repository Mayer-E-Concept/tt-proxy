from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import base64
import hashlib
import os
import time

app = Flask(__name__)

# ── CORS: doar originea aplicatiei (GitHub Pages). Suprascrie cu env ALLOWED_ORIGINS. ──
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://mayer-e-concept.github.io"
).split(",") if o.strip()]
CORS(app, origins=ALLOWED_ORIGINS, allow_headers=["Authorization", "Content-Type"])

USERS = [
    {"name": "Marius Poenar",  "email": os.environ.get("TT_EMAIL",   "m.poenar@me-concept.de"), "password": os.environ.get("TT_PASSWORD",   "")},
    {"name": "Ioan Chindea",   "email": os.environ.get("TT_EMAIL_2", "i.chindea@me-concept.de"), "password": os.environ.get("TT_PASSWORD_2", "")},
    {"name": "Stefan Picu",    "email": os.environ.get("TT_EMAIL_3", "s.picu@me-concept.de"),    "password": os.environ.get("TT_PASSWORD_3", "")},
    {"name": "Martin Mayer",   "email": os.environ.get("TT_EMAIL_4", "m.mayer@me-concept.de"),   "password": os.environ.get("TT_PASSWORD_4", "")},
    {"name": "Vadim Rosca",    "email": os.environ.get("TT_EMAIL_5", "v.rosca@me-concept.de"),   "password": os.environ.get("TT_PASSWORD_5", "")},
]

# ── Autorizare: tokenul MSAL al userului e validat la Graph /me.
#    Daca ALLOWED_EMAILS e setat (lista separata prin virgula), doar acele adrese trec. ──
ALLOWED_EMAILS = {e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()}
_token_cache = {}   # sha256(token) -> (email, expiry_epoch)
_TOKEN_TTL = 300    # 5 minute

def validate_request():
    """Returneaza (email, None) daca tokenul e valid (+ in whitelist daca e setata),
    altfel (None, (mesaj, status_http))."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, ("missing_token", 401)
    token = auth[7:].strip()
    if not token:
        return None, ("missing_token", 401)

    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    cached = _token_cache.get(key)
    if cached and cached[1] > now:
        email = cached[0]
    else:
        try:
            r = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": "Bearer " + token},
                timeout=10,
            )
        except requests.RequestException:
            return None, ("graph_unreachable", 503)
        if r.status_code != 200:
            return None, ("invalid_token", 401)
        me = r.json()
        email = (me.get("mail") or me.get("userPrincipalName") or "").lower()
        # curata intrarile expirate, apoi cache
        for k in [k for k, v in _token_cache.items() if v[1] <= now]:
            _token_cache.pop(k, None)
        _token_cache[key] = (email, now + _TOKEN_TTL)

    if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
        return None, ("forbidden", 403)
    return email, None

def get_auth_header(email, password):
    encoded = base64.b64encode(f"{email}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}

def tt_get(path, email, password):
    r = requests.get(
        f"https://app.trackingtime.co{path}",
        headers=get_auth_header(email, password),
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
    Fiecare user vede worked_hours = totalul ECHIPEI pentru proiectele la care e member.
    Agregam de la toti userii, deduplicam dupa nume, luam valoarea maxima.
    Astfel obtinem totalul corect indiferent de cine e member in ce proiect.
    """
    email, err = validate_request()
    if err:
        msg, status = err
        return jsonify({"error": msg}), status

    all_projects = {}  # {project_name: max_worked_hours}

    for user in USERS:
        if not user["password"]:
            continue
        d = tt_get("/api/v4/projects", user["email"], user["password"])
        if not d:
            continue
        for p in d.get("data", []):
            name = (p.get("name") or "").strip()
            hours = float(p.get("worked_hours") or 0)
            if name and hours > all_projects.get(name, -1):
                all_projects[name] = hours

    result = {k: round(v, 4) for k, v in all_projects.items() if v > 0}

    return jsonify({
        "projects": result,
        "count": len(result)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
