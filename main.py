from flask import Flask, jsonify
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)  # Allow requests from any origin (planificator pe GitHub Pages)

# Credentiale TrackingTime - setate ca variabile de mediu pe Railway
TT_EMAIL = os.environ.get("TT_EMAIL", "m.poenar@me-concept.de")
TT_PASSWORD = os.environ.get("TT_PASSWORD", "")  # Setezi pe Railway, nu in cod

def get_auth_header():
    credentials = f"{TT_EMAIL}:{TT_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}

@app.route("/raw", methods=["GET"])
def get_raw():
    """Returneaza raspunsul brut de la TrackingTime pentru debug"""
    try:
        response = requests.get(
            "https://app.trackingtime.co/api/v4/tasks",
            headers=get_auth_header(),
            timeout=10
        )
        return jsonify({
            "status_code": response.status_code,
            "raw": response.json()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/hours", methods=["GET"])
def get_hours():
    """Returneaza orele lucrate per proiect din TrackingTime"""
    try:
        response = requests.get(
            "https://app.trackingtime.co/api/v4/tasks",
            headers=get_auth_header(),
            timeout=10
        )
        
        if not response.ok:
            return jsonify({"error": f"TrackingTime API error: {response.status_code}"}), 500
        
        data = response.json()
        projects_raw = data.get("data", [])
        
        # Construim un dict simplu: {project_name: hours}
        result = {}
        for p in projects_raw:
            name = (p.get("name") or p.get("title") or "").strip()
            hours = float(p.get("worked_hours") or 0)
            if p.get("accumulated_time"):
                hours = float(p["accumulated_time"]) / 3600
            if name:
                result[name] = round(hours, 1)
        
        return jsonify({"projects": result, "count": len(result)})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
