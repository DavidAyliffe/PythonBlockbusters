"""
routes/auth.py - Authentication routes and helpers.

Handles user login, registration, logout, and provides decorators
for protecting routes by login status or user role.
"""
import re
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import query, execute

# Blueprint for all authentication-related routes
auth_bp = Blueprint("auth", __name__)


def validate_password(pw):
    """Validate password strength. Returns a list of error messages (empty if valid).

    Requirements: min 8 chars, uppercase, lowercase, digit, special character.
    """
    errors = []
    if len(pw) < 8:
        errors.append("Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", pw):
        errors.append("Password must contain an uppercase letter.")
    if not re.search(r"[a-z]", pw):
        errors.append("Password must contain a lowercase letter.")
    if not re.search(r"\d", pw):
        errors.append("Password must contain a digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pw):
        errors.append("Password must contain a special character.")
    return errors


def validate_email(email):
    """Check whether the given string looks like a valid email address."""
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email)


def get_current_user():
    """Return the currently logged-in user's record, or None if not authenticated."""
    uid = session.get("user_id")
    if not uid:
        return None
    return query("SELECT * FROM v_users WHERE id = %s", (uid,), one=True)


def role_required(*roles):
    """Decorator that restricts a route to users with one of the specified roles.

    Usage: @role_required("admin", "staff")
    Redirects to login if not authenticated, or to dashboard if insufficient role.
    """
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please log in.", "warning")
                return redirect(url_for("auth.login"))
            if user["role"] not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def login_required(f):
    """Decorator that restricts a route to any authenticated user.

    Redirects to the login page if the user is not logged in.
    """
    from functools import wraps

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            flash("Please log in.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapped


# --- Routes ---

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle the login page. GET shows the form, POST authenticates the user."""
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        # Look up the user and verify the password hash
        user = query("SELECT * FROM v_users WHERE username = %s", (username,), one=True)
        if user and hashlib.sha256(password.encode()).hexdigest() == user["password_hash"]:
            # Store user info in the session
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["username"] = user["username"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard.index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle the registration page. Creates a new customer account."""
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()

        # Validate all input fields
        errors = []
        if not username:
            errors.append("Username is required.")
        if not validate_email(email):
            errors.append("Invalid email address.")
        if password != confirm:
            errors.append("Passwords do not match.")
        errors.extend(validate_password(password))
        if query("SELECT user_id FROM v_users WHERE username = %s", (username,), one=True):
            errors.append("Username already taken.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html")

        # Create a new customer record (uses first available address and store)
        address_id = query("SELECT address_id FROM address LIMIT 1", one=True)["address_id"]
        store_id = query("SELECT store_id FROM store LIMIT 1", one=True)["store_id"]
        execute(
            """INSERT INTO customer (store_id, first_name, last_name, email, address_id, active)
               VALUES (%s, %s, %s, %s, %s, 1)""",
            (store_id, first_name, last_name, email, address_id),
        )
        # Retrieve the newly created customer's ID
        customer_id = query(
            "SELECT customer_id FROM customer WHERE email = %s ORDER BY customer_id DESC LIMIT 1",
            (email,), one=True
        )["customer_id"]

        # Create the corresponding app_users login record
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        execute(
            "INSERT INTO app_users (username, password_hash, role, customer_id) VALUES (%s, %s, 'customer', %s)",
            (username, pw_hash, customer_id),
        )
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    """Log the user out by clearing the session and redirecting to login."""
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
