"""Generate PNG profile picture avatars for every customer in the database."""
import json
import os
import hashlib
import math
import random
import pymysql
import pymysql.cursors
from PIL import Image, ImageDraw, ImageFont

AVATAR_DIR = os.path.join(os.path.dirname(__file__), "static", "avatars")
SIZE = 200

# Pleasing background colour palettes (pairs for gradient)
PALETTE = [
    ((99, 102, 241),  (129, 140, 248)),   # indigo
    ((236, 72, 153),  (244, 114, 182)),    # pink
    ((14, 165, 233),  (56, 189, 248)),     # sky
    ((168, 85, 247),  (192, 132, 252)),    # purple
    ((245, 158, 11),  (251, 191, 36)),     # amber
    ((20, 184, 166),  (45, 212, 191)),     # teal
    ((239, 68, 68),   (248, 113, 113)),    # red
    ((34, 197, 94),   (74, 222, 128)),     # green
    ((59, 130, 246),  (96, 165, 250)),     # blue
    ((217, 70, 239),  (232, 121, 249)),    # fuchsia
]


def _seed_from_name(first, last):
    """Deterministic seed so the same customer always gets the same avatar."""
    return int(hashlib.md5(f"{first}{last}".encode()).hexdigest(), 16)


def _try_load_font(size):
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


def _draw_gradient_circle(img, color1, color2, size):
    """Draw a circular gradient background."""
    draw = ImageDraw.Draw(img)
    for y in range(size):
        ratio = y / size
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # Apply circular mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)
    return draw


def _draw_pattern(draw, seed, color1, size):
    """Add subtle decorative pattern."""
    rng = random.Random(seed)
    # Draw a few subtle circles in the background
    for _ in range(rng.randint(2, 4)):
        cx = rng.randint(0, size)
        cy = rng.randint(0, size)
        radius = rng.randint(30, 80)
        alpha = rng.randint(20, 50)
        lighter = (
            min(255, color1[0] + 40),
            min(255, color1[1] + 40),
            min(255, color1[2] + 40),
            alpha,
        )
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=lighter,
        )


def generate_avatar(customer_id, first_name, last_name):
    seed = _seed_from_name(first_name, last_name)
    rng = random.Random(seed)
    color1, color2 = PALETTE[seed % len(PALETTE)]

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Gradient background circle
    _draw_gradient_circle(img, color1, color2, SIZE)

    # Overlay for pattern
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    _draw_pattern(overlay_draw, seed, color1, SIZE)
    img = Image.alpha_composite(img, overlay)

    # Re-apply circular mask after compositing
    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    img.putalpha(mask)

    # Draw initials
    draw = ImageDraw.Draw(img)
    initials = (first_name[0] + last_name[0]).upper()
    font = _try_load_font(72)

    draw.text(
        (SIZE // 2, SIZE // 2),
        initials,
        font=font,
        fill=(255, 255, 255),
        anchor="mm",
    )

    out_path = os.path.join(AVATAR_DIR, f"{customer_id}.png")
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    os.makedirs(AVATAR_DIR, exist_ok=True)

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
                SELECT customer_id, first_name, last_name
                FROM customer
                ORDER BY customer_id
            """)
            customers = cur.fetchall()
    finally:
        conn.close()

    print(f"Generating {len(customers)} avatars...")
    for i, c in enumerate(customers, 1):
        generate_avatar(c["customer_id"], c["first_name"], c["last_name"])
        if i % 100 == 0:
            print(f"  {i}/{len(customers)} done")

    print(f"Done! {len(customers)} avatars saved to {AVATAR_DIR}")


if __name__ == "__main__":
    main()
