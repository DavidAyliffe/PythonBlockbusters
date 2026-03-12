"""
generate_avatars.py - Generates circular PNG avatar images for every customer.

Each avatar features:
  - A gradient background circle using a colour from a fixed palette.
  - Subtle decorative pattern circles for visual variety.
  - The customer's initials centred in white text.

Avatars are deterministic: the same customer name always produces the same design.
Output directory: static/avatars/<customer_id>.png
"""
import json
import os
import hashlib
import math
import random
import pymysql
import pymysql.cursors
from PIL import Image, ImageDraw, ImageFont

# Output directory for generated avatars
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "static", "avatars")

# Avatar dimensions in pixels
SIZE = 200

# Gradient colour pairs (top colour, bottom colour) used as backgrounds
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
    """Create a deterministic integer seed from a customer's name,
    ensuring the same name always produces the same avatar."""
    return int(hashlib.md5(f"{first}{last}".encode()).hexdigest(), 16)


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


def _draw_gradient_circle(img, color1, color2, size):
    """Draw a vertical gradient across the image, then mask it into a circle."""
    draw = ImageDraw.Draw(img)
    # Draw horizontal lines with interpolated colours to form the gradient
    for y in range(size):
        ratio = y / size
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # Apply a circular mask so only the circle area is visible
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)
    return draw


def _draw_pattern(draw, seed, color1, size):
    """Draw a few semi-transparent decorative circles for visual interest."""
    rng = random.Random(seed)
    for _ in range(rng.randint(2, 4)):
        cx = rng.randint(0, size)
        cy = rng.randint(0, size)
        radius = rng.randint(30, 80)
        alpha = rng.randint(20, 50)
        # Slightly lighter variant of the background colour
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
    """Generate and save a single avatar PNG for the given customer.

    Args:
        customer_id: Used as the output filename (<customer_id>.png).
        first_name:  Customer's first name (first initial used).
        last_name:   Customer's last name (second initial used).

    Returns:
        The file path of the saved avatar image.
    """
    seed = _seed_from_name(first_name, last_name)
    rng = random.Random(seed)
    color1, color2 = PALETTE[seed % len(PALETTE)]

    # Start with a transparent canvas
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Draw the gradient background circle
    _draw_gradient_circle(img, color1, color2, SIZE)

    # Overlay decorative pattern on a separate layer then composite
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    _draw_pattern(overlay_draw, seed, color1, SIZE)
    img = Image.alpha_composite(img, overlay)

    # Re-apply the circular mask after compositing (pattern may extend beyond)
    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    img.putalpha(mask)

    # Draw the customer's initials in the centre
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

    # Save the final image
    out_path = os.path.join(AVATAR_DIR, f"{customer_id}.png")
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    """Fetch all customers from the database and generate an avatar for each one."""
    os.makedirs(AVATAR_DIR, exist_ok=True)

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
            cur.execute("""
                SELECT customer_id, first_name, last_name
                FROM customer
                ORDER BY customer_id
            """)
            customers = cur.fetchall()
    finally:
        conn.close()

    # Generate avatars with progress reporting every 100 customers
    print(f"Generating {len(customers)} avatars...")
    for i, c in enumerate(customers, 1):
        generate_avatar(c["customer_id"], c["first_name"], c["last_name"])
        if i % 100 == 0:
            print(f"  {i}/{len(customers)} done")

    print(f"Done! {len(customers)} avatars saved to {AVATAR_DIR}")


# Run the generator when executed directly
if __name__ == "__main__":
    main()
