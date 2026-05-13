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
    """Debug: ce endpoint-uri sunt disponibile"""
    results = {}
    
    # Lista useri
    for path in ["/api/v4/users", "/api/v4/accounts/657424/users", 
                  "/api/v4/team", "/api/v4/accounts/657424/team"]:
        d = tt_get(path)
        if d:
            items = d.get("data", [])
            results[path] = {
                "status": "ok",
                "count": len(items) if isinstance(items, list) else "N/A",
                "keys": list(d.keys()),
                "sample": items[0] if isinstance(items, list) and items else str(d)[:200]
            }
        else:
            results[path] = {"status": "failed"}
    
    # Events cu user_id param
    d = tt_get("/api/v4/events", {"all_users": "true"})
    if d:
        items = d.get("data", [])
        results["events_all_users"] = {"count": len(items)}
    
    d = tt_get("/api/v4/events", {"user_id": "all"})
    if d:
        items = d.get("data", [])
        results["events_user_all"] = {"count": len(items)}

    return jsonify(results)

@app.route("/hours", methods=["GET"])
def get_hours():
    """Returneaza orele per proiect pentru toti userii"""
    result = {}
    
    # Incearca sa obtina lista de useri
    users_data = tt_get("/api/v4/users")
    users = []
    if users_data and isinstance(users_data.get("data"), list):
        users = users_data["data"]
    
    if users:
        # Fetch events pentru fiecare user
        for user in users:
            uid = user.get("id") or user.get("uid")
            if not uid:
                continue
            d = tt_get("/api/v4/events", {"user_id": uid})
            if d:
                for evt in d.get("data", []):
                    name = (evt.get("c") or evt.get("p") or "").strip()
                    secs = float(evt.get("d") or 0)
                    if name and secs > 0:
                        result[name] = result.get(name, 0) + secs / 3600
    else:
        # Fallback: events pentru userul curent
        d = tt_get("/api/v4/events")
        if d:
            for evt in d.get("data", []):
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
        "count": len(result),
        "users_found": len(users)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
