# app/sql_validator.py
import sqlparse
import logging

logger = logging.getLogger(__name__)

# --- Allowed Schema Elements for Validation (Corrected Table Name: inventory) ---
# Defines the single table and its columns the AI is allowed to query
ALLOWED_TABLES = {
    "inventory": {"id", "item", "unit_cost", "unit_price", "quantity_sold", "quantity_available"}
}
# Defines SQL functions the AI is allowed to use in queries
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "max", "min", "strftime"}

def validate_sql(sql_query: str) -> bool:
    """
    Validates the AI-generated SQL query template using sqlparse.
    Checks for allowed statement type (SELECT), tables ('inventory'), columns, and functions.
    Prevents execution of potentially harmful or disallowed SQL structures.
    """
    if not sql_query:
        logger.warning("Validation failed: Empty SQL query.")
        return False

    try:
        # Parse the SQL query string into statement objects
        parsed_list = sqlparse.parse(sql_query)
        if not parsed_list:
            logger.warning("Validation failed: Could not parse SQL.")
            return False

        # --- 1. Check for single SELECT statement ---
        # Ensure only one SQL statement is present to prevent batch attacks
        if len(parsed_list) > 1:
            logger.warning(f"Validation failed: Multiple SQL statements detected.")
            return False
        parsed = parsed_list[0] # Get the first (and only) statement

        # Ensure the statement type is SELECT (currently only allowing reads)
        if parsed.get_type() != 'SELECT':
            logger.warning(f"Validation failed: Query type is not SELECT ({parsed.get_type()}).")
            return False

        # --- 2. Extract Tables, Columns, Functions from the parsed query ---
        identifiers = set() # Potential columns or tables used in the query
        functions = set()   # SQL functions used (e.g., COUNT, SUM)
        tables = set()      # Tables explicitly mentioned after FROM/JOIN

        # Iterate through all tokens (keywords, identifiers, etc.) in the statement
        for token in parsed.flatten():
            # Extract identifiers (potential columns or table names)
            if isinstance(token, sqlparse.sql.Identifier):
                parent = token.parent # Get the parent token (e.g., Function if it's COUNT(id))
                # Check if the identifier is part of a function call
                is_function_param = isinstance(parent, sqlparse.sql.Function)
                # Check if it's a wildcard within a function (e.g., the '*' in COUNT(*))
                is_wildcard = is_function_param and token.value == '*'

                # Store the identifier name (lowercase)
                # Only add if not a direct function param unless it's a wildcard
                if not is_function_param or is_wildcard :
                     ident_name = token.get_real_name().lower()
                     # Exclude '*' used in COUNT(*) etc directly here, as it's handled by function check
                     if ident_name != '*':
                         identifiers.add(ident_name)

                # Try to identify table names (often follows FROM or JOIN keywords)
                # Look at the previous non-whitespace token
                prev_token, _ = parsed.token_prev(parsed.token_index(token))
                if prev_token and prev_token.ttype == sqlparse.tokens.Keyword and prev_token.value.upper() in ['FROM', 'JOIN']:
                     # Assume the identifier following FROM/JOIN is a table name
                     # This should now correctly identify 'inventory' if used
                     tables.add(token.get_real_name().lower())

            # Extract function names (e.g., COUNT, SUM)
            elif isinstance(token, sqlparse.sql.Function):
                functions.add(token.get_name().lower())

        # --- 3. Validate against Allowed Schema Elements ---
        # Validate Functions used against the allowed list
        for func in functions:
            if func not in ALLOWED_FUNCTIONS:
                logger.warning(f"Validation failed: Disallowed function used: {func}")
                return False

        # Validate Tables explicitly identified after FROM/JOIN against the allowed list ('inventory')
        for table in tables:
             if table not in ALLOWED_TABLES: # ALLOWED_TABLES now only contains 'inventory'
                  logger.warning(f"Validation failed: Disallowed table used: {table}")
                  return False

        # Validate other Identifiers (could be columns or tables missed above)
        # Combine all allowed column names from the 'inventory' table into a single set
        all_allowed_columns = set().union(*ALLOWED_TABLES.values()) # Gets columns from 'inventory'
        for ident in identifiers:
            # Check if the identifier is the table name, an allowed column, or an allowed function (used as alias)
            if ident not in ALLOWED_TABLES and ident not in all_allowed_columns and ident not in ALLOWED_FUNCTIONS:
                logger.warning(f"Validation failed: Disallowed identifier (table/column/alias) used: {ident}")
                return False

        # If all checks pass without returning False
        logger.info("SQL template validation successful.")
        return True

    except Exception as e:
        # Catch any unexpected errors during parsing/validation
        logger.error(f"Error during SQL validation: {e}")
        return False
