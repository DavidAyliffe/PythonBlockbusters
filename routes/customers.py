import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import role_required, validate_email, validate_password
from db import query, execute

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/customers")
@role_required("admin", "staff")
def index():
    search = request.args.get("search", "").strip()
    sql = """
        SELECT c.customer_id, c.first_name, c.last_name, c.email, c.active,
               c.created_date, s.store_id
        FROM customer c
        JOIN store s ON c.store_id = s.store_id
    """
    args = []
    if search:
        sql += " WHERE (c.first_name LIKE %s OR c.last_name LIKE %s OR c.email LIKE %s)"
        args.extend([f"%{search}%"] * 3)
    sql += " ORDER BY c.last_name, c.first_name"
    customers = query(sql, args)
    return render_template("customers.html", customers=customers, search=search)


@customers_bp.route("/customers/<int:cid>")
@role_required("admin", "staff")
def detail(cid):
    customer = query(
        """SELECT c.*, s.name AS store_name,
                  a.address, ci.city
           FROM customer c
           JOIN store s ON c.store_id = s.store_id
           JOIN address a ON c.address_id = a.address_id
           JOIN city ci ON a.city_id = ci.city_id
           WHERE c.customer_id = %s""",
        (cid,), one=True,
    )
    if not customer:
        return "Customer not found", 404

    total_rentals = query(
        "SELECT COUNT(*) AS cnt FROM rental WHERE customer_id = %s",
        (cid,), one=True,
    )
    active_rentals = query(
        "SELECT COUNT(*) AS cnt FROM rental WHERE customer_id = %s AND returned_date IS NULL",
        (cid,), one=True,
    )
    total_spent = query(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM payment WHERE customer_id = %s",
        (cid,), one=True,
    )
    favorite_category = query(
        """SELECT c.name AS category, COUNT(*) AS cnt
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film_category fc ON i.film_id = fc.film_id
           JOIN category c ON fc.category_id = c.category_id
           WHERE r.customer_id = %s
           GROUP BY c.category_id, c.name
           ORDER BY cnt DESC LIMIT 1""",
        (cid,), one=True,
    )
    rentals = query(
        """SELECT r.rental_id, r.rental_date, r.returned_date,
                  f.title, f.film_id,
                  COALESCE(p.amount, 0) AS amount
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film f ON i.film_id = f.film_id
           LEFT JOIN payment p ON p.rental_id = r.rental_id
           WHERE r.customer_id = %s
           ORDER BY r.rental_date DESC LIMIT 50""",
        (cid,),
    )
    top_categories = query(
        """SELECT c.name AS category, COUNT(*) AS cnt
           FROM rental r
           JOIN inventory i ON r.inventory_id = i.inventory_id
           JOIN film_category fc ON i.film_id = fc.film_id
           JOIN category c ON fc.category_id = c.category_id
           WHERE r.customer_id = %s
           GROUP BY c.category_id, c.name
           ORDER BY cnt DESC LIMIT 5""",
        (cid,),
    )

    return render_template(
        "customer_detail.html", customer=customer,
        total_rentals=total_rentals["cnt"] if total_rentals else 0,
        active_rentals=active_rentals["cnt"] if active_rentals else 0,
        total_spent=float(total_spent["total"]) if total_spent else 0,
        favorite_category=favorite_category["category"] if favorite_category else "N/A",
        rentals=rentals or [],
        top_categories=top_categories or [],
    )


@customers_bp.route("/customers/add", methods=["GET", "POST"])
@role_required("admin", "staff")
def add():
    stores = query("SELECT store_id FROM store ORDER BY store_id")
    if request.method == "POST":
        first = request.form["first_name"].strip()
        last = request.form["last_name"].strip()
        email = request.form["email"].strip()
        store_id = request.form["store_id"]
        username = request.form["username"].strip()
        password = request.form["password"]

        errors = []
        if not first or not last:
            errors.append("First and last name are required.")
        if not validate_email(email):
            errors.append("Invalid email address.")
        errors.extend(validate_password(password))
        if query("SELECT user_id FROM app_users WHERE username = %s", (username,), one=True):
            errors.append("Username already taken.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("customer_form.html", stores=stores, editing=False)

        address_id = query("SELECT address_id FROM address LIMIT 1", one=True)["address_id"]
        cust_id = execute(
            """INSERT INTO customer (store_id, first_name, last_name, email, address_id, active)
               VALUES (%s, %s, %s, %s, %s, 1)""",
            (store_id, first, last, email, address_id),
        )
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        execute(
            "INSERT INTO app_users (username, password_hash, role, customer_id) VALUES (%s, %s, 'customer', %s)",
            (username, pw_hash, cust_id),
        )
        flash("Customer added successfully.", "success")
        return redirect(url_for("customers.index"))

    return render_template("customer_form.html", stores=stores, editing=False)


@customers_bp.route("/customers/<int:cid>/edit", methods=["GET", "POST"])
@role_required("admin", "staff")
def edit(cid):
    customer = query("SELECT * FROM customer WHERE customer_id = %s", (cid,), one=True)
    if not customer:
        return "Customer not found", 404
    stores = query("SELECT store_id FROM store ORDER BY store_id")

    if request.method == "POST":
        first = request.form["first_name"].strip()
        last = request.form["last_name"].strip()
        email = request.form["email"].strip()
        store_id = request.form["store_id"]
        active = 1 if request.form.get("active") else 0

        errors = []
        if not first or not last:
            errors.append("First and last name are required.")
        if not validate_email(email):
            errors.append("Invalid email address.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("customer_form.html", stores=stores, customer=customer, editing=True)

        execute(
            """UPDATE customer SET store_id=%s, first_name=%s, last_name=%s, email=%s, active=%s
               WHERE customer_id=%s""",
            (store_id, first, last, email, active, cid),
        )
        flash("Customer updated.", "success")
        return redirect(url_for("customers.index"))

    return render_template("customer_form.html", stores=stores, customer=customer, editing=True)


@customers_bp.route("/customers/<int:cid>/delete", methods=["POST"])
@role_required("admin")
def delete(cid):
    execute("DELETE FROM app_users WHERE customer_id = %s", (cid,))
    execute("UPDATE customer SET active = 0 WHERE customer_id = %s", (cid,))
    flash("Customer deactivated.", "info")
    return redirect(url_for("customers.index"))
