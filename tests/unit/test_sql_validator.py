import pytest

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.sql_validator import validate_sql, validate_update_statement

def test_validate_sql_select():
    """Test validation of SELECT statements."""
    # Valid SELECT statement
    valid_sql = "SELECT item, quantity_available FROM inventory WHERE item = ?"
    assert validate_sql(valid_sql) is True
    
    # Invalid SELECT statement (invalid table)
    invalid_sql = "SELECT item FROM products WHERE item = ?"
    assert validate_sql(invalid_sql) is False
    
    # Invalid SELECT statement (invalid column)
    invalid_sql = "SELECT item, price FROM inventory WHERE item = ?"
    assert validate_sql(invalid_sql) is False

def test_validate_sql_update_record_sale():
    """Test validation of UPDATE statements for recording sales."""
    # Valid UPDATE statement for recording a sale
    valid_sql = "UPDATE inventory SET quantity_sold = quantity_sold + ?, quantity_available = quantity_available - ? WHERE item = ?"
    assert validate_sql(valid_sql) is True
    
    # Another valid format
    valid_sql = "UPDATE inventory SET quantity_available = quantity_available - ?, quantity_sold = quantity_sold + ? WHERE item = ?"
    assert validate_sql(valid_sql) is True
    
    # Valid with ID
    valid_sql = "UPDATE inventory SET quantity_sold = quantity_sold + ?, quantity_available = quantity_available - ? WHERE id = ?"
    assert validate_sql(valid_sql) is True

def test_validate_sql_update_add_stock():
    """Test validation of UPDATE statements for adding stock."""
    # Valid UPDATE statement for adding stock
    valid_sql = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
    assert validate_sql(valid_sql) is True
    
    # Valid with ID
    valid_sql = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE id = ?"
    assert validate_sql(valid_sql) is True

def test_validate_sql_update_invalid():
    """Test validation of invalid UPDATE statements."""
    # Invalid table
    invalid_sql = "UPDATE products SET quantity_available = quantity_available + ? WHERE item = ?"
    assert validate_sql(invalid_sql) is False
    
    # No WHERE clause
    invalid_sql = "UPDATE inventory SET quantity_available = quantity_available + ?"
    assert validate_sql(invalid_sql) is False
    
    # Invalid column in WHERE clause
    invalid_sql = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE product_name = ?"
    assert validate_sql(invalid_sql) is False
    
    # Direct assignment instead of increment/decrement
    invalid_sql = "UPDATE inventory SET quantity_available = ? WHERE item = ?"
    assert validate_sql(invalid_sql) is False
    
    # Attempt to update disallowed columns
    invalid_sql = "UPDATE inventory SET unit_price = ? WHERE item = ?"
    assert validate_sql(invalid_sql) is False

def test_validate_update_statement_direct():
    """Test the direct validation of UPDATE statements."""
    # Valid record sale
    valid_sql = "UPDATE inventory SET quantity_sold = quantity_sold + ?, quantity_available = quantity_available - ? WHERE item = ?"
    assert validate_update_statement(valid_sql) is True
    
    # Valid add stock
    valid_sql = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
    assert validate_update_statement(valid_sql) is True
    
    # Invalid patterns
    invalid_sql = "UPDATE inventory SET quantity_available = ? WHERE item = ?"
    assert validate_update_statement(invalid_sql) is False
    
    # Direct updates to quantity_sold without incrementing
    invalid_sql = "UPDATE inventory SET quantity_sold = ? WHERE item = ?"
    assert validate_update_statement(invalid_sql) is False

def test_multiple_statements_rejection():
    """Test that multiple SQL statements are rejected."""
    # Multiple statements
    invalid_sql = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?; DELETE FROM inventory;"
    assert validate_sql(invalid_sql) is False

def test_non_update_rejection():
    """Test that non-UPDATE statements are rejected by validate_update_statement."""
    # SELECT statement
    invalid_sql = "SELECT * FROM inventory WHERE item = ?"
    assert validate_update_statement(invalid_sql) is False
    
    # DELETE statement
    invalid_sql = "DELETE FROM inventory WHERE item = ?"
    assert validate_update_statement(invalid_sql) is False
    
    # INSERT statement
    invalid_sql = "INSERT INTO inventory (item, quantity_available) VALUES (?, ?)"
    assert validate_update_statement(invalid_sql) is False 