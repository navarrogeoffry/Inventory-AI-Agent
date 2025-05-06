import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.routes.api import process_query, process_modification, QueryRequest

client = TestClient(app)

@pytest.mark.asyncio
async def test_record_sale_integration():
    """Test the complete flow for recording a sale."""
    # Mock the AI processing to return a record_sale intent
    mock_intent_result = ("record_sale", {
        "item_name": "laptop",
        "quantity": 5,
        "confidence": 0.95
    })
    
    # Mock the database checks and operations
    with patch('app.routes.api.get_modification_intent', return_value=mock_intent_result), \
         patch('app.routes.api.check_item_exists', return_value=True), \
         patch('app.routes.api.get_item_quantity', return_value=10), \
         patch('app.routes.api.validate_sql', return_value=True), \
         patch('app.routes.api.execute_modification', return_value=(1, None)), \
         patch('app.routes.api.execute_query', return_value=[{"quantity_available": 5}]):
        
        # Create a QueryRequest object
        request = QueryRequest(
            natural_language_query="I sold 5 laptops today",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Call the API endpoint directly
        response = await process_query(request)
        
        # Verify the response
        assert response.status == "success"
        assert response.modification_type == "record_sale"
        assert "LAPTOP" in response.explanation
        assert "5" in response.explanation
        assert "Remaining stock: 5" in response.explanation

@pytest.mark.asyncio
async def test_add_stock_integration():
    """Test the complete flow for adding stock."""
    # Mock the AI processing to return an add_stock intent
    mock_intent_result = ("add_stock", {
        "item_name": "keyboard",
        "quantity": 20,
        "confidence": 0.9
    })
    
    # Mock the database checks and operations
    with patch('app.routes.api.get_modification_intent', return_value=mock_intent_result), \
         patch('app.routes.api.check_item_exists', return_value=True), \
         patch('app.routes.api.validate_sql', return_value=True), \
         patch('app.routes.api.execute_modification', return_value=(1, None)), \
         patch('app.routes.api.execute_query', return_value=[{"quantity_available": 50}]):
        
        # Create a QueryRequest object
        request = QueryRequest(
            natural_language_query="We just received 20 new keyboards",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Call the API endpoint directly
        response = await process_query(request)
        
        # Verify the response
        assert response.status == "success"
        assert response.modification_type == "add_stock"
        assert "KEYBOARD" in response.explanation
        assert "20" in response.explanation
        assert "New stock level: 50" in response.explanation

@pytest.mark.asyncio
async def test_record_sale_insufficient_stock():
    """Test handling of insufficient stock during sale recording."""
    # Mock the AI processing to return a record_sale intent
    mock_intent_result = ("record_sale", {
        "item_name": "monitor",
        "quantity": 15,
        "confidence": 0.95
    })
    
    # Mock the database checks to show insufficient stock
    with patch('app.routes.api.get_modification_intent', return_value=mock_intent_result), \
         patch('app.routes.api.check_item_exists', return_value=True), \
         patch('app.routes.api.get_item_quantity', return_value=10):
        
        # Create a QueryRequest object
        request = QueryRequest(
            natural_language_query="I sold 15 monitors today",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Call the API endpoint directly
        response = await process_query(request)
        
        # Verify the response
        assert response.status == "error"
        assert "Cannot record sale" in response.error
        assert "only 10 units" in response.error

@pytest.mark.asyncio
async def test_modification_item_not_found():
    """Test handling of non-existent items during modification."""
    # Mock the AI processing to return an add_stock intent
    mock_intent_result = ("add_stock", {
        "item_name": "nonexistent_item",
        "quantity": 10,
        "confidence": 0.9
    })
    
    # Mock the database check to show item doesn't exist
    with patch('app.routes.api.get_modification_intent', return_value=mock_intent_result), \
         patch('app.routes.api.check_item_exists', return_value=False):
        
        # Create a QueryRequest object
        request = QueryRequest(
            natural_language_query="Add 10 units of nonexistent_item",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Call the API endpoint directly
        response = await process_query(request)
        
        # Verify the response
        assert response.status == "error"
        assert "not found in inventory" in response.error

@pytest.mark.asyncio
async def test_modification_db_error():
    """Test handling of database errors during modification."""
    # Mock the AI processing to return an add_stock intent
    mock_intent_result = ("add_stock", {
        "item_name": "keyboard",
        "quantity": 20,
        "confidence": 0.9
    })
    
    # Mock the database operations to simulate a database error
    with patch('app.routes.api.get_modification_intent', return_value=mock_intent_result), \
         patch('app.routes.api.check_item_exists', return_value=True), \
         patch('app.routes.api.validate_sql', return_value=True), \
         patch('app.routes.api.execute_modification', return_value=(None, "Database error")):
        
        # Create a QueryRequest object
        request = QueryRequest(
            natural_language_query="Add 20 keyboards to inventory",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Call the API endpoint directly
        response = await process_query(request)
        
        # Verify the response
        assert response.status == "error"
        assert "Database error" in response.error

@pytest.mark.asyncio
async def test_process_modification_direct():
    """Test the process_modification function directly."""
    # Set up test parameters
    action_type = "record_sale"
    action_details = {
        "item_name": "laptop",
        "quantity": 5,
        "confidence": 0.95
    }
    natural_query = "I sold 5 laptops"
    session_id = "test_session"
    current_user_message = {"role": "user", "content": natural_query}
    history = []
    
    # Mock the database operations
    with patch('app.routes.api.check_item_exists', return_value=True), \
         patch('app.routes.api.get_item_quantity', return_value=10), \
         patch('app.routes.api.validate_sql', return_value=True), \
         patch('app.routes.api.execute_modification', return_value=(1, None)), \
         patch('app.routes.api.execute_query', return_value=[{"quantity_available": 5}]), \
         patch('app.routes.api.conversation_histories', {}):
        
        # Call the function directly
        response = await process_modification(
            action_type, action_details, natural_query, 
            session_id, current_user_message, history
        )
        
        # Verify the response
        assert response.status == "success"
        assert response.modification_type == "record_sale"
        assert response.modification_details["item_name"] == "LAPTOP"
        assert "LAPTOP" in response.explanation
        assert "Recorded sale of 5 units" in response.explanation 