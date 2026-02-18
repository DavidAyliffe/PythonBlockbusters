import json
import re
import sys
import os
from flask import Flask, request as flask_request
from markupsafe import Markup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(__name__)
    with open("config.json") as f:
        cfg = json.load(f)
    app.secret_key = cfg.get("secret_key", "dev-secret-key")

    # Create page_views table
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
            cur.execute("SELECT id FROM page_views WHERE id = 1")
            if not cur.fetchone():
                cur.execute("INSERT INTO page_views (id, view_count) VALUES (1, 0)")
            conn.commit()
    finally:
        conn.close()

    # Store icon helper: converts store name to icon filename
    def store_icon_filename(store_name):
        if not store_name:
            return None
        name = store_name.lower()
        name = name.replace("'s ", "s_").replace("'", "")
        name = name.replace(" & ", "_and_")
        name = re.sub(r'[^a-z0-9]+', '_', name)
        name = name.strip('_')
        return f"store_icons/{name}.svg"

    @app.template_filter('store_icon')
    def store_icon_filter(store_name):
        filename = store_icon_filename(store_name)
        if not filename:
            return ""
        return Markup(
            f'<img src="/static/{filename}" alt="" width="20" height="20" '
            f'class="rounded me-1" style="vertical-align: text-bottom;">'
        )

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

    # Increment page view counter on each page request
    @app.before_request
    def track_page_views():
        if flask_request.endpoint and not flask_request.path.startswith('/static'):
            from db import execute
            execute("UPDATE page_views SET view_count = view_count + 1 WHERE id = 1")

    # Inject user and page view count into all templates
    from routes.auth import get_current_user
    @app.context_processor
    def inject_globals():
        from db import query
        row = query("SELECT view_count FROM page_views WHERE id = 1", one=True)
        page_views = row["view_count"] if row else 0
        return {"current_user": get_current_user(), "page_views": page_views}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)
