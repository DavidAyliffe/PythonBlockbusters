import json
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(__name__)
    with open("config.json") as f:
        cfg = json.load(f)
    app.secret_key = cfg.get("secret_key", "dev-secret-key")

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.films import films_bp
    from routes.customers import customers_bp
    from routes.rentals import rentals_bp
    from routes.staff import staff_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(films_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(rentals_bp)
    app.register_blueprint(staff_bp)

    # Inject user into all templates
    from routes.auth import get_current_user
    @app.context_processor
    def inject_user():
        return {"current_user": get_current_user()}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)
