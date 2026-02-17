from flask import Blueprint, render_template, jsonify, session
from routes.auth import login_required, get_current_user
from db import query

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    user = get_current_user()
    if user["role"] == "customer":
        return _customer_dashboard(user)
    return render_template("dashboard.html", user=user)


def _customer_dashboard(user):
    active = query(
        """SELECT r.rental_id, r.rental_date, f.title
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film f ON i.film_id = f.film_id
           WHERE r.customer_id = %s AND r.returned_date IS NULL
           ORDER BY r.rental_date DESC""",
        (user["customer_id"],),
    )
    history_count = query(
        "SELECT COUNT(*) AS cnt FROM rental WHERE customer_id = %s",
        (user["customer_id"],), one=True,
    )
    total_spent = query(
        "SELECT COALESCE(SUM(amount),0) AS total FROM payment WHERE customer_id = %s",
        (user["customer_id"],), one=True,
    )
    return render_template(
        "customer_dashboard.html", user=user, active_rentals=active,
        history_count=history_count["cnt"], total_spent=total_spent["total"],
    )


@dashboard_bp.route("/api/dashboard/stats")
@login_required
def stats():
    user = get_current_user()
    if user["role"] == "customer":
        return jsonify({}), 403

    today_rentals = query(
        "SELECT COUNT(*) AS cnt FROM rental WHERE DATE(rental_date) = CURDATE()", one=True
    )
    today_revenue = query(
        "SELECT COALESCE(SUM(amount),0) AS total FROM payment WHERE DATE(payment_date) = CURDATE()",
        one=True,
    )
    total_rentals = query("SELECT COUNT(*) AS cnt FROM rental", one=True)
    total_revenue = query("SELECT COALESCE(SUM(amount),0) AS total FROM payment", one=True)
    active_rentals = query(
        "SELECT COUNT(*) AS cnt FROM rental WHERE return_date IS NULL", one=True
    )
    overdue = query(
        """SELECT COUNT(*) AS cnt FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film f ON i.film_id = f.film_id
           WHERE r.returned_date IS NULL
             AND DATE_ADD(r.rental_date, INTERVAL f.rental_duration DAY) < NOW()""",
        one=True,
    )
    total_customers = query("SELECT COUNT(*) AS cnt FROM customer WHERE active = 1", one=True)
    total_films = query("SELECT COUNT(*) AS cnt FROM film", one=True)
    total_inventory = query("SELECT COUNT(*) AS cnt FROM inventory", one=True)

    # Top 10 films
    top_films = query(
        """SELECT f.title, COUNT(r.rental_id) AS rentals
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film f ON i.film_id = f.film_id
           GROUP BY f.film_id, f.title
           ORDER BY rentals DESC LIMIT 10"""
    )

    # Rentals by category
    by_category = query(
        """SELECT c.name AS category, COUNT(r.rental_id) AS rentals
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film_category fc ON i.film_id = fc.film_id
           JOIN category c ON fc.category_id = c.category_id
           GROUP BY c.category_id, c.name
           ORDER BY rentals DESC"""
    )

    # Revenue last 7 days (or months if no recent data)
    revenue_trend = query(
        """SELECT DATE(payment_date) AS day, SUM(amount) AS total
           FROM payment
           GROUP BY DATE(payment_date)
           ORDER BY day DESC LIMIT 30"""
    )

    # Rentals by store
    by_store = query(
        """SELECT s.store_id, COUNT(r.rental_id) AS rentals
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN store s ON i.store_id = s.store_id
           GROUP BY s.store_id ORDER BY s.store_id"""
    )

    # Inventory by rating
    by_rating = query(
        """SELECT f.rating, COUNT(i.inventory_id) AS count
           FROM inventory i
           JOIN film f ON i.film_id = f.film_id
           GROUP BY f.rating ORDER BY count DESC"""
    )

    return jsonify({
        "today_rentals": today_rentals["cnt"] if today_rentals else 0,
        "today_revenue": float(today_revenue["total"]) if today_revenue else 0,
        "total_rentals": total_rentals["cnt"] if total_rentals else 0,
        "total_revenue": float(total_revenue["total"]) if total_revenue else 0,
        "active_rentals": active_rentals["cnt"] if active_rentals else 0,
        "overdue_rentals": overdue["cnt"] if overdue else 0,
        "total_customers": total_customers["cnt"] if total_customers else 0,
        "total_films": total_films["cnt"] if total_films else 0,
        "total_inventory": total_inventory["cnt"] if total_inventory else 0,
        "top_films": top_films or [],
        "by_category": by_category or [],
        "revenue_trend": [{"day": str(r["day"]), "total": float(r["total"])} for r in (revenue_trend or [])],
        "by_store": by_store or [],
        "by_rating": by_rating or [],
    })
