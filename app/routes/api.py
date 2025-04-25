# app/routes/api.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
import os
from app.db import execute_query # Import the execution function

# === OpenAI Integration ===
from openai import AsyncOpenAI, OpenAIError
import sqlparse # For SQL validation
import json # For parsing AI response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- OpenAI Client Initialization ---
try:
    # Reads API key from OPENAI_API_KEY environment variable automatically
    openai_client = AsyncOpenAI()
    logger.info("OpenAI client initialized successfully.")
except OpenAIError as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    openai_client = None # Handle potential endpoint failures later

# --- Database Schema Definition ---
# Define the relevant parts of your schema clearly for the AI
DB_SCHEMA = """
Tables:
1. items: Stores information about inventory items.
   Columns:
   - id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for the item.
   - item (TEXT UNIQUE NOT NULL): The name of the item.
   - unit_cost (REAL): The cost price of one unit of the item.
   - unit_price (REAL): The selling price of one unit of the item.
   - quantity_sold (INTEGER DEFAULT 0): The total number of units sold historically.
   - quantity_available (INTEGER DEFAULT 0): The current number of units in stock.

2. transactions: Records stock movements (in or out).
   Columns:
   - id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for the transaction.
   - item_id (INTEGER NOT NULL): Foreign key referencing items.id.
   - type (TEXT NOT NULL): Type of transaction, either 'IN' (stock increase) or 'OUT' (stock decrease/sale).
   - qty (INTEGER NOT NULL): The number of units involved in the transaction.
   - tx_date (DATETIME DEFAULT CURRENT_TIMESTAMP): The date and time of the transaction.
   - notes (TEXT): Optional notes about the transaction.

3. locations: Stores information about warehouse or storage locations.
   Columns:
   - id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for the location.
   - name (TEXT UNIQUE NOT NULL): The name of the location (e.g., 'Warehouse A', 'Shelf 3B').

Relationships:
- transactions.item_id relates to items.id.

SQL Dialect: SQLite
"""

# --- Allowed Schema Elements for Validation ---
# Defines tables and columns the AI is allowed to query
ALLOWED_TABLES = {
    "items": {"id", "item", "unit_cost", "unit_price", "quantity_sold", "quantity_available"},
    "transactions": {"id", "item_id", "type", "qty", "tx_date", "notes"},
    "locations": {"id", "name"}
}
# Defines SQL functions the AI is allowed to use
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "max", "min", "strftime"}


# --- SQL Validation Function ---
def validate_sql(sql_query: str) -> bool:
    """
    Validates the AI-generated SQL query template using sqlparse.
    Checks for allowed statement type (SELECT), tables, columns, and functions.
    """
    if not sql_query:
        logger.warning("Validation failed: Empty SQL query.")
        return False

    try:
        # Parse the SQL query string
        parsed_list = sqlparse.parse(sql_query)
        if not parsed_list:
            logger.warning("Validation failed: Could not parse SQL.")
            return False

        # --- 1. Check for single SELECT statement ---
        # Ensure only one SQL statement is present
        if len(parsed_list) > 1:
            logger.warning(f"Validation failed: Multiple SQL statements detected.")
            return False
        parsed = parsed_list[0] # Get the first (and only) statement

        # Ensure the statement type is SELECT
        if parsed.get_type() != 'SELECT':
            logger.warning(f"Validation failed: Query type is not SELECT ({parsed.get_type()}).")
            return False

        # --- 2. Extract Tables, Columns, Functions from the parsed query ---
        identifiers = set() # Potential columns or tables
        functions = set()   # SQL functions used (e.g., COUNT, SUM)
        tables = set()      # Tables explicitly mentioned after FROM/JOIN

        # Iterate through all tokens in the flattened statement
        for token in parsed.flatten():
            # Extract identifiers (potential columns or table names)
            if isinstance(token, sqlparse.sql.Identifier):
                parent = token.parent
                # Check if the identifier is part of a function call (e.g., the 'id' in COUNT(id))
                is_function_param = isinstance(parent, sqlparse.sql.Function)
                # Check if it's a wildcard within a function (e.g., the '*' in COUNT(*))
                is_wildcard = is_function_param and token.value == '*'

                # Store the identifier name (lowercase)
                # Only add if not a direct function param unless it's a wildcard
                if not is_function_param or is_wildcard :
                     ident_name = token.get_real_name().lower()
                     # Exclude '*' used in COUNT(*) etc directly here
                     if ident_name != '*':
                         identifiers.add(ident_name)

                # Try to identify table names (often follows FROM or JOIN keywords)
                # Look at the previous non-whitespace token
                prev_token, _ = parsed.token_prev(parsed.token_index(token))
                if prev_token and prev_token.ttype == sqlparse.tokens.Keyword and prev_token.value.upper() in ['FROM', 'JOIN']:
                     # Assume the identifier following FROM/JOIN is a table name
                     tables.add(token.get_real_name().lower())

            # Extract function names (e.g., COUNT, SUM)
            elif isinstance(token, sqlparse.sql.Function):
                functions.add(token.get_name().lower())

        # --- 3. Validate against Allowed Schema Elements ---
        # Validate Functions used
        for func in functions:
            if func not in ALLOWED_FUNCTIONS:
                logger.warning(f"Validation failed: Disallowed function used: {func}")
                return False

        # Validate Tables explicitly identified after FROM/JOIN
        for table in tables:
             if table not in ALLOWED_TABLES:
                  logger.warning(f"Validation failed: Disallowed table used: {table}")
                  return False

        # Validate other Identifiers (could be columns or tables missed above)
        # Combine all allowed column names from all allowed tables
        all_allowed_columns = set().union(*ALLOWED_TABLES.values())
        for ident in identifiers:
            # Check if the identifier is a known table or a known column
            if ident not in ALLOWED_TABLES and ident not in all_allowed_columns:
                logger.warning(f"Validation failed: Disallowed identifier (table/column) used: {ident}")
                return False

        # If all checks pass
        logger.info("SQL template validation successful.")
        return True

    except Exception as e:
        # Catch any unexpected errors during parsing/validation
        logger.error(f"Error during SQL validation: {e}")
        return False


# --- OpenAI Call Function (Updated for Parameterized Queries) ---
async def get_sql_from_openai(natural_query: str) -> tuple[str | None, list | None]:
    """
    Sends the natural language query to OpenAI.
    Expects a JSON response containing 'sql' (template) and 'params' (list).
    Returns (sql_template, params_list) or (None, None) on failure.
    """
    if not openai_client:
        logger.error("OpenAI client is not initialized. Cannot process query.")
        return None, None

    # === UPDATED PROMPT ===
    # Instructs the AI on its role, the desired JSON output format, the schema, and constraints.
    system_prompt = f"""
You are an AI assistant that translates natural language requests into parameterized SQL queries
for a specific inventory database using SQLite syntax.

Your goal is to generate a JSON object containing two keys:
1. "sql": A SINGLE, executable SQLite SQL query template using "?" as placeholders for values.
2. "params": A JSON list of the parameters corresponding to the "?" placeholders in the SQL query.

Only output the JSON object and nothing else. Do not include explanations or markdown formatting outside the JSON.

Example Request: "Show me items named Super Widget that cost more than 50"
Example Response:
```json
{{
  "sql": "SELECT * FROM items WHERE item = ? AND unit_cost > ?",
  "params": ["Super Widget", 50.0]
}}
```

Database Schema:
{DB_SCHEMA}

Constraints:
- ONLY generate SELECT queries for now.
- Ensure the query template is valid SQLite syntax.
- Ensure the 'params' list matches the number and order of '?' placeholders.
- Query ONLY the tables and columns listed in the schema.
- If the request is ambiguous or requires information not present in the schema, respond with:
  ```json
  {{
    "sql": "QUERY_UNABLE_TO_GENERATE",
    "params": []
  }}
  ```
- If the request seems potentially harmful or unrelated to inventory, respond with:
  ```json
  {{
    "sql": "QUERY_UNSAFE",
    "params": []
  }}
  ```
- Prioritize safety and correctness. Do not guess table or column names.
"""

    try:
        logger.info(f"Sending query to OpenAI for parameterized SQL: '{natural_query}'")
        # Call the OpenAI API asynchronously
        response = await openai_client.chat.completions.create(
            model="gpt-4o", # Specify the desired OpenAI model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": natural_query}
            ],
            temperature=0.1, # Lower temperature for more deterministic, structured output
            max_tokens=400, # Max length of the response
            n=1, # Request only one completion
            stop=None, # Let the model decide when to stop
            # Instruct the model to return a JSON object
            response_format={"type": "json_object"}
        )
        # Extract the response content
        response_content = response.choices[0].message.content.strip()
        logger.info(f"Received JSON response from OpenAI: '{response_content}'")

        # Parse the JSON response string
        try:
            data = json.loads(response_content)
            sql_template = data.get("sql")
            params_list = data.get("params")

            # Basic validation of the received JSON structure
            if not isinstance(sql_template, str) or not isinstance(params_list, list):
                raise ValueError("Invalid JSON structure received from AI (missing/wrong types).")

            # Check for explicit refusals from the AI
            if sql_template in ["QUERY_UNABLE_TO_GENERATE", "QUERY_UNSAFE"]:
                logger.warning(f"OpenAI indicated query cannot/should not be generated: {sql_template}")
                return None, None # Indicate failure

            # Basic check: Ensure parameter count matches placeholder count
            if sql_template.count('?') != len(params_list):
                 logger.error(f"Mismatch between placeholders count ({sql_template.count('?')}) and params count ({len(params_list)}) from AI.")
                 raise ValueError("AI response parameter count mismatch.")

            # Remove trailing semicolon from SQL template if present
            if sql_template.endswith(';'):
                 sql_template = sql_template[:-1]

            logger.info(f"Successfully parsed SQL template and parameters.")
            # Return the validated SQL template and parameters list
            return sql_template.strip(), params_list

        except json.JSONDecodeError as jde:
            # Handle errors if the AI response is not valid JSON
            logger.error(f"Failed to decode JSON response from OpenAI: {jde} | Response: {response_content}")
            return None, None
        except ValueError as ve:
             # Handle other errors during JSON processing (e.g., structure mismatch)
             logger.error(f"Error processing AI response: {ve} | Response: {response_content}")
             return None, None

    except OpenAIError as e:
        # Handle errors related to the OpenAI API call itself
        logger.error(f"OpenAI API error: {e}")
        return None, None
    except Exception as e:
        # Catch any other unexpected errors during the API call
        logger.error(f"An unexpected error occurred while calling OpenAI: {e}")
        return None, None


# Create the API router instance
router = APIRouter()

# --- Pydantic Models ---
# Define the structure for API request and response bodies
class QueryRequest(BaseModel):
    natural_language_query: str
    user_id: str | None = None # Optional: for potential role-based access later

class QueryResponse(BaseModel):
    status: str
    natural_query: str
    sql_query: str | None = None # The generated SQL (template + params for debugging)
    results: list | None = None # The data returned from the DB
    explanation: str | None = None # AI explanation of the results (Placeholder)
    error: str | None = None # Error message if something went wrong

# --- Health Check Endpoint ---
@router.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# --- Process Query Endpoint (Updated for Parameters) ---
@router.post("/process_query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Processes a natural language query about inventory.
    Connects to AI (expects JSON with SQL template + params), validates SQL template,
    executes query with parameters, and returns results.
    """
    logger.info(f"Received query: '{request.natural_language_query}' from user: {request.user_id}")

    # Initialize variables
    sql_template: str | None = None
    params: list | None = None # Now expecting a list of parameters
    db_results: list | None = None
    status_msg: str = "error" # Default status to error
    error_msg: str | None = None
    ai_explanation: str | None = "AI explanation placeholder." # Placeholder for future feature

    try:
        # ===== Pipeline Steps =====

        # 1. Get SQL Template and Parameters from AI
        sql_template, params = await get_sql_from_openai(request.natural_language_query)

        # Check if AI call was successful and returned both parts
        if not sql_template or params is None:
            raise ValueError("AI failed to generate a valid SQL query template and parameters, or refused.")

        # 2. Validate the generated SQL *Template* using sqlparse logic
        if not validate_sql(sql_template):
            unsafe_sql = sql_template # Keep for logging if needed
            sql_template = None # Don't show unsafe SQL template in response
            params = None # Clear params associated with unsafe template
            raise ValueError(f"Generated SQL template failed validation checks. Blocked for safety.")

        # 3. Execute the SQL using db.execute_query with parameters
        # Ensure params is a tuple, as required by sqlite3 cursor.execute
        db_results = execute_query(sql_template, tuple(params))
        status_msg = "success" # Update status if execution succeeds

        # 4. TODO: (Optional) Ask AI to explain the results based on the query & results
        #    Example call:
        #    ai_explanation = await call_openai_to_explain(request.natural_language_query, sql_template, params, db_results)
        logger.info("Using placeholder AI explanation.")


    except ValueError as ve:
        # Handle specific ValueErrors raised during processing (AI failure, validation, DB error)
        logger.error(f"Processing error: {ve}")
        error_msg = str(ve)
        # Optionally hide SQL template on ValueErrors too, depending on sensitivity
        # sql_template = None
    except Exception as e:
        # Catch any other unexpected exceptions
        logger.exception("An unexpected error occurred during query processing.") # Log full traceback
        error_msg = f"An unexpected server error occurred: {e}"
        # Ensure potentially problematic SQL/results are not returned on generic errors
        sql_template = None
        db_results = None

    # 5. Format and return the response using the Pydantic model
    response = QueryResponse(
        status=status_msg,
        natural_query=request.natural_language_query,
        # Displaying the template and params might be useful for debugging
        sql_query=f"Template: {sql_template} | Params: {params}" if sql_template else None,
        results=db_results,
        explanation=ai_explanation,
        error=error_msg
    )

    return response
