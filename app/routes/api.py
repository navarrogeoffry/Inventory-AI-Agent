# app/routes/api.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging
import os
import io
import uuid
from typing import List, Dict, Any, Tuple

# Import functions from refactored modules
from app.db import execute_query, execute_modification, check_item_exists, get_item_quantity
from app.plotting import create_bar_chart, create_pie_chart, create_line_chart, create_scatter_plot
from app.sql_validator import validate_sql # Import validation function
from app.ai_processing import get_sql_and_chart_info, get_ai_explanation, get_modification_intent # Import AI functions

logger = logging.getLogger(__name__)

# --- In-Memory Conversation History Store ---
# WARNING: This is lost on server restart and not suitable for production scaling.
conversation_histories: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 5 # Keep last N user/assistant turns

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    natural_language_query: str
    user_id: str | None = None
    session_id: str | None = None # Optional session ID from client

class QueryResponse(BaseModel):
    status: str # 'success', 'warning', 'error'
    natural_query: str
    sql_query: str | None = None # The generated SQL (template + params for debugging)
    results: list | None = None # The data returned from the DB (for data responses)
    explanation: str | None = None # AI explanation or status message
    error: str | None = None # Error message if status is 'error' or 'warning'
    session_id: str # Always return session ID for client to use next time
    chart_url: str | None = None
    modification_type: str | None = None # Type of modification performed (record_sale, add_stock)
    modification_details: dict | None = None # Details of the modification

# Create the API router instance
router = APIRouter()

@router.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# --- Process Query Endpoint (Using Refactored Modules) ---
@router.post("/process_query")
async def process_query(request: QueryRequest):
    """
    Processes query using refactored components: manages history, calls AI processing,
    validates SQL, executes query, handles plotting, generates explanation.
    Returns JSON data or chart image. Includes session_id.
    """
    logger.info(f"Received query: '{request.natural_language_query}' from user: {request.user_id}, session: {request.session_id}")

# --- Session and History Management ---
    if request.session_id and request.session_id in conversation_histories:
        session_id = request.session_id
        history = conversation_histories[session_id]
        logger.info(f"Using existing session {session_id} with {len(history)} turns.")
    else:
        session_id = request.session_id or str(uuid.uuid4())
        history = []
        conversation_histories[session_id] = history
        logger.info(f"Started new session {session_id}.")

    current_user_message = {"role": "user", "content": request.natural_language_query}
    limited_history = history[-(MAX_HISTORY_TURNS * 2):]


    # --- Initialize variables ---
    sql_template: str | None = None; params: list | None = None; response_type: str | None = "data"; chart_type: str | None = None
    x_col_suggestion: str | None = None; y_col_suggestion: str | None = None; db_results: list | None = None
    status_msg: str | None = None # Initialize status to None
    error_msg: str | None = None; ai_explanation: str | None = None
    assistant_response_content: str | None = None # For history
    modification_type: str | None = None
    modification_details: dict | None = None

    try:
        # 0. Check for data modification intent
        action_type, action_details = await get_modification_intent(
            request.natural_language_query, limited_history
        )
        
        # If this is a modification request
        if action_type in ["record_sale", "add_stock"] and action_details:
            logger.info(f"Detected modification intent: {action_type}")
            return await process_modification(
                action_type, action_details, 
                request.natural_language_query, session_id, 
                current_user_message, limited_history
            )
        
        # 1. Get info from AI (Call refactored function)
        (sql_template, params, response_type, chart_type,
         x_col_suggestion, y_col_suggestion) = await get_sql_and_chart_info(
             request.natural_language_query, limited_history
         )
        # Handle AI refusal/failure
        if sql_template is None: raise ValueError("AI failed to generate valid response.")
        if sql_template in ["QUERY_UNABLE_TO_GENERATE", "QUERY_UNSAFE"]:
            assistant_response_content = f"AI Response: {sql_template}"; status_msg = "error"
            error_msg = f"Query cannot be processed: {sql_template}"; response_type = "data"
        else:
             assistant_response_content = f"SQL: {sql_template}, Params: {params}"

        # 2. Validate SQL Template (Skip if AI refused)
        if status_msg != "error":
            # Call refactored validation function
            if not validate_sql(sql_template):
                assistant_response_content = "SQL validation failed."; raise ValueError("SQL validation failed.")

        # 3. Execute Query (Skip if error already occurred)
        if status_msg != "error":
            logger.info("Attempting database query execution...")
            try:
                db_results = execute_query(sql_template, tuple(params))
                status_msg = "success" # Set status only on success
                logger.info(f"Database query successful. Status set to: {status_msg}. Results count: {len(db_results) if db_results is not None else 'None'}")
            except ValueError as db_ve:
                 logger.error(f"Database execution error caught: {db_ve}")
                 status_msg = "error"; error_msg = str(db_ve)
                 assistant_response_content = error_msg; response_type = "data"
            logger.info(f"After DB execution block: status='{status_msg}', error='{error_msg}'")

        # 4. Decide Response: Chart or Data? (Skip if error occurred)
        if response_type == "chart" and status_msg == "success":
            if not db_results: # Fallback if no data
                logger.warning("Chart requested, but query returned no results.")
                response_type = "data"; status_msg = "warning"; ai_explanation = "No data to plot."
                assistant_response_content = ai_explanation
            else: # Attempt chart generation
                logger.info(f"Attempting chart: '{chart_type}', x_sug='{x_col_suggestion}', y_sug='{y_col_suggestion}'")
                image_buffer: io.BytesIO | None = None; plot_title = f"Chart: {request.natural_language_query}"
                x_col, y_col = x_col_suggestion, y_col_suggestion; actual_columns = list(db_results[0].keys())
                
                #logging debug delete this
                logger.info(f"Original AI columns: x='{x_col_suggestion}', y='{y_col_suggestion}'")
                logger.info(f"Actual fallback columns: x='{x_col}', y='{y_col}'")
                logger.info(f"Available columns: {actual_columns}")
                #end debug logging



                # Column fallback logic...
                if x_col is None or x_col not in actual_columns: x_col = next((k for k in actual_columns if isinstance(db_results[0][k], str)), actual_columns[0])
                if y_col is None or y_col not in actual_columns:
                     y_col_fallback = next((k for k in actual_columns if isinstance(db_results[0][k], (int, float))), None)
                     if y_col_fallback is None: y_col_fallback = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
                     y_col = y_col_fallback if y_col_fallback != x_col else actual_columns[0]
                logger.info(f"Using columns for plot: x='{x_col}', y='{y_col}'")
                # Call plotting function...
                plot_func = None
                if chart_type == "bar": plot_func = create_bar_chart
                elif chart_type == "pie": 
                    def pie_chart_adapter(data, x_col, y_col, title):
                        return create_pie_chart(data, label_col=x_col, value_col=y_col, title=title)
                    plot_func = pie_chart_adapter
                elif chart_type == "line": plot_func = create_line_chart
                elif chart_type == "scatter": plot_func = create_scatter_plot
                if plot_func: image_buffer = plot_func(db_results, x_col=x_col, y_col=y_col, title=plot_title)
                else: error_msg = f"Unknown chart type '{chart_type}'."; response_type = "data"
                # Return image if successful
                
                if image_buffer:
                    logger.info("Saving chart image and returning URL.")

                    # Create a filename using session ID and timestamp
                filename = f"chart_{session_id[:8]}_{uuid.uuid4().hex[:8]}.png"
                file_path = f"static/{filename}"

                # Save image to static directory
                with open(file_path, "wb") as f:
                    f.write(image_buffer.read())
                    logger.info(f"Saved chart to: {file_path}")


                # Append chart message to history
                chart_url = f"/static/{filename}"
                history.append(current_user_message)
                history.append({"role": "assistant", "content": f"Generated a {chart_type} chart.", "chart_url": chart_url})
                conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]

                 # Return chart URL in JSON
                return QueryResponse(
                    status="success",
                    natural_query=request.natural_language_query,
                    sql_query=None,
                    results=None,
                    explanation=None,
                    error=None,
                    session_id=session_id,
                    chart_url=chart_url  #  Add this to QueryResponse model
                )

            # fallback if image_buffer was None
            logger.warning("Plotting function failed.")
            response_type = "data"
            status_msg = "warning"
            error_msg = error_msg or "Failed to generate requested chart."
            ai_explanation = error_msg
            assistant_response_content = ai_explanation

        # 5. If response_type is "data", generate explanation and return JSON
        if response_type == "data":
            # Set status to success if no error/warning occurred
            if status_msg is None: status_msg = "success"

            logger.info(f"Preparing JSON response. Current status='{status_msg}', error='{error_msg}'")
            if status_msg in ["success", "warning"]:
                 # Call refactored explanation function
                 ai_explanation = ai_explanation or await get_ai_explanation(
                     request.natural_language_query, sql_template, db_results, limited_history
                 )
                 assistant_response_content = ai_explanation if ai_explanation else "Processed the request."
            else: # status == "error"
                 error_msg = error_msg or "An unknown error occurred during processing."
                 ai_explanation = error_msg
                 assistant_response_content = ai_explanation

            logger.info("Returning data as JSON response with explanation.")
            history.append(current_user_message); history.append({"role": "assistant", "content": assistant_response_content})
            conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]
            response = QueryResponse(
                status=status_msg, natural_query=request.natural_language_query,
                sql_query=f"Template: {sql_template} | Params: {params}" if sql_template else None,
                results=db_results, explanation=ai_explanation, error=error_msg,
                session_id=session_id
            )
            return response

        # Fallback safeguard
        logger.error("Reached unexpected end of endpoint logic.")
        raise HTTPException(status_code=500, detail="Server error: Invalid response state.")

    # --- Exception Handling ---
    except ValueError as ve:
        logger.error(f"Caught ValueError in main try block: {ve}")
        status_msg = "error"; error_msg = str(ve) if str(ve) else "Processing error occurred."
        if "validation failed" in error_msg.lower(): sql_template = None; params = None
    except Exception as e:
        logger.exception("[Exception Block] Caught unexpected exception:")
        status_msg = "error"; error_msg = repr(e) if repr(e) else "An unexpected server error occurred."
        sql_template = None; db_results = None

    # --- Return Error Response ---
    final_error_msg = error_msg or "An unspecified error occurred."
    logger.info(f"FINAL: Returning error as JSON response due to exception: {final_error_msg}")
    history.append(current_user_message)
    history.append({"role": "assistant", "content": final_error_msg})
    conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]

    error_response = QueryResponse(
        status=status_msg or "error", natural_query=request.natural_language_query,
        sql_query=f"Template: {sql_template} | Params: {params}" if sql_template else None,
        results=None, explanation=None, error=final_error_msg, session_id=session_id
    )
    return error_response

async def process_modification(
    action_type: str, 
    action_details: dict, 
    natural_query: str, 
    session_id: str, 
    current_user_message: dict, 
    history: list
) -> QueryResponse:
    """
    Processes data modification requests (record_sale, add_stock).
    Performs pre-execution checks, validates and executes SQL update statements,
    and returns appropriate response.
    """
    logger.info(f"Processing modification: {action_type} with details: {action_details}")
    
    # Convert item name to uppercase for consistent database operations
    item_name = action_details.get("item_name", "").upper()
    quantity = action_details.get("quantity", 0)
    
    # Update the action_details with uppercase item name for response
    action_details["item_name"] = item_name
    
    sql_template = None
    params = []
    status = "success"
    error_msg = None
    ai_explanation = None
    db_results = None
    
    try:
        # 1. Check if item exists
        if not check_item_exists(item_name):
            logger.warning(f"Item '{item_name}' does not exist in inventory.")
            status = "error"
            error_msg = f"Item '{item_name}' not found in inventory. Please add this item first."
            raise ValueError(error_msg)
        
        # 2. For record_sale, ensure sufficient stock is available
        if action_type == "record_sale":
            available_quantity = get_item_quantity(item_name)
            if available_quantity < quantity:
                logger.warning(f"Insufficient stock for sale: requested {quantity}, available {available_quantity}.")
                status = "error"
                error_msg = f"Cannot record sale: only {available_quantity} units of '{item_name}' available, but tried to sell {quantity}."
                raise ValueError(error_msg)
            
            # Generate UPDATE statement for recording a sale
            sql_template = """
            UPDATE inventory 
            SET quantity_sold = quantity_sold + ?, 
                quantity_available = quantity_available - ? 
            WHERE item = ?
            """
            params = [quantity, quantity, item_name]
            
        elif action_type == "add_stock":
            # Generate UPDATE statement for adding stock
            sql_template = """
            UPDATE inventory 
            SET quantity_available = quantity_available + ? 
            WHERE item = ?
            """
            params = [quantity, item_name]
        
        # 3. Validate the SQL statement
        if not validate_sql(sql_template):
            logger.warning("SQL validation failed for modification.")
            status = "error"
            error_msg = "SQL validation failed for the modification operation."
            raise ValueError(error_msg)
        
        # 4. Execute the modification
        rows_affected, db_error = execute_modification(sql_template, tuple(params))
        
        if db_error:
            status = "error"
            error_msg = db_error
            raise ValueError(db_error)
        
        if rows_affected == 0:
            status = "warning"
            error_msg = f"No rows were affected. The item '{item_name}' may not exist."
            ai_explanation = error_msg
        else:
            # 5. Check the new state and generate explanation
            if action_type == "record_sale":
                # Query the updated state
                query = "SELECT * FROM inventory WHERE item = ?"
                db_results = execute_query(query, (item_name,))
                remaining = db_results[0].get('quantity_available', 0) if db_results else 0
                
                ai_explanation = f"Recorded sale of {quantity} units of '{item_name}'. Remaining stock: {remaining} units."
            else:  # add_stock
                # Query the updated state
                query = "SELECT * FROM inventory WHERE item = ?"
                db_results = execute_query(query, (item_name,))
                new_quantity = db_results[0].get('quantity_available', 0) if db_results else 0
                
                ai_explanation = f"Added {quantity} units of '{item_name}' to inventory. New stock level: {new_quantity} units."
    
    except ValueError as ve:
        logger.error(f"Error during modification: {ve}")
        status = "error"
        error_msg = str(ve)
        ai_explanation = error_msg
    except Exception as e:
        logger.exception(f"Unexpected error during modification: {e}")
        status = "error"
        error_msg = f"Unexpected error during modification: {str(e)}"
        ai_explanation = error_msg
    
    # Update conversation history
    assistant_response = ai_explanation or error_msg or "Modification completed."
    history.append(current_user_message)
    history.append({"role": "assistant", "content": assistant_response})
    conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]
    
    # Return the response
    return QueryResponse(
        status=status,
        natural_query=natural_query,
        sql_query=f"Template: {sql_template} | Params: {params}" if sql_template else None,
        results=db_results,
        explanation=ai_explanation,
        error=error_msg,
        session_id=session_id,
        modification_type=action_type,
        modification_details=action_details
    )
