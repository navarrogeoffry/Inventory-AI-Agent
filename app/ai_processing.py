# app/ai_processing.py
import logging
import json
from typing import List, Dict, Tuple
from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger(__name__)

# --- OpenAI Client Initialization ---
# Initialize client here, as this is where it's used.
# Assumes OPENAI_API_KEY environment variable is set.
try:
    openai_client = AsyncOpenAI()
    logger.info("OpenAI client initialized successfully in ai_processing module.")
except OpenAIError as e:
    logger.error(f"Failed to initialize OpenAI client in ai_processing: {e}")
    openai_client = None
except Exception as e:
    logger.error(f"Non-OpenAI error during client initialization in ai_processing: {e}")
    openai_client = None


# --- Database Schema Definition (Corrected Table Name: inventory) ---
# Keep schema definition close to where it's used in prompts
DB_SCHEMA = """
Table: inventory
Description: Stores information about inventory items.
Columns:
- id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier.
- item (TEXT UNIQUE NOT NULL): Name of the item.
- unit_cost (REAL): Cost price per unit.
- unit_price (REAL): Selling price per unit.
- quantity_sold (INTEGER DEFAULT 0): Total units sold.
- quantity_available (INTEGER DEFAULT 0): Current units in stock.
SQL Dialect: SQLite
"""

# --- OpenAI Call Function (SQL + Chart Info + History) ---
async def get_sql_and_chart_info(
    natural_query: str,
    history: List[Dict[str, str]]
) -> Tuple[str | None, list | None, str | None, str | None, str | None, str | None]:
    """
    Sends the natural language query AND conversation history to OpenAI.
    Expects JSON response with 'sql', 'params', 'response_type', 'chart_type', 'x_column', 'y_column'.
    Returns tuple or (None * 6) on failure.
    """
    if not openai_client:
        logger.error("OpenAI client is not available. Cannot process query.")
        return (None,) * 6 # Return tuple of Nones

    # System prompt defining the task and expected JSON output
    system_prompt = f"""
You are an AI assistant that translates natural language requests into parameterized SQL queries
for an inventory database (SQLite). You understand conversation history. You also determine
if the user wants data or a chart, and suggest columns for charting.

Your goal is to generate a JSON object containing these keys:
1. "sql": A SINGLE, executable SQLite SQL query template using "?" placeholders.
2. "params": A JSON list of the parameters for the "?" placeholders.
3. "response_type": String, either "data" or "chart".
4. "chart_type": If "response_type" is "chart", specify chart type (e.g., "bar", "pie", "line", "scatter"). Null otherwise. Use "bar" as default if type not specified.
5. "x_column": If "response_type" is "chart", suggest the column name from the SQL result for X-axis/labels. Null otherwise.
6. "y_column": If "response_type" is "chart", suggest the column name from the SQL result for Y-axis/values. Null otherwise.

Output ONLY the JSON object. Do not include explanations or markdown.

Database Schema:
{DB_SCHEMA}

Constraints: SELECT only, valid SQLite, params match '?', query only 'inventory' table columns, suggest appropriate chart columns. Refuse if ambiguous ("QUERY_UNABLE_TO_GENERATE") or harmful ("QUERY_UNSAFE"). Default response_type to "data".
"""
    # Prepare messages list including history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history) # Add past conversation turns
    messages.append({"role": "user", "content": natural_query}) # Add current query

    try:
        logger.info(f"Sending query with history ({len(history)} turns) to OpenAI...")
        response = await openai_client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.1, max_tokens=550, n=1, stop=None, response_format={"type": "json_object"}
        )
        response_content = response.choices[0].message.content.strip()
        logger.info(f"Received JSON response from OpenAI: '{response_content}'")

        # Parse the JSON response
        try:
            data = json.loads(response_content)
            sql_template = data.get("sql")
            params_list = data.get("params")
            response_type = data.get("response_type", "data")
            chart_type = data.get("chart_type")
            x_column = data.get("x_column")
            y_column = data.get("y_column")

            # Validate structure
            if not isinstance(sql_template, str) or not isinstance(params_list, list):
                raise ValueError("Invalid JSON structure (sql/params).")
            if response_type not in ["data", "chart"]:
                 logger.warning(f"Received invalid response_type '{response_type}', defaulting to 'data'.")
                 response_type = "data"

            # Handle chart defaults and nulls
            allowed_chart_types = {"bar", "pie", "line", "scatter"}
            if response_type == "data":
                chart_type = None; x_column = None; y_column = None
            else: # response_type == "chart"
                if chart_type not in allowed_chart_types:
                    chart_type = "bar" # Default if invalid/missing

            # Check for refusals
            if sql_template in ["QUERY_UNABLE_TO_GENERATE", "QUERY_UNSAFE"]:
                logger.warning(f"OpenAI refused: {sql_template}")
                # Return None for SQL but keep refusal message for logging/history
                return sql_template, [], response_type, chart_type, x_column, y_column

            # Check parameter count
            if sql_template.count('?') != len(params_list):
                 raise ValueError("AI response parameter count mismatch.")

            # Clean SQL template
            if sql_template.endswith(';'):
                 sql_template = sql_template[:-1]

            logger.info(f"Parsed AI response: type='{response_type}', chart='{chart_type}', x='{x_column}', y='{y_column}'")
            return sql_template.strip(), params_list, response_type, chart_type, x_column, y_column

        except json.JSONDecodeError as jde:
            logger.error(f"Failed JSON decode: {jde} | Response: {response_content}")
            return (None,) * 6
        except ValueError as ve:
             logger.error(f"Error processing AI response: {ve} | Response: {response_content}")
             return (None,) * 6

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return (None,) * 6
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI: {e}")
        return (None,) * 6


# --- OpenAI Call Function (Generate Explanation + History) ---
async def get_ai_explanation(
    natural_query: str,
    sql_query: str | None,
    results: list | None,
    history: List[Dict[str, str]]
) -> str:
    """
    Asks OpenAI to generate a natural language explanation of the query results,
    considering conversation history.
    """
    if not openai_client:
        logger.error("OpenAI client is not available. Cannot generate explanation.")
        return "Explanation failed: AI client not available."
    if results is None: # Don't explain if query failed
        return "No results available to explain."
    if not results: # Explain empty results
        return "The query returned no results."

    max_results_for_explanation = 10
    results_preview = results[:max_results_for_explanation]
    results_omitted = len(results) > max_results_for_explanation

    system_prompt = """
You are an AI assistant explaining database query results to a non-technical user,
considering the previous conversation context. Based on the user's original question,
the SQL query run, the results, and the conversation history, provide a concise,
easy-to-understand summary (1-3 sentences). Focus on answering the user's question directly.
Do not mention the SQL query unless necessary. If the results list is empty, state that clearly.
"""
    explanation_context = f"""
User's current question: "{natural_query}"
SQL query run: "{sql_query if sql_query else 'N/A'}"
Results obtained (first {len(results_preview)} rows):
{json.dumps(results_preview, indent=2)}
"""
    if results_omitted:
        explanation_context += f"\n(... {len(results) - max_results_for_explanation} more rows omitted)"

    # Prepare messages list including history and current context
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history) # Add past conversation turns
    messages.append({"role": "user", "content": explanation_context}) # Add current context

    try:
        logger.info("Sending request to OpenAI for explanation with history.")
        response = await openai_client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.5, max_tokens=150, n=1, stop=None
        )
        explanation = response.choices[0].message.content.strip()
        logger.info(f"Received explanation from OpenAI: '{explanation}'")
        return explanation
    except OpenAIError as e:
        logger.error(f"OpenAI API error during explanation: {e}")
        return "Failed to generate explanation (API error)."
    except Exception as e:
        logger.error(f"Unexpected error during explanation: {e}")
        return "Failed to generate explanation (unexpected error)."

# --- OpenAI Call Function (Data Modification Intent Recognition) ---
async def get_modification_intent(
    natural_query: str,
    history: List[Dict[str, str]]
) -> Tuple[str | None, dict | None]:
    """
    Analyzes the natural language query to determine if it's a data modification request,
    and extracts relevant details for actions like "Record Sale" or "Add Stock".
    
    Returns a tuple of (action_type, action_details) where:
    - action_type: One of "record_sale", "add_stock", or None (if not a modification intent)
    - action_details: Dictionary with parameters needed for the modification, or None
    """
    if not openai_client:
        logger.error("OpenAI client is not available. Cannot process modification intent.")
        return None, None

    system_prompt = f"""
You are an AI assistant that identifies inventory modification requests and extracts specific details.
Focus on recognizing two types of modifications:
1. "Record Sale" - when a user wants to record that they sold some items
2. "Add Stock" - when a user wants to add new inventory

Your goal is to generate a JSON object with these keys:
1. "action_type": Either "record_sale", "add_stock", or "not_modification" (if query isn't a modification request)
2. "item_name": The name of the inventory item being modified
3. "quantity": The quantity being sold or added
4. "confidence": A number from 0.0-1.0 indicating your confidence in this interpretation

Database Schema:
{DB_SCHEMA}

Example 1: "I sold 5 laptops today"
Response: {{"action_type": "record_sale", "item_name": "laptops", "quantity": 5, "confidence": 0.95}}

Example 2: "We just received 20 new keyboards"
Response: {{"action_type": "add_stock", "item_name": "keyboards", "quantity": 20, "confidence": 0.9}}

Example 3: "How many monitors do we have in stock?"
Response: {{"action_type": "not_modification", "item_name": null, "quantity": null, "confidence": 0.95}}

Output ONLY the JSON object. Do not include explanations or markdown.
"""
    # Prepare messages list including history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history) # Add past conversation turns
    messages.append({"role": "user", "content": natural_query}) # Add current query

    try:
        logger.info(f"Sending modification intent analysis request to OpenAI...")
        response = await openai_client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.1, max_tokens=250, n=1, stop=None, response_format={"type": "json_object"}
        )
        response_content = response.choices[0].message.content.strip()
        logger.info(f"Received modification intent JSON from OpenAI: '{response_content}'")

        # Parse the JSON response
        try:
            data = json.loads(response_content)
            action_type = data.get("action_type")
            item_name = data.get("item_name")
            quantity = data.get("quantity")
            confidence = data.get("confidence", 0.0)

            # If not a modification or low confidence, return None
            if action_type == "not_modification" or confidence < 0.7:
                logger.info(f"Not a modification intent or low confidence: {action_type}, confidence: {confidence}")
                return None, None

            # Validate required fields for modification intents
            if action_type in ["record_sale", "add_stock"]:
                if not item_name or not isinstance(quantity, (int, float)) or quantity <= 0:
                    logger.warning(f"Invalid modification details: item_name={item_name}, quantity={quantity}")
                    return None, None
                
                # Create action details dictionary
                action_details = {
                    "item_name": item_name,
                    "quantity": int(quantity),  # Ensure quantity is an integer
                    "confidence": confidence
                }
                
                logger.info(f"Identified modification intent: {action_type} with details: {action_details}")
                return action_type, action_details
            
            # If action_type is not recognized
            logger.warning(f"Unrecognized action_type: {action_type}")
            return None, None

        except json.JSONDecodeError as jde:
            logger.error(f"Failed JSON decode for modification intent: {jde} | Response: {response_content}")
            return None, None
        except Exception as ve:
            logger.error(f"Error processing modification intent response: {ve} | Response: {response_content}")
            return None, None

    except OpenAIError as e:
        logger.error(f"OpenAI API error during modification intent analysis: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error during modification intent analysis: {e}")
        return None, None

