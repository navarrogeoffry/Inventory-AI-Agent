import pytest
import sqlite3
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import execute_modification, check_item_exists, get_item_quantity

class MockCursor:
    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.executed_query = None
        self.executed_params = None
    
    def execute(self, query, params=()):
        self.executed_query = query
        self.executed_params = params

class MockConnection:
    def __init__(self, cursor=None, raises=None):
        self.cursor_obj = cursor or MockCursor()
        self.committed = False
        self.closed = False
        self.rolled_back = False
        self.raises = raises
        self.executed_transactions = []
    
    def cursor(self):
        if self.raises:
            raise self.raises
        return self.cursor_obj
    
    def commit(self):
        self.committed = True
    
    def rollback(self):
        self.rolled_back = True
    
    def close(self):
        self.closed = True
        
    def execute(self, query):
        self.executed_transactions.append(query)
        return self.cursor_obj

def test_execute_modification_success():
    """Test successful execution of a modification query."""
    # Mock cursor with rowcount=1 (1 row affected)
    mock_cursor = MockCursor(rowcount=1)
    mock_conn = MockConnection(cursor=mock_cursor)
    
    with patch('app.db.get_db_connection', return_value=mock_conn):
        # Execute a valid UPDATE statement
        query = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
        params = (10, "laptop")
        rows_affected, error = execute_modification(query, params)
        
        # Verify results
        assert rows_affected == 1
        assert error is None
        # Check if parameters were converted to uppercase for item name
        assert mock_cursor.executed_params == (10, "LAPTOP")
        assert mock_conn.committed is True
        assert mock_conn.closed is True

def test_execute_modification_no_rows():
    """Test execution of a modification query that affects no rows."""
    # Mock cursor with rowcount=0 (no rows affected)
    mock_cursor = MockCursor(rowcount=0)
    mock_conn = MockConnection(cursor=mock_cursor)
    
    with patch('app.db.get_db_connection', return_value=mock_conn):
        # Execute a valid UPDATE statement that doesn't match any rows
        query = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
        params = (10, "nonexistent_item")
        rows_affected, error = execute_modification(query, params)
        
        # Verify results
        assert rows_affected == 0
        assert error is None
        # Check if parameters were converted to uppercase for item name
        assert mock_cursor.executed_params == (10, "NONEXISTENT_ITEM")
        assert mock_conn.committed is True
        assert mock_conn.closed is True

def test_execute_modification_db_error():
    """Test handling of database errors during modification."""
    # Mock connection that raises a SQLite error
    mock_conn = MockConnection(raises=sqlite3.Error("Database error"))
    
    with patch('app.db.get_db_connection', return_value=mock_conn):
        # Execute a query that will trigger an error
        query = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
        params = (10, "laptop")
        rows_affected, error = execute_modification(query, params)
        
        # Verify results
        assert rows_affected == 0
        assert "Database error during modification" in error
        assert mock_conn.rolled_back is True
        assert mock_conn.closed is True

def test_execute_modification_non_string_params():
    """Test handling params that don't include string item names."""
    mock_cursor = MockCursor(rowcount=1)
    mock_conn = MockConnection(cursor=mock_cursor)
    
    with patch('app.db.get_db_connection', return_value=mock_conn):
        # Execute with numeric parameters only
        query = "UPDATE inventory SET quantity_available = ? WHERE id = ?"
        params = (10, 1)
        rows_affected, error = execute_modification(query, params)
        
        # Verify results
        assert rows_affected == 1
        assert error is None
        # Parameters should remain unchanged as there's no string to convert
        assert mock_cursor.executed_params == (10, 1)

def test_check_item_exists():
    """Test the item existence check functionality."""
    # Mock execute_query to return results for existing item
    with patch('app.db.execute_query', side_effect=[
        [{"1": 1}],  # First call: item exists
        []           # Second call: item does not exist
    ]):
        # Check for existing item
        assert check_item_exists("laptop") is True
        
        # Check for non-existing item
        assert check_item_exists("nonexistent_item") is False

def test_check_item_exists_error():
    """Test handling of errors during item existence check."""
    # Mock execute_query to raise an error
    with patch('app.db.execute_query', side_effect=ValueError("Database error")):
        # Check should return False on error
        assert check_item_exists("laptop") is False

def test_get_item_quantity():
    """Test retrieving item quantity."""
    # Mock execute_query to return results with quantity
    with patch('app.db.execute_query', side_effect=[
        [{"quantity_available": 10}],  # First call: item with quantity 10
        [],                           # Second call: item not found
    ]):
        # Get quantity for existing item
        assert get_item_quantity("laptop") == 10
        
        # Get quantity for non-existing item (should return 0)
        assert get_item_quantity("nonexistent_item") == 0

def test_get_item_quantity_error():
    """Test handling of errors during quantity retrieval."""
    # Mock execute_query to raise an error
    with patch('app.db.execute_query', side_effect=ValueError("Database error")):
        # Should return 0 on error
        assert get_item_quantity("laptop") == 0 