# app/db.py
import pathlib
import sqlite3
import os
import logging
from typing import Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variable for DB URL or default to 'inventory.db' in the project root
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "inventory.db"
DATABASE_URL = os.getenv("DATABASE_URL", str(DEFAULT_DB_PATH))

logger.info(f"Database path configured to: {DATABASE_URL}")
logger.info(f"Database absolute path: {os.path.abspath(DATABASE_URL)}")

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
        conn.row_factory = sqlite3.Row # Return rows as dict-like objects
        logger.info(f"Successfully connected to database: {DATABASE_URL}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database {DATABASE_URL}: {e}")
        # Re-raise as a standard Exception for the application to handle startup failure if needed
        raise Exception(f"Database connection failed: {e}")


def init_db():
    """
    Initializes the database, ensuring the 'inventory' table exists
    with the correct schema. Populates with sample data if empty.
    """
    logger.info("Attempting to initialize database tables (inventory table)...")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create inventory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE NOT NULL,
            unit_cost REAL,
            unit_price REAL,
            quantity_sold INTEGER DEFAULT 0,
            quantity_available INTEGER DEFAULT 0
        );""")
        logger.info("Table 'inventory' checked/created.")

        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM inventory;")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("Inventory table is empty. Inserting sample data.")
            sample_data = [
                ("LAPTOP", 500.0, 800.0, 10, 50),
                ("KEYBOARD", 20.0, 35.0, 5, 100),
                ("MONITOR", 100.0, 150.0, 7, 30),
                ("MOUSE", 10.0, 20.0, 12, 200),
                ("PRINTER", 80.0, 120.0, 3, 15)
            ]
            cursor.executemany(
                "INSERT INTO inventory (item, unit_cost, unit_price, quantity_sold, quantity_available) VALUES (?, ?, ?, ?, ?);",
                sample_data
            )
            logger.info("Sample inventory data inserted.")

        conn.commit()
        logger.info("Database initialization complete (inventory table).")
    except sqlite3.Error as e:
        logger.error(f"Error during database initialization: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: tuple = ()):
    """
    Executes a given SQL SELECT query safely using parameters.
    Raises ValueError on database errors, including the original error message.
    """
    # Basic check remains, though primary validation happens in api.py
    if not query.strip().upper().startswith("SELECT"):
         logger.warning(f"Blocked non-SELECT query intended for execution: {query}")
         # Raise ValueError consistent with other potential failures
         raise ValueError("Query execution failed: Only SELECT queries are allowed currently for safety.")

    logger.info(f"Attempting to execute query: '{query}' with params: {params}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)

        results = cursor.fetchall()
        results_list = [dict(row) for row in results]
        logger.info(f"Query executed successfully. Rows returned: {len(results_list)}")
        return results_list
    # --- Improved Error Handling ---
    except sqlite3.Error as db_err:
        # Catch specific SQLite errors (like syntax errors, missing columns/tables etc.)
        error_message = f"Database query failed: [{type(db_err).__name__}] {db_err}"
        logger.error(error_message + f" | Query: {query} | Params: {params}")
        # Re-raise as ValueError for the API layer to catch consistently
        raise ValueError(error_message)
    except Exception as e:
        # Catch any other unexpected errors during execution
        error_message = f"Unexpected error during query execution: {repr(e)}"
        logger.error(error_message + f" | Query: {query} | Params: {params}")
        # Re-raise as ValueError
        raise ValueError(error_message)
    # --- End Improved Error Handling ---
    finally:
        if conn:
            conn.close()

def execute_modification(sql_template: str, params: tuple) -> Tuple[int, str | None]:
    """
    Executes a modification query (UPDATE) with transaction support.
    Returns tuple of (rows_affected, error_message).
    Error message is None if successful, string with error details otherwise.
    
    Note: This function handles transaction management for data modifications.
    """
    conn = None
    rows_affected = 0
    error_message = None
    
    # Ensure uppercase item names for consistency in WHERE clauses
    # If the last parameter is the item name (typical for WHERE item = ?), convert to uppercase
    if params and isinstance(params[-1], str):
        # Convert parameters to list to modify
        params_list = list(params)
        params_list[-1] = params_list[-1].upper()
        # Convert back to tuple
        params = tuple(params_list)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Execute the query
        cursor.execute(sql_template, params)
        rows_affected = cursor.rowcount
        
        # Commit the transaction if successful
        conn.commit()
        
        logger.info(f"Modification executed successfully. Rows affected: {rows_affected}")
        
    except sqlite3.Error as e:
        # Rollback the transaction on error
        if conn:
            conn.rollback()
        error_message = f"Database error during modification: {e}"
        logger.error(error_message)
    except Exception as e:
        # Rollback the transaction on any other error
        if conn:
            conn.rollback()
        error_message = f"Unexpected error during modification: {e}"
        logger.error(error_message)
    finally:
        if conn:
            conn.close()
    
    return rows_affected, error_message

def check_item_exists(item_name: str) -> bool:
    """
    Checks if an item exists in the inventory.
    Returns True if the item exists, False otherwise.
    Converts item name to uppercase for consistency.
    """
    # Convert item name to uppercase
    item_name = item_name.upper()
    query = "SELECT 1 FROM inventory WHERE item = ? LIMIT 1"
    
    try:
        results = execute_query(query, (item_name,))
        return len(results) > 0
    except ValueError:
        return False

def get_item_quantity(item_name: str) -> int:
    """
    Gets the current available quantity of an item in the inventory.
    Returns the quantity if the item exists, 0 otherwise.
    Converts item name to uppercase for consistency.
    """
    # Convert item name to uppercase
    item_name = item_name.upper()
    query = "SELECT quantity_available FROM inventory WHERE item = ? LIMIT 1"
    
    try:
        results = execute_query(query, (item_name,))
        if results and len(results) > 0:
            return results[0].get('quantity_available', 0)
        return 0
    except ValueError:
        return 0

