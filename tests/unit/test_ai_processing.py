import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ai_processing import get_modification_intent

@pytest.mark.asyncio
async def test_get_modification_intent_record_sale():
    """Test that the function correctly identifies a record sale intent."""
    # Mock the OpenAI client response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "action_type": "record_sale",
                    "item_name": "laptop",
                    "quantity": 5,
                    "confidence": 0.95
                })
            )
        )
    ]
    
    # Mock the OpenAI client
    with patch('app.ai_processing.openai_client', new=AsyncMock()) as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        
        action_type, action_details = await get_modification_intent(
            "I sold 5 laptops today",
            []  # Empty history
        )
        
        # Verify the function correctly processed the OpenAI response
        assert action_type == "record_sale"
        assert action_details["item_name"] == "laptop"
        assert action_details["quantity"] == 5
        assert action_details["confidence"] == 0.95
        
        # Verify the OpenAI client was called with expected parameters
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_modification_intent_add_stock():
    """Test that the function correctly identifies an add stock intent."""
    # Mock the OpenAI client response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "action_type": "add_stock",
                    "item_name": "keyboard",
                    "quantity": 20,
                    "confidence": 0.9
                })
            )
        )
    ]
    
    # Mock the OpenAI client
    with patch('app.ai_processing.openai_client', new=AsyncMock()) as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        
        action_type, action_details = await get_modification_intent(
            "We just received 20 new keyboards",
            []  # Empty history
        )
        
        # Verify the function correctly processed the OpenAI response
        assert action_type == "add_stock"
        assert action_details["item_name"] == "keyboard"
        assert action_details["quantity"] == 20
        assert action_details["confidence"] == 0.9
        
        # Verify the OpenAI client was called with expected parameters
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_modification_intent_not_modification():
    """Test that the function correctly identifies a non-modification intent."""
    # Mock the OpenAI client response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "action_type": "not_modification",
                    "item_name": None,
                    "quantity": None,
                    "confidence": 0.95
                })
            )
        )
    ]
    
    # Mock the OpenAI client
    with patch('app.ai_processing.openai_client', new=AsyncMock()) as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        
        action_type, action_details = await get_modification_intent(
            "How many monitors do we have in stock?",
            []  # Empty history
        )
        
        # Verify the function returns None for non-modification intents
        assert action_type is None
        assert action_details is None
        
        # Verify the OpenAI client was called with expected parameters
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_modification_intent_low_confidence():
    """Test that the function handles low confidence scores correctly."""
    # Mock the OpenAI client response with low confidence
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "action_type": "record_sale",
                    "item_name": "laptop",
                    "quantity": 5,
                    "confidence": 0.5  # Low confidence score
                })
            )
        )
    ]
    
    # Mock the OpenAI client
    with patch('app.ai_processing.openai_client', new=AsyncMock()) as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        
        action_type, action_details = await get_modification_intent(
            "I think I might have sold some laptops today",
            []  # Empty history
        )
        
        # Verify the function returns None for low confidence scores
        assert action_type is None
        assert action_details is None
        
        # Verify the OpenAI client was called with expected parameters
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_modification_intent_invalid_details():
    """Test that the function handles invalid details correctly."""
    # Mock the OpenAI client response with invalid quantity
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "action_type": "record_sale",
                    "item_name": "laptop",
                    "quantity": -5,  # Invalid negative quantity
                    "confidence": 0.95
                })
            )
        )
    ]
    
    # Mock the OpenAI client
    with patch('app.ai_processing.openai_client', new=AsyncMock()) as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        
        action_type, action_details = await get_modification_intent(
            "I returned 5 laptops today",
            []  # Empty history
        )
        
        # Verify the function returns None for invalid details
        assert action_type is None
        assert action_details is None
        
        # Verify the OpenAI client was called with expected parameters
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_modification_intent_openai_error():
    """Test that the function handles OpenAI errors correctly."""
    # Mock the OpenAI client to raise an exception
    with patch('app.ai_processing.openai_client', new=AsyncMock()) as mock_client:
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        action_type, action_details = await get_modification_intent(
            "I sold 5 laptops today",
            []  # Empty history
        )
        
        # Verify the function returns None when OpenAI raises an error
        assert action_type is None
        assert action_details is None
        
        # Verify the OpenAI client was called with expected parameters
        mock_client.chat.completions.create.assert_called_once() 