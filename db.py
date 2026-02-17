import json
import pymysql
import pymysql.cursors

def load_config():
    with open("config.json") as f:
        return json.load(f)

def get_connection():
    cfg = load_config()["db"]
    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

def query(sql, args=None, one=False):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            rows = cur.fetchall()
            return rows[0] if one and rows else rows if not one else None
    finally:
        conn.close()

def execute(sql, args=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()
