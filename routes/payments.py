"""
routes/payments.py - Payment history routes.

Displays a searchable, filterable list of payment records.
Accessible to admin and staff roles only.
"""
from flask import Blueprint, render_template, request
from routes.auth import role_required
from db import query

# Blueprint for payment-related routes
payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/payments")
@role_required("admin", "staff")
def index():
    """Display the payment history with optional search and date range filters."""
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Base query joins payments with customer, rental, inventory, film, and store
    sql = """
        SELECT p.payment_id, p.amount, p.payment_date,
               CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
               c.customer_id,
               f.title, f.film_id,
               i.store_id, st.name AS store_name
        FROM payment p
        JOIN customer c ON p.customer_id = c.customer_id
        JOIN rental r ON p.rental_id = r.rental_id
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN store st ON i.store_id = st.store_id
        WHERE 1=1
    """
    args = []

    # Filter by customer name or film title
    if search:
        sql += " AND (c.first_name LIKE %s OR c.last_name LIKE %s OR f.title LIKE %s)"
        args.extend([f"%{search}%"] * 3)
    # Filter by start date
    if date_from:
        sql += " AND DATE(p.payment_date) >= %s"
        args.append(date_from)
    # Filter by end date
    if date_to:
        sql += " AND DATE(p.payment_date) <= %s"
        args.append(date_to)

    sql += " ORDER BY p.payment_date DESC LIMIT 500"
    payments = query(sql, args)

    # Calculate the total amount for the displayed payments
    total = sum(float(p["amount"]) for p in payments) if payments else 0

    return render_template(
        "payments.html", payments=payments, search=search,
        date_from=date_from, date_to=date_to, total=total,
    )
