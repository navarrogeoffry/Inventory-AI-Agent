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
from app.db import execute_query
from app.plotting import create_bar_chart, create_pie_chart, create_line_chart, create_scatter_plot
from app.sql_validator import validate_sql # Import validation function
from app.ai_processing import get_sql_and_chart_info, get_ai_explanation # Import AI functions

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
    session_id = request.session_id
    if session_id and session_id in conversation_histories:
        history = conversation_histories[session_id]; logger.info(f"Using session {session_id} with {len(history)} turns.")
    else:
        session_id = str(uuid.uuid4()); history = []; conversation_histories[session_id] = history; logger.info(f"Started new session {session_id}.")
    current_user_message = {"role": "user", "content": request.natural_language_query}
    limited_history = history[-(MAX_HISTORY_TURNS * 2):]

    # --- Initialize variables ---
    sql_template: str | None = None; params: list | None = None; response_type: str | None = "data"; chart_type: str | None = None
    x_col_suggestion: str | None = None; y_col_suggestion: str | None = None; db_results: list | None = None
    status_msg: str | None = None # Initialize status to None
    error_msg: str | None = None; ai_explanation: str | None = None
    assistant_response_content: str | None = None # For history

    try:
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
                elif chart_type == "pie": plot_func = lambda d, x, y, t: create_pie_chart(d, label_col=x, value_col=y, title=t)
                elif chart_type == "line": plot_func = create_line_chart
                elif chart_type == "scatter": plot_func = create_scatter_plot
                if plot_func: image_buffer = plot_func(db_results, x_col=x_col, y_col=y_col, title=plot_title)
                else: error_msg = f"Unknown chart type '{chart_type}'."; response_type = "data"
                # Return image if successful
                if image_buffer:
                    logger.info("Returning generated chart as image response.")
                    history.append(current_user_message); history.append({"role": "assistant", "content": f"Generated a {chart_type} chart."})
                    conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]
                    return StreamingResponse(image_buffer, media_type="image/png")
                else: # Plotting failed
                     logger.warning("Plotting function failed."); response_type = "data"; status_msg = "warning"
                     error_msg = error_msg or "Failed to generate requested chart."; ai_explanation = error_msg
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
