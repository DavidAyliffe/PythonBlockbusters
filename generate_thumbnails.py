"""
generate_thumbnails.py - Generates PNG poster thumbnails for every film.

Each thumbnail features:
  - A vertical gradient background coloured by film category.
  - Random decorative geometric shapes for visual variety.
  - The film title (word-wrapped) at the bottom.
  - The release year below the title.
  - A colour-coded rating badge (G, PG, PG-13, R, NC-17) in the top-right corner.

Thumbnails are deterministic: the same film title always produces the same design.
Output directory: static/thumbnails/<film_id>.png
"""
import json
import os
import hashlib
import pymysql
import pymysql.cursors
from PIL import Image, ImageDraw, ImageFont

# Output directory for generated thumbnails
THUMB_DIR = os.path.join(os.path.dirname(__file__), "static", "thumbnails")

# Thumbnail dimensions in pixels
WIDTH, HEIGHT = 200, 300

# Colour palettes per film category (gradient top colour, gradient bottom colour)
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
# Fallback colours for films with no/unknown category
DEFAULT_COLORS = ((70, 70, 90), (35, 35, 50))

# Badge background colours for each MPAA rating
RATING_BADGE = {
    "G":     (76, 175, 80),    # green
    "PG":    (33, 150, 243),   # blue
    "PG-13": (255, 152, 0),    # orange
    "R":     (244, 67, 54),    # red
    "NC-17": (156, 39, 176),   # purple
}


def _seed_from_title(title):
    """Create a deterministic integer seed from a film title,
    ensuring the same title always produces the same design."""
    return int(hashlib.md5(title.encode()).hexdigest(), 16)


def _draw_gradient(draw, top_color, bot_color, width, height):
    """Draw a vertical colour gradient from top_color to bot_color."""
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_decorative_shapes(draw, seed, top_color, width, height):
    """Add random semi-transparent circles and diagonal lines for visual interest."""
    import random
    rng = random.Random(seed)

    # Draw a few semi-transparent ellipses
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

    # Draw a few subtle diagonal lines
    for _ in range(rng.randint(1, 3)):
        x1 = rng.randint(-20, width)
        y1 = rng.randint(0, height)
        x2 = x1 + rng.randint(40, 150)
        y2 = y1 + rng.randint(-100, 100)
        lw = rng.randint(1, 3)
        color = (255, 255, 255, rng.randint(10, 30))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=lw)


def _try_load_font(size):
    """Attempt to load a system font at the given size.
    Falls back to Pillow's built-in default font if none are found."""
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
    """Generate and save a single poster thumbnail PNG for a film.

    Args:
        film_id:      Used as the output filename (<film_id>.png).
        title:        Film title displayed on the poster.
        rating:       MPAA rating string (G, PG, PG-13, R, NC-17).
        release_year: Year displayed below the title.
        category:     Film category used to pick the colour scheme.

    Returns:
        The file path of the saved thumbnail image.
    """
    top_c, bot_c = CATEGORY_COLORS.get(category, DEFAULT_COLORS)
    seed = _seed_from_title(title)

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Draw the category-coloured gradient background
    _draw_gradient(draw, top_c, bot_c, WIDTH, HEIGHT)

    # Composite decorative shapes on a transparent overlay
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    _draw_decorative_shapes(overlay_draw, seed, top_c, WIDTH, HEIGHT)
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Semi-transparent dark band at the bottom for the title area
    draw.rectangle([(0, HEIGHT - 90), (WIDTH, HEIGHT)], fill=(0, 0, 0, 160))

    # Film icon emoji at the top centre
    icon_font = _try_load_font(40)
    draw.text((WIDTH // 2, 30), "🎬", font=icon_font, fill=(255, 255, 255, 180), anchor="mt")

    # Word-wrap the title to fit within the poster width
    title_font = _try_load_font(16)
    small_font = _try_load_font(12)

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
    lines = lines[:3]  # Limit to 3 lines maximum

    # Draw each line of the title
    y_text = HEIGHT - 85
    for line in lines:
        draw.text((WIDTH // 2, y_text), line, font=title_font, fill="white", anchor="mt")
        y_text += 20

    # Release year below the title
    draw.text((WIDTH // 2, HEIGHT - 25), str(release_year), font=small_font, fill=(200, 200, 200), anchor="mt")

    # Rating badge in the top-right corner
    if rating:
        badge_color = RATING_BADGE.get(rating, (100, 100, 100))
        badge_font = _try_load_font(11)
        bbox = draw.textbbox((0, 0), rating, font=badge_font)
        bw = bbox[2] - bbox[0] + 12  # badge width with padding
        bh = bbox[3] - bbox[1] + 8   # badge height with padding
        bx = WIDTH - bw - 8          # position from right edge
        by = 8                        # position from top edge
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=4, fill=badge_color)
        draw.text((bx + bw // 2, by + bh // 2), rating, font=badge_font, fill="white", anchor="mm")

    # Convert to RGB (drop alpha) and save
    final = img.convert("RGB")
    out_path = os.path.join(THUMB_DIR, f"{film_id}.png")
    final.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    """Fetch all films from the database and generate a thumbnail for each one."""
    os.makedirs(THUMB_DIR, exist_ok=True)

    # Connect to the database using config.json credentials
    with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
        cfg = json.load(f)["db"]

    conn = pymysql.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"],
        password=cfg["password"], database=cfg["database"],
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            # Join with film_category and category to get the category name
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

    # Generate thumbnails with progress reporting every 100 films
    print(f"Generating {len(films)} thumbnails...")
    for i, film in enumerate(films, 1):
        generate_thumbnail(
            film["film_id"], film["title"], film["rating"],
            film["release_year"], film.get("category", ""),
        )
        if i % 100 == 0:
            print(f"  {i}/{len(films)} done")

    print(f"Done! {len(films)} thumbnails saved to {THUMB_DIR}")


# Run the generator when executed directly
if __name__ == "__main__":
    main()
