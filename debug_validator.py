import logging
from app.sql_validator import validate_sql, validate_update_statement

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Test query that's failing
query = """
            UPDATE inventory 
            SET quantity_available = quantity_available + ? 
            WHERE item = ?
            """

# Test both validators
print("\nTesting validate_sql function:")
result1 = validate_sql(query)
print(f"validate_sql result: {result1}")

print("\nTesting validate_update_statement function directly:")
result2 = validate_update_statement(query)
print(f"validate_update_statement result: {result2}")

# Test with a more simplified query format
simple_query = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
print("\nTesting with simplified query format:")
result3 = validate_update_statement(simple_query)
print(f"validate_update_statement result: {result3}") 