import logging
from app.sql_validator import validate_sql, validate_update_statement

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Test query for record sale with multi-line SET clause
record_sale_query = """
            UPDATE inventory 
            SET quantity_sold = quantity_sold + ?, 
                quantity_available = quantity_available - ? 
            WHERE item = ?
            """

# Test both validators
print("\nTesting validate_sql function with record sale query:")
result1 = validate_sql(record_sale_query)
print(f"validate_sql result: {result1}")

print("\nTesting validate_update_statement function directly:")
result2 = validate_update_statement(record_sale_query)
print(f"validate_update_statement result: {result2}")

# Test with a simpler record sale query
simple_record_sale = "UPDATE inventory SET quantity_sold = quantity_sold + ?, quantity_available = quantity_available - ? WHERE item = ?"
print("\nTesting with simplified record sale query:")
result3 = validate_update_statement(simple_record_sale)
print(f"validate_update_statement result: {result3}") 