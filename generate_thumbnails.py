"""Generate PNG thumbnail posters for every film in the database."""
import json
import os
import hashlib
import pymysql
import pymysql.cursors
from PIL import Image, ImageDraw, ImageFont

THUMB_DIR = os.path.join(os.path.dirname(__file__), "static", "thumbnails")
WIDTH, HEIGHT = 200, 300

# Category -> colour palette (gradient top, gradient bottom)
CATEGORY_COLORS = {
    "Action":           ((180, 30, 30),   (80, 10, 10)),
    "Adult":            ((100, 20, 60),   (50, 10, 30)),
    "Animation":        ((50, 180, 220),  (20, 80, 120)),
    "Children":         ((255, 180, 50),  (200, 100, 20)),
    "Classics":         ((60, 60, 80),    (30, 30, 50)),
    "Comedy":           ((255, 200, 50),  (200, 130, 10)),
    "Crime":            ((40, 40, 50),    (20, 20, 30)),
    "Documentary":      ((50, 130, 80),   (20, 70, 40)),
    "Drama":            ((100, 50, 120),  (50, 20, 70)),
    "Family":           ((80, 180, 130),  (30, 100, 70)),
    "Foreign":          ((60, 100, 160),  (30, 50, 100)),
    "Games":            ((30, 160, 160),  (10, 80, 80)),
    "Horror":           ((30, 30, 30),    (10, 10, 10)),
    "Music":            ((200, 80, 160),  (120, 30, 90)),
    "Romantic Comedy":  ((220, 100, 120), (150, 40, 60)),
    "Sci-Fi":           ((20, 40, 100),   (10, 15, 50)),
    "Sports":           ((40, 140, 40),   (15, 70, 15)),
    "Travel":           ((50, 150, 200),  (20, 80, 130)),
    "War":              ((80, 70, 50),    (40, 35, 20)),
    "Westerns":         ((160, 110, 50),  (90, 60, 20)),
}
DEFAULT_COLORS = ((70, 70, 90), (35, 35, 50))

RATING_BADGE = {
    "G":     (76, 175, 80),
    "PG":    (33, 150, 243),
    "PG-13": (255, 152, 0),
    "R":     (244, 67, 54),
    "NC-17": (156, 39, 176),
}


def _seed_from_title(title):
    """Deterministic seed so the same film always gets the same design."""
    return int(hashlib.md5(title.encode()).hexdigest(), 16)


def _draw_gradient(draw, top_color, bot_color, width, height):
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_decorative_shapes(draw, seed, top_color, width, height):
    """Add some geometric shapes for visual interest."""
    import random
    rng = random.Random(seed)

    # Draw a few circles / ellipses
    for _ in range(rng.randint(2, 5)):
        cx = rng.randint(-30, width + 30)
        cy = rng.randint(40, height - 80)
        rx = rng.randint(20, 80)
        ry = rng.randint(20, 80)
        alpha = rng.randint(15, 40)
        color = (
            min(255, top_color[0] + rng.randint(-30, 60)),
            min(255, top_color[1] + rng.randint(-30, 60)),
            min(255, top_color[2] + rng.randint(-30, 60)),
            alpha,
        )
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color)

    # Draw a few diagonal lines
    for _ in range(rng.randint(1, 3)):
        x1 = rng.randint(-20, width)
        y1 = rng.randint(0, height)
        x2 = x1 + rng.randint(40, 150)
        y2 = y1 + rng.randint(-100, 100)
        lw = rng.randint(1, 3)
        color = (255, 255, 255, rng.randint(10, 30))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=lw)


def _try_load_font(size):
    """Try to load a nice font, fall back to default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_thumbnail(film_id, title, rating, release_year, category):
    top_c, bot_c = CATEGORY_COLORS.get(category, DEFAULT_COLORS)
    seed = _seed_from_title(title)

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Background gradient
    _draw_gradient(draw, top_c, bot_c, WIDTH, HEIGHT)

    # Decorative shapes
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    _draw_decorative_shapes(overlay_draw, seed, top_c, WIDTH, HEIGHT)
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Dark band at bottom for title
    draw.rectangle([(0, HEIGHT - 90), (WIDTH, HEIGHT)], fill=(0, 0, 0, 160))

    # Film icon at top
    icon_font = _try_load_font(40)
    draw.text((WIDTH // 2, 30), "🎬", font=icon_font, fill=(255, 255, 255, 180), anchor="mt")

    # Title text (wrapped)
    title_font = _try_load_font(16)
    small_font = _try_load_font(12)

    # Wrap title
    display_title = title.title()
    words = display_title.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] > WIDTH - 20:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    lines = lines[:3]  # max 3 lines

    y_text = HEIGHT - 85
    for line in lines:
        draw.text((WIDTH // 2, y_text), line, font=title_font, fill="white", anchor="mt")
        y_text += 20

    # Year
    draw.text((WIDTH // 2, HEIGHT - 25), str(release_year), font=small_font, fill=(200, 200, 200), anchor="mt")

    # Rating badge (top right)
    if rating:
        badge_color = RATING_BADGE.get(rating, (100, 100, 100))
        badge_font = _try_load_font(11)
        bbox = draw.textbbox((0, 0), rating, font=badge_font)
        bw = bbox[2] - bbox[0] + 12
        bh = bbox[3] - bbox[1] + 8
        bx = WIDTH - bw - 8
        by = 8
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=4, fill=badge_color)
        draw.text((bx + bw // 2, by + bh // 2), rating, font=badge_font, fill="white", anchor="mm")

    # Save as RGB PNG
    final = img.convert("RGB")
    out_path = os.path.join(THUMB_DIR, f"{film_id}.png")
    final.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    os.makedirs(THUMB_DIR, exist_ok=True)

    with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
        cfg = json.load(f)["db"]

    conn = pymysql.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"],
        password=cfg["password"], database=cfg["database"],
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.film_id, f.title, f.rating, f.release_year, c.name AS category
                FROM film f
                LEFT JOIN film_category fc ON f.film_id = fc.film_id
                LEFT JOIN category c ON fc.category_id = c.category_id
                ORDER BY f.film_id
            """)
            films = cur.fetchall()
    finally:
        conn.close()

    print(f"Generating {len(films)} thumbnails...")
    for i, film in enumerate(films, 1):
        generate_thumbnail(
            film["film_id"], film["title"], film["rating"],
            film["release_year"], film.get("category", ""),
        )
        if i % 100 == 0:
            print(f"  {i}/{len(films)} done")

    print(f"Done! {len(films)} thumbnails saved to {THUMB_DIR}")


if __name__ == "__main__":
    main()
