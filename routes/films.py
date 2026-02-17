from flask import Blueprint, render_template, request
from routes.auth import login_required
from db import query

films_bp = Blueprint("films", __name__)


@films_bp.route("/films")
@login_required
def index():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "")
    rating = request.args.get("rating", "")
    year = request.args.get("year", "")

    sql = """
        SELECT DISTINCT f.film_id, f.title, f.release_year, f.rating, f.rental_rate,
               f.length, c.name AS category
        FROM film f
        LEFT JOIN film_category fc ON f.film_id = fc.film_id
        LEFT JOIN category c ON fc.category_id = c.category_id
        WHERE 1=1
    """
    args = []

    if search:
        sql += " AND (f.title LIKE %s OR f.description LIKE %s)"
        args.extend([f"%{search}%", f"%{search}%"])
    if category:
        sql += " AND c.name = %s"
        args.append(category)
    if rating:
        sql += " AND f.rating = %s"
        args.append(rating)
    if year:
        sql += " AND f.release_year = %s"
        args.append(year)

    sql += " ORDER BY f.title"
    films = query(sql, args)

    categories = query("SELECT name FROM category ORDER BY name")
    ratings = query("SELECT DISTINCT rating FROM film ORDER BY rating")
    years = query("SELECT DISTINCT release_year FROM film ORDER BY release_year DESC")

    return render_template(
        "films.html", films=films, categories=categories, ratings=ratings,
        years=years, search=search, sel_category=category, sel_rating=rating, sel_year=year,
    )


@films_bp.route("/films/<int:film_id>")
@login_required
def detail(film_id):
    film = query(
        """SELECT f.*, c.name AS category, l.name AS language
           FROM film f
           LEFT JOIN film_category fc ON f.film_id = fc.film_id
           LEFT JOIN category c ON fc.category_id = c.category_id
           LEFT JOIN language l ON f.language_id = l.language_id
           WHERE f.film_id = %s""",
        (film_id,), one=True,
    )
    if not film:
        return "Film not found", 404

    actors = query(
        """SELECT a.first_name, a.last_name
           FROM actor a
           JOIN film_actor fa ON a.actor_id = fa.actor_id
           WHERE fa.film_id = %s ORDER BY a.last_name""",
        (film_id,),
    )

    inventory = query(
        """SELECT s.store_id,
                  a.address AS store_address,
                  ci.name,
                  COUNT(i.inventory_id) AS total_copies,
                  SUM(CASE WHEN r.rental_id IS NULL OR r.returned_date IS NOT NULL THEN 1 ELSE 0 END) AS available
           FROM inventory i
           JOIN store s ON i.store_id = s.store_id
           JOIN address a ON s.address_id = a.address_id
           JOIN city ci ON a.city_id = ci.city_id
           LEFT JOIN rental r ON i.inventory_id = r.inventory_id
               AND r.returned_date IS NULL
           WHERE i.film_id = %s
           GROUP BY s.store_id, a.address, ci.name""",
        (film_id,),
    )

    return render_template("film_detail.html", film=film, actors=actors, inventory=inventory)
