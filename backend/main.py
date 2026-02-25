import logging
import os
import sys

# Ensure backend and root are in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from backend.database.connection import init_db
from backend.api.routes import routes_bp
from backend.api.health import health_bp

# ── Setup ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("v2x_backend")

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize Database
    init_db()

    # Register Blueprints
    app.register_blueprint(routes_bp)
    app.register_blueprint(health_bp, url_prefix="/health_check") # Avoid conflict with /health

    # ── Serve Frontend SPA ──────────────────────────────────────
    # React build is in ../frontend/dist (or frontend/dist relative to root)
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path):
        if path != "" and os.path.exists(os.path.join(dist_path, path)):
            return send_from_directory(dist_path, path)
        else:
            return send_from_directory(dist_path, "index.html")

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
