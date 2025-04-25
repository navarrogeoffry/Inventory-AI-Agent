# Updated app/db.py

import sqlite3
import os
import logging

# --- Configure logging, DATABASE_URL, get_db_connection, init_db (Same as before) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "inventory.db")
logger.info(f"Database path configured to: {DATABASE_URL}")

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        logger.info(f"Successfully connected to database: {DATABASE_URL}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database {DATABASE_URL}: {e}")
        raise

def init_db():
    """Initializes the database tables if they don't already exist..."""
    # ... (Same init_db function as before, containing CREATE TABLE statements) ...
    logger.info("Attempting to initialize database tables with updated schema...")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Create items table (Updated Schema based on user input)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE NOT NULL,
            unit_cost REAL,
            unit_price REAL,
            quantity_sold INTEGER DEFAULT 0,
            quantity_available INTEGER DEFAULT 0
        );""")
        logger.info("Table 'items' checked/created.")
        # Create transactions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           item_id INTEGER NOT NULL,
           type TEXT NOT NULL CHECK(type IN ('IN','OUT')),
           qty INTEGER NOT NULL,
           tx_date DATETIME DEFAULT CURRENT_TIMESTAMP,
           notes TEXT,
           FOREIGN KEY (item_id) REFERENCES items (id)
        );""")
        logger.info("Table 'transactions' checked/created.")
        # Create locations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );""")
        logger.info("Table 'locations' checked/created.")
        conn.commit()
        logger.info("Database initialization complete.")
    except sqlite3.Error as e:
        logger.error(f"Error during database initialization: {e}")
    finally:
        if conn:
            conn.close()


# === execute_query (Updated to accept params) ===
def execute_query(query: str, params: tuple = ()):
    """
    Executes a given SQL SELECT query safely using parameters.
    WARNING: Still assumes query has passed external validation.
    """
    # Basic check remains, though less critical now validation happens earlier
    if not query.strip().upper().startswith("SELECT"):
         logger.warning(f"Blocked non-SELECT query intended for execution: {query}")
         raise ValueError("Query execution failed: Only SELECT queries are allowed currently for safety.")

    logger.info(f"Attempting to execute query: '{query}' with params: {params}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Pass parameters directly to execute - this is the safe way
        cursor.execute(query, params)

        results = cursor.fetchall()
        results_list = [dict(row) for row in results]
        logger.info(f"Query executed successfully. Rows returned: {len(results_list)}")
        return results_list
    except sqlite3.Error as e:
        logger.error(f"Database error during query execution: {e} | Query: {query} | Params: {params}")
        raise ValueError(f"Database query failed: {e}")
    finally:
        if conn:
            conn.close()