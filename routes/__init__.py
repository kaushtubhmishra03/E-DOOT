from routes.main import main_bp
from routes.auth import auth_bp
from routes.app_routes import app_routes_bp
from routes.emergency_routes import emergency_bp
from routes.portal_routes import portal_bp
from routes.api_routes import api_bp

__all__ = ["main_bp", "auth_bp", "app_routes_bp", "emergency_bp", "portal_bp", "api_bp"]
