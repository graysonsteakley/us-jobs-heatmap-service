from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .routes import register_routes
from .settings import load_settings


def create_app() -> Flask:
    settings = load_settings()
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    register_routes(app, settings)
    return app
