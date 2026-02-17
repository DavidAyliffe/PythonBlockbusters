import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import role_required, validate_email, validate_password
from db import query, execute

staff_bp = Blueprint("staff", __name__)


@staff_bp.route("/staff")
@role_required("admin")
def index():
    members = query(
        """SELECT s.staff_id, s.first_name, s.last_name, s.email, s.active, s.store_id,
                  u.username
           FROM staff s
           LEFT JOIN app_users u ON u.staff_id = s.staff_id
           ORDER BY s.last_name"""
    )
    return render_template("staff.html", members=members)


@staff_bp.route("/staff/add", methods=["GET", "POST"])
@role_required("admin")
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
            errors.append("First and last name required.")
        if not validate_email(email):
            errors.append("Invalid email address.")
        errors.extend(validate_password(password))
        if query("SELECT user_id FROM app_users WHERE username = %s", (username,), one=True):
            errors.append("Username already taken.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("staff_form.html", stores=stores, editing=False)

        address_id = query("SELECT address_id FROM address LIMIT 1", one=True)["address_id"]
        sid = execute(
            """INSERT INTO staff (first_name, last_name, email, store_id, address_id, active, username)
               VALUES (%s, %s, %s, %s, %s, 1, %s)""",
            (first, last, email, store_id, address_id, username),
        )
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        execute(
            "INSERT INTO app_users (username, password_hash, role, staff_id) VALUES (%s, %s, 'staff', %s)",
            (username, pw_hash, sid),
        )
        flash("Staff member added.", "success")
        return redirect(url_for("staff.index"))

    return render_template("staff_form.html", stores=stores, editing=False)


@staff_bp.route("/staff/<int:sid>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit(sid):
    member = query("SELECT * FROM staff WHERE staff_id = %s", (sid,), one=True)
    if not member:
        return "Staff not found", 404
    stores = query("SELECT store_id FROM store ORDER BY store_id")

    if request.method == "POST":
        first = request.form["first_name"].strip()
        last = request.form["last_name"].strip()
        email = request.form["email"].strip()
        store_id = request.form["store_id"]
        active = 1 if request.form.get("active") else 0

        errors = []
        if not first or not last:
            errors.append("First and last name required.")
        if not validate_email(email):
            errors.append("Invalid email address.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("staff_form.html", stores=stores, member=member, editing=True)

        execute(
            "UPDATE staff SET first_name=%s, last_name=%s, email=%s, store_id=%s, active=%s WHERE staff_id=%s",
            (first, last, email, store_id, active, sid),
        )
        flash("Staff member updated.", "success")
        return redirect(url_for("staff.index"))

    return render_template("staff_form.html", stores=stores, member=member, editing=True)


@staff_bp.route("/staff/<int:sid>/delete", methods=["POST"])
@role_required("admin")
def delete(sid):
    execute("DELETE FROM app_users WHERE staff_id = %s", (sid,))
    execute("UPDATE staff SET active = 0 WHERE staff_id = %s", (sid,))
    flash("Staff member deactivated.", "info")
    return redirect(url_for("staff.index"))
