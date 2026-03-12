"""
app.py - Main application entry point for the Blockbusters Flask web app.

Creates and configures the Flask application, registers all route blueprints,
sets up the page view tracking system, and provides global template context.
"""
import json
import re
import sys
import os
from flask import Flask, request as flask_request
from markupsafe import Markup

# Ensure the project root is on the Python path so local modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_app():
    """Factory function that creates and configures the Flask application instance."""
    app = Flask(__name__)

    # Load configuration from config.json (copy config.example.json to get started)
    with open("config.json") as f:
        cfg = json.load(f)
    app.secret_key = cfg.get("secret_key", "dev-secret-key")

    # Create the page_views table if it doesn't exist, used for tracking site-wide page views
    from db import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS page_views (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    view_count BIGINT NOT NULL DEFAULT 0
                ) ENGINE=InnoDB
            """)
            # Ensure there is exactly one row to hold the counter
            cur.execute("SELECT id FROM page_views WHERE id = 1")
            if not cur.fetchone():
                cur.execute("INSERT INTO page_views (id, view_count) VALUES (1, 0)")
            conn.commit()
    finally:
        conn.close()

    # --- Template helpers ---

    def store_icon_filename(store_name):
        """Convert a store name (e.g. "Oscar's Choice Video") into a sanitised
        SVG filename path like 'store_icons/oscars_choice_video.svg'."""
        if not store_name:
            return None
        name = store_name.lower()
        # Normalise possessives and ampersands
        name = name.replace("'s ", "s_").replace("'", "")
        name = name.replace(" & ", "_and_")
        # Replace any remaining non-alphanumeric characters with underscores
        name = re.sub(r'[^a-z0-9]+', '_', name)
        name = name.strip('_')
        return f"store_icons/{name}.svg"

    @app.template_filter('store_icon')
    def store_icon_filter(store_name):
        """Jinja2 filter that renders an <img> tag for a store's icon, given its name."""
        filename = store_icon_filename(store_name)
        if not filename:
            return ""
        return Markup(
            f'<img src="/static/{filename}" alt="" width="20" height="20" '
            f'class="rounded me-1" style="vertical-align: text-bottom;">'
        )

    # --- Register route blueprints ---
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.films import films_bp
    from routes.customers import customers_bp
    from routes.rentals import rentals_bp
    from routes.staff import staff_bp
    from routes.payments import payments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(films_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(rentals_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(payments_bp)

    # --- Middleware ---

    @app.before_request
    def track_page_views():
        """Increment the global page view counter for every non-static request."""
        if flask_request.endpoint and not flask_request.path.startswith('/static'):
            from db import execute
            execute("UPDATE page_views SET view_count = view_count + 1 WHERE id = 1")

    # --- Global template context ---

    from routes.auth import get_current_user

    @app.context_processor
    def inject_globals():
        """Make the current user and page view count available in every template."""
        from db import query
        row = query("SELECT view_count FROM page_views WHERE id = 1", one=True)
        page_views = row["view_count"] if row else 0
        return {"current_user": get_current_user(), "page_views": page_views}

    return app


# Run the development server when executed directly
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)
