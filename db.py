"""
db.py - Database helper module.

Provides convenience functions for connecting to the MySQL database
and executing queries. All functions open and close their own connections
(no connection pooling), keeping things simple for this application.
"""
import json
import pymysql
import pymysql.cursors


def load_config():
    """Load and return the full application configuration from config.json."""
    with open("config.json") as f:
        return json.load(f)


def get_connection():
    """Create and return a new PyMySQL connection using settings from config.json.
    Uses DictCursor so rows are returned as dictionaries, and autocommit is on."""
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
    """Execute a SELECT query and return the results.

    Args:
        sql:  The SQL query string (use %s placeholders for parameters).
        args: Tuple of parameters to safely substitute into the query.
        one:  If True, return only the first row (or None if no results).

    Returns:
        A single dict (if one=True) or a list of dicts.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            rows = cur.fetchall()
            return rows[0] if one and rows else rows if not one else None
    finally:
        conn.close()


def execute(sql, args=None):
    """Execute an INSERT, UPDATE, or DELETE statement.

    Args:
        sql:  The SQL statement string (use %s placeholders for parameters).
        args: Tuple of parameters to safely substitute into the statement.

    Returns:
        The last inserted row ID (useful after INSERT statements).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()
