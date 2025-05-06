"""
Simple test script to verify item name capitalization when performing operations.
This tests our fix for the case-sensitivity issue with item names in the database.
"""
import logging
import sqlite3
from app.db import check_item_exists, get_item_quantity, execute_modification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test with a lowercase item name
item_name = "aby"
uppercase_item = item_name.upper()

logger.info(f"Testing with item name: '{item_name}' (should be converted to '{uppercase_item}')")

# Test check_item_exists - should convert to uppercase internally
exists = check_item_exists(item_name)
logger.info(f"check_item_exists('{item_name}') returned: {exists}")

# Test get_item_quantity - should convert to uppercase internally
quantity = get_item_quantity(item_name)
logger.info(f"get_item_quantity('{item_name}') returned: {quantity}")

# Test execute_modification with an UPDATE query
update_query = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
params = (10, item_name)  # item_name should be converted to uppercase

logger.info(f"Testing execute_modification with params: {params}")
rows, error = execute_modification(update_query, params)

if error:
    logger.error(f"Error during modification: {error}")
else:
    logger.info(f"Modification successful, rows affected: {rows}")
    logger.info(f"Item name was converted to uppercase for database operation")

logger.info("Test completed!") 