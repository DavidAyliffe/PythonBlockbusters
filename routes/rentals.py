from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from routes.auth import login_required, get_current_user, role_required
from db import query, execute

rentals_bp = Blueprint("rentals", __name__)


@rentals_bp.route("/rentals")
@login_required
def index():
    user = get_current_user()
    if user["role"] == "customer":
        sql = """
            SELECT r.rental_id, r.rental_date, r.returned_date,
                   f.title, f.film_id, s.store_id,
                   CONCAT(st.first_name, ' ', st.last_name) AS staff_name
            FROM rental r
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            JOIN store s ON i.store_id = s.store_id
            JOIN staff st ON r.staff_id = st.staff_id
            WHERE r.customer_id = %s
            ORDER BY r.rental_date DESC
        """
        rentals = query(sql, (user["customer_id"],))
    else:
        search = request.args.get("search", "").strip()
        sql = """
            SELECT r.rental_id, r.rental_date, r.returned_date,
                   f.title, f.film_id, s.store_id,
                   CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                   c.customer_id,
                   CONCAT(st.first_name, ' ', st.last_name) AS staff_name
            FROM rental r
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            JOIN store s ON i.store_id = s.store_id
            JOIN customer c ON r.customer_id = c.customer_id
            JOIN staff st ON r.staff_id = st.staff_id
        """
        args = []
        if search:
            sql += " WHERE (f.title LIKE %s OR c.first_name LIKE %s OR c.last_name LIKE %s)"
            args.extend([f"%{search}%"] * 3)
        sql += " ORDER BY r.rental_date DESC LIMIT 500"
        rentals = query(sql, args)
        return render_template("rentals.html", rentals=rentals, search=search)

    return render_template("rentals.html", rentals=rentals, search="")


@rentals_bp.route("/rentals/new", methods=["GET", "POST"])
@role_required("admin", "staff")
def new_rental():
    if request.method == "POST":
        customer_id = request.form["customer_id"]
        film_id = request.form["film_id"]
        store_id = request.form["store_id"]

        user = get_current_user()
        staff_id = user.get("staff_id")
        if not staff_id:
            staff = query("SELECT staff_id FROM staff WHERE store_id = %s LIMIT 1", (store_id,), one=True)
            staff_id = staff["staff_id"] if staff else 1

        inv = query(
            """SELECT i.inventory_id
               FROM inventory i
               LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.returned_date IS NULL
               WHERE i.film_id = %s AND i.store_id = %s AND r.rental_id IS NULL
               LIMIT 1""",
            (film_id, store_id), one=True,
        )
        if not inv:
            flash("No copies available at this store.", "danger")
            return redirect(url_for("rentals.new_rental"))

        execute(
            "INSERT INTO rental (rental_date, inventory_id, customer_id, staff_id) VALUES (NOW(), %s, %s, %s)",
            (inv["inventory_id"], customer_id, staff_id),
        )
        flash("Rental created successfully.", "success")
        return redirect(url_for("rentals.index"))

    customers = query("SELECT customer_id, first_name, last_name, email FROM customer WHERE active = 1 ORDER BY last_name")
    films = query("SELECT film_id, title FROM film ORDER BY title")
    stores = query("SELECT store_id FROM store ORDER BY store_id")
    return render_template("rental_form.html", customers=customers, films=films, stores=stores)


@rentals_bp.route("/rentals/<int:rid>/return", methods=["POST"])
@role_required("admin", "staff")
def return_rental(rid):
    rental = query("SELECT * FROM rental WHERE rental_id = %s", (rid,), one=True)
    if not rental:
        flash("Rental not found.", "danger")
        return redirect(url_for("rentals.index"))
    if rental["returned_date"]:
        flash("Already returned.", "info")
        return redirect(url_for("rentals.index"))

    execute("UPDATE rental SET returned_date = NOW() WHERE rental_id = %s", (rid,))

    # Insert payment with late fee calculation
    film = query(
        """SELECT f.rental_rate, f.rental_duration
           FROM rental r JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film f ON i.film_id = f.film_id WHERE r.rental_id = %s""",
        (rid,), one=True,
    )
    base_rate = float(film["rental_rate"]) if film else 4.99
    rental_duration = int(film["rental_duration"]) if film else 3

    from datetime import datetime, timedelta
    due_date = rental["rental_date"] + timedelta(days=rental_duration)
    now = datetime.now()
    days_overdue = max(0, (now - due_date).days)
    late_fee = days_overdue * 1.00
    amount = base_rate + late_fee

    execute(
        "INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date) VALUES (%s, %s, %s, %s, NOW())",
        (rental["customer_id"], rental["staff_id"], rid, amount),
    )

    if late_fee > 0:
        flash(
            f"Rental returned. Base: ${base_rate:.2f} + Late fee: ${late_fee:.2f} ({days_overdue} days overdue) = ${amount:.2f}",
            "warning",
        )
    else:
        flash(f"Rental returned. Payment of ${amount:.2f} recorded.", "success")
    return redirect(url_for("rentals.index"))


@rentals_bp.route("/api/inventory/<int:film_id>/<int:store_id>")
@login_required
def check_inventory(film_id, store_id):
    row = query(
        """SELECT COUNT(*) AS available
           FROM inventory i
           LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.returned_date IS NULL
           WHERE i.film_id = %s AND i.store_id = %s AND r.rental_id IS NULL""",
        (film_id, store_id), one=True,
    )
    return jsonify({"available": row["available"] if row else 0})
