import pytest

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.sql_validator import validate_sql, validate_update_statement, validate_expressions

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

def test_validate_calculated_columns():
    """Test validation of calculated columns in SELECT statements."""
    # Valid calculated column - simple arithmetic
    valid_sql = "SELECT item, (unit_price - unit_cost) AS profit_per_unit FROM inventory"
    assert validate_sql(valid_sql) is True
    
    # Valid calculated column - multiplication
    valid_sql = "SELECT item, (unit_price * quantity_sold) AS total_revenue FROM inventory"
    assert validate_sql(valid_sql) is True
    
    # Valid calculated column - multiple operations
    valid_sql = "SELECT item, (unit_price - unit_cost) * quantity_sold AS total_profit FROM inventory"
    assert validate_sql(valid_sql) is True
    
    # Invalid calculated column - uses unknown column
    invalid_sql = "SELECT item, (price - cost) AS profit FROM inventory"
    assert validate_sql(invalid_sql) is False
    
    # Invalid calculated column - uses unsafe SQL pattern
    invalid_sql = "SELECT item, CASE WHEN unit_price > 100 THEN 'high' ELSE 'low' END AS price_category FROM inventory"
    assert validate_sql(invalid_sql) is False
    
    # Test with multiple calculated columns
    valid_sql = """
    SELECT 
        item, 
        (unit_price - unit_cost) AS profit_per_unit,
        (unit_price - unit_cost) * quantity_sold AS total_profit 
    FROM inventory
    """
    assert validate_sql(valid_sql) is True

def test_validate_update_valid():
    """Test validation of valid UPDATE statements."""
    # Valid UPDATE for adding stock
    valid_sql = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
    assert validate_sql(valid_sql) is True
    
    # Valid UPDATE for recording a sale (single column)
    valid_sql = "UPDATE inventory SET quantity_available = quantity_available - ? WHERE item = ?"
    assert validate_sql(valid_sql) is True
    
    # Valid UPDATE for recording a sale (multiple columns)
    valid_sql = """
    UPDATE inventory 
    SET 
        quantity_sold = quantity_sold + ?,
        quantity_available = quantity_available - ?
    WHERE item = ?
    """
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

def test_validate_expressions():
    """Test the expression validation function directly."""
    # Valid expressions
    assert validate_expressions(["(unit_price - unit_cost)"]) is True
    assert validate_expressions(["quantity_sold * unit_price"]) is True
    assert validate_expressions(["(unit_price - unit_cost) * quantity_sold"]) is True
    
    # Invalid expressions - unknown columns
    assert validate_expressions(["(price - cost)"]) is False
    
    # Invalid expressions - unsafe patterns
    assert validate_expressions(["CASE WHEN unit_price > 10 THEN 'High' ELSE 'Low' END"]) is False
    assert validate_expressions(["(SELECT MAX(unit_price) FROM inventory)"]) is False
    assert validate_expressions(["unit_price; DROP TABLE inventory"]) is False

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