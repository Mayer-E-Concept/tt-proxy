from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

TT_EMAIL = os.environ.get("TT_EMAIL", "m.poenar@me-concept.de")
TT_PASSWORD = os.environ.get("TT_PASSWORD", "")

def get_auth_header():
    credentials = f"{TT_EMAIL}:{TT_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}

def fetch_all_pages(base_url, params=None):
    """Fetch all pages from a paginated endpoint"""
    all_items = []
    page = 1
    headers = get_auth_header()
    
    while True:
        p = (params or {}).copy()
        p["page"] = page
        p["per_page"] = 100
        
        r = requests.get(base_url, headers=headers, params=p, timeout=15)
        if not r.ok:
            break
        
        data = r.json()
        items = data.get("data", [])
        
        if not isinstance(items, list) or not items:
            break
        
        all_items.extend(items)
        
        # Stop if we got less than per_page (last page)
        if len(items) < 100:
            break
        
        page += 1
        if page > 20:  # Safety limit
            break
    
    return all_items

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/hours", methods=["GET"])
def get_hours():
    """Returneaza orele lucrate per proiect agregat din events"""
    try:
        year = datetime.now().year
        
        # Strategia 1: Agregate din events (mai precis)
        events = fetch_all_pages(
            "https://app.trackingtime.co/api/v4/events",
            {"from": f"{year}-01-01", "to": f"{year}-12-31"}
        )
        
        result = {}
        
        if events:
            for evt in events:
                # Campul "c" sau "p" = project name, "d" = duration in seconds
                name = (evt.get("c") or evt.get("p") or "").strip()
                duration_sec = float(evt.get("d") or 0)
                if name and duration_sec > 0:
                    result[name] = result.get(name, 0) + duration_sec / 3600
        
        # Strategia 2: Fallback pe /projects daca events e gol
        if not result:
            projects = fetch_all_pages("https://app.trackingtime.co/api/v4/projects")
            for p in projects:
                name = (p.get("name") or "").strip()
                hours = float(p.get("worked_hours") or 0)
                if not hours and p.get("accumulated_time"):
                    hours = float(p["accumulated_time"]) / 3600
                if name:
                    result[name] = hours
        
        # Rotunjire
        result = {k: round(v, 1) for k, v in result.items()}
        
        return jsonify({
            "projects": result,
            "count": len(result),
            "source": "events" if events else "projects"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
