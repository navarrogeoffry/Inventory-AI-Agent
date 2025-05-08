# app/sql_validator.py
import sqlparse
import logging
import re

logger = logging.getLogger(__name__)

# --- Allowed Schema Elements for Validation (Corrected Table Name: inventory) ---
# Defines the single table and its columns the AI is allowed to query
ALLOWED_TABLES = {
    "inventory": {"id", "item", "unit_cost", "unit_price", "quantity_sold", "quantity_available"}
}
# Defines SQL functions the AI is allowed to use in queries
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "max", "min", "strftime"}
# Defines allowed arithmetic operators for expressions
ALLOWED_OPERATORS = {"+", "-", "*", "/", "%"}

def validate_sql(sql_query: str) -> bool:
    """
    Validates the AI-generated SQL query template using sqlparse.
    Checks for allowed statement type (SELECT/UPDATE), tables ('inventory'), columns, and functions.
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

        # --- 1. Check for single SQL statement ---
        # Ensure only one SQL statement is present to prevent batch attacks
        if len(parsed_list) > 1:
            logger.warning(f"Validation failed: Multiple SQL statements detected.")
            return False
        parsed = parsed_list[0] # Get the first (and only) statement
        
        # Get statement type
        statement_type = parsed.get_type()

        # Support SELECT and UPDATE types
        if statement_type not in ["SELECT", "UPDATE"]:
            logger.warning(f"Validation failed: Unsupported query type: {statement_type}.")
            return False
        
        # --- 2. Extract Tables, Columns, Functions from the parsed query ---
        identifiers = set() # Potential columns or tables used in the query
        functions = set()   # SQL functions used (e.g., COUNT, SUM)
        tables = set()      # Tables explicitly mentioned after FROM/JOIN
        columns = set()     # Columns explicitly used in the query
        expressions = []    # Calculated expressions

        # For SELECT statements, check if it contains our allowed table
        if statement_type == "SELECT":
            sql_lower = sql_query.lower()
            # Simple check for "from inventory"
            if "from inventory" in sql_lower:
                tables.add("inventory")
            
            # Extract column names from SELECT clause
            select_match = re.search(r'select\s+(.*?)\s+from', sql_lower, re.DOTALL)
            if select_match:
                select_columns = select_match.group(1).strip()
                # Handle * wildcard
                if select_columns == '*':
                    pass  # Allow all columns
                else:
                    # Split by commas to get individual columns or expressions
                    col_list = []
                    in_parentheses = 0
                    current_col = ""
                    
                    # Handle expressions with commas inside parentheses
                    for char in select_columns:
                        if char == '(' and in_parentheses == 0:
                            in_parentheses += 1
                            current_col += char
                        elif char == '(' and in_parentheses > 0:
                            in_parentheses += 1
                            current_col += char
                        elif char == ')' and in_parentheses > 0:
                            in_parentheses -= 1
                            current_col += char
                        elif char == ',' and in_parentheses == 0:
                            col_list.append(current_col.strip())
                            current_col = ""
                        else:
                            current_col += char
                    
                    if current_col:
                        col_list.append(current_col.strip())
                    
                    for col in col_list:
                        # Detect and extract aggregate functions for validation
                        function_match = re.search(r'^(\w+)\(', col.lower())
                        if function_match:
                            func_name = function_match.group(1)
                            if func_name in ALLOWED_FUNCTIONS:
                                # This is an aggregate function, add it to functions set
                                functions.add(func_name)
                                
                        # Detect expressions (calculated columns)
                        if '(' in col or any(op in col for op in ALLOWED_OPERATORS):
                            expressions.append(col)
                            # Skip further processing for expressions
                            continue
                        
                        # Handle normal columns
                        # Remove "as alias" if present
                        if ' as ' in col:
                            col = col.split(' as ')[0].strip()
                        
                        # Remove table prefix if present
                        if '.' in col:
                            _, col_name = col.split('.', 1)
                            columns.add(col_name)
                        else:
                            columns.add(col)

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
                if not is_function_param or is_wildcard:
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
                
                # For UPDATE, the table name is right after the UPDATE keyword
                if statement_type == "UPDATE":
                    prev_token, _ = parsed.token_prev(parsed.token_index(token))
                    if prev_token and prev_token.value.upper() == 'UPDATE':
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

        # Validate Tables explicitly identified against the allowed list ('inventory')
        for table in tables:
             if table not in ALLOWED_TABLES: # ALLOWED_TABLES now only contains 'inventory'
                  logger.warning(f"Validation failed: Disallowed table used: {table}")
                  return False
                  
        # For SELECT queries, make sure we found at least one table and it's in our allowed list
        if statement_type == "SELECT" and (not tables or not any(table in ALLOWED_TABLES for table in tables)):
            logger.warning(f"Validation failed: No allowed tables found in query: {tables}")
            return False

        # Validate expressions (calculated columns)
        if statement_type == "SELECT" and expressions:
            if not validate_expressions(expressions):
                return False

        # Validate columns if explicitly extracted
        all_allowed_columns = set().union(*ALLOWED_TABLES.values())
        if columns:
            for col in columns:
                if col not in all_allowed_columns:
                    logger.warning(f"Validation failed: Disallowed column used: {col}")
                    return False

        # Validate other Identifiers (could be columns or tables missed above)
        # Exclude identifiers already validated as columns
        remaining_identifiers = identifiers - columns
        for ident in remaining_identifiers:
            # Check if the identifier is the table name, an allowed column, or an allowed function (used as alias)
            if (ident not in ALLOWED_TABLES and 
                ident not in all_allowed_columns and 
                ident not in ALLOWED_FUNCTIONS and
                ident not in {"as", "total_profit", "profit_per_unit", "total_cost_value", "total_price_value", 
                             "total_value", "avg_price", "avg_cost", "min_price", "max_price", "inventory_value",
                             "count", "total", "average", "minimum", "maximum"}):  # Allow common alias names
                logger.warning(f"Validation failed: Disallowed identifier (table/column/alias) used: {ident}")
                return False
        
        # --- 4. Additional validation for UPDATE statements ---
        if statement_type == "UPDATE":
            # Validate UPDATE structure for inventory table
            return validate_update_statement(sql_query)

        # If all checks pass without returning False
        logger.info("SQL template validation successful.")
        return True

    except Exception as e:
        # Catch any unexpected errors during parsing/validation
        logger.error(f"Error during SQL validation: {e}")
        return False

def validate_expressions(expressions):
    """
    Validates calculated column expressions to ensure they use only allowed columns and operations.
    """
    all_allowed_columns = set().union(*ALLOWED_TABLES.values())
    
    for expr in expressions:
        # Strip 'as alias' part if present
        if " as " in expr.lower():
            expr = expr.split(" as ", 1)[0].strip()
            
        # Extract all identifiers from the expression
        # Simplistic approach: split by operators, strip whitespace, and check each part
        parts = re.split(r'[\s\(\)\+\-\*\/\%\,]', expr)
        parts = [p.strip() for p in parts if p.strip()]
        
        # Check each part is a valid column or number
        for part in parts:
            # Skip empty parts or numbers
            if not part or part.replace('.', '', 1).isdigit():
                continue
                
            # Check if this part is an allowed column or SQL function
            if part.lower() not in all_allowed_columns and part.lower() not in ALLOWED_FUNCTIONS:
                logger.warning(f"Validation failed: Expression contains disallowed column or value: {part}")
                return False
    
    # Check for unsafe SQL syntax in expressions
    unsafe_patterns = [
        r'\bcase\b', r'\bwhen\b', r'\bthen\b', r'\belse\b', r'\bend\b',  # CASE statements
        r'\bselect\b', r'\bfrom\b',  # Subqueries
        r'\bunion\b', r'\bexcept\b', r'\bintersect\b',  # Set operations
        r'\b(in|not\s+in)\b\s*\(',  # IN clauses
        r'\bexists\b',  # EXISTS
        r'\bcreate\b', r'\bdrop\b', r'\balter\b',  # DDL
        r'\bdelete\b', r'\binsert\b',  # DML
        r'\;',  # Multiple statements
    ]
    
    for expr in expressions:
        for pattern in unsafe_patterns:
            if re.search(pattern, expr.lower()):
                logger.warning(f"Validation failed: Expression contains unsafe SQL pattern: {pattern}")
                return False
    
    return True

def validate_update_statement(sql_query: str) -> bool:
    """
    Validates UPDATE statements for the inventory table.
    Ensures they follow the expected patterns for:
    - Recording sales (updating quantity_sold and quantity_available)
    - Adding stock (updating quantity_available)
    
    Only allows updates to specific columns via WHERE clause with item name or id.
    """
    # Convert to lowercase for case-insensitive matching
    sql_lower = sql_query.lower()
    
    logger.info(f"Validating UPDATE statement: {sql_query}")
    
    # Only allow updates to the inventory table - using regex pattern to handle whitespace
    if not re.search(r'^\s*update\s+inventory\b', sql_lower):
        logger.warning("Validation failed: UPDATE must target the inventory table.")
        return False
    
    # Check for WHERE clause - required for safety
    if 'where' not in sql_lower:
        logger.warning("Validation failed: UPDATE must include a WHERE clause for safety.")
        return False
    
    # Ensure WHERE clause filters by item name or id
    where_clause_pattern = r'where\s+(item\s*=\s*\?|id\s*=\s*\?)'
    where_match = re.search(where_clause_pattern, sql_lower)
    if not where_match:
        logger.warning(f"Validation failed: UPDATE must filter by item name or id. Found: {sql_lower}")
        return False
    else:
        logger.info(f"WHERE clause validation passed: {where_match.group(0)}")
    
    # Check for SET clause - what's being updated
    # Using re.DOTALL flag to make '.' match newlines as well
    set_clause = re.search(r'set\s+(.*?)\s+where', sql_lower, re.DOTALL)
    if not set_clause:
        logger.warning("Validation failed: Cannot extract SET clause from UPDATE.")
        return False
    
    set_columns = set_clause.group(1).strip()
    logger.info(f"Extracted SET clause: '{set_columns}'")
    
    # Define patterns for allowed column updates - handling multi-line with commas
    record_sale_pattern = r'(quantity_sold\s*=\s*quantity_sold\s*\+\s*\?|quantity_available\s*=\s*quantity_available\s*-\s*\?)'
    add_stock_pattern = r'quantity_available\s*=\s*quantity_available\s*\+\s*\?'
    
    # For record sale, need to validate that both updates are present
    if ',' in set_columns or '\n' in set_columns:
        # This is likely a multi-column update (record sale)
        valid_record_sale = (
            re.search(r'quantity_sold\s*=\s*quantity_sold\s*\+\s*\?', set_columns) is not None and
            re.search(r'quantity_available\s*=\s*quantity_available\s*-\s*\?', set_columns) is not None
        )
        valid_add_stock = re.search(add_stock_pattern, set_columns) is not None
    else:
        # Single column update
        valid_record_sale = re.search(record_sale_pattern, set_columns) is not None
        valid_add_stock = re.search(add_stock_pattern, set_columns) is not None
    
    logger.info(f"Pattern matching results - record_sale: {valid_record_sale}, add_stock: {valid_add_stock}")
    
    if not (valid_record_sale or valid_add_stock):
        logger.warning(f"Validation failed: SET clause doesn't match allowed update patterns: {set_columns}")
        return False
    
    logger.info("UPDATE statement validation successful.")
    return True
