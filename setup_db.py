"""Run once to create the app_users table and default admin account."""
import bcrypt
from db import get_connection, load_config

def setup():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin','staff','customer') NOT NULL DEFAULT 'customer',
                    staff_id SMALLINT UNSIGNED NULL,
                    customer_id SMALLINT UNSIGNED NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL,
                    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()

            # Create default admin
            cfg = load_config()
            admin_user = cfg.get("admin_username", "admin")
            admin_pass = cfg.get("admin_password", "Admin@1234")
            pw_hash = bcrypt.hashpw(admin_pass.encode(), bcrypt.gensalt()).decode()

            cur.execute("SELECT user_id FROM app_users WHERE username = %s", (admin_user,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO app_users (username, password_hash, role) VALUES (%s, %s, 'admin')",
                    (admin_user, pw_hash),
                )
                conn.commit()
                print(f"Admin account created: {admin_user}")
            else:
                print("Admin account already exists.")

            # Create accounts for existing staff
            cur.execute("SELECT staff_id, first_name, last_name, email FROM staff")
            for s in cur.fetchall():
                uname = s["email"].split("@")[0].lower()
                cur.execute("SELECT user_id FROM app_users WHERE staff_id = %s", (s["staff_id"],))
                if not cur.fetchone():
                    pw = bcrypt.hashpw("Staff@1234".encode(), bcrypt.gensalt()).decode()
                    cur.execute(
                        "INSERT INTO app_users (username, password_hash, role, staff_id) VALUES (%s, %s, 'staff', %s)",
                        (uname, pw, s["staff_id"]),
                    )
                    print(f"Staff account created: {uname} (password: Staff@1234)")
            conn.commit()

        print("Setup complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    setup()
