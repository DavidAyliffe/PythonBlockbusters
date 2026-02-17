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
