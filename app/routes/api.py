# app/routes/api.py
import pathlib
from fastapi import APIRouter, HTTPException, Depends
# from fastapi.responses import StreamingResponse # Not used here
from pydantic import BaseModel, Field
import logging
import os
import io
import uuid
from typing import List, Dict, Any, Tuple

# --- Path Setup for Chart Saving ---
# Assumes main.py (the script being run) is in the project root.
# So, at the time this module is imported, cwd() should be the project root.
PROJECT_ROOT_FOR_API = pathlib.Path(__file__).resolve().parent.parent.parent
CHART_SAVE_DIRECTORY = PROJECT_ROOT_FOR_API / "static"  
# Ensure this directory exists when the module is loaded.
# main.py's lifespan manager also ensures this, but this is good for direct tests/robustness.
try:
    CHART_SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)
except Exception as e_mkdir_api:
    # If logger isn't configured yet by main.py, this might not show.
    # But main.py's early logging setup should catch this if it's an issue for the app overall.
    print(f"API.PY WARNING: Could not create chart save directory {CHART_SAVE_DIRECTORY}: {e_mkdir_api}")


# Import functions from refactored modules
from app.db import execute_query, execute_modification, check_item_exists, get_item_quantity
from app.plotting import create_bar_chart, create_pie_chart, create_line_chart, create_scatter_plot

plot_func_map = {
    "bar": create_bar_chart,
    "pie": create_pie_chart,
    "line": create_line_chart,
    "scatter": create_scatter_plot,
}
from app.sql_validator import validate_sql
from app.ai_processing import get_sql_and_chart_info, get_ai_explanation, get_modification_intent
plot_func_map = {
    "bar": create_bar_chart,
    "pie": create_pie_chart,
    "line": create_line_chart,
    "scatter": create_scatter_plot,
}
logger = logging.getLogger(__name__) # Get logger instance

# Add a test log message at module load time for api.py
logger.critical("API.PY: Module loaded and logger is active. CRITICAL.")
logger.error("API.PY: Module loaded and logger is active. ERROR.")
logger.warning("API.PY: Module loaded and logger is active. WARNING.")
logger.info("API.PY: Module loaded and logger is active. INFO.")
logger.debug("API.PY: Module loaded and logger is active. DEBUG.")


# --- In-Memory Conversation History Store ---
conversation_histories: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 5

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    natural_language_query: str
    user_id: str | None = None
    session_id: str | None = None

class QueryResponse(BaseModel):
    status: str
    natural_query: str
    sql_query: str | None = None
    results: list | None = None
    explanation: str | None = None
    error: str | None = None
    session_id: str
    chart_url: str | None = None
    modification_type: str | None = None
    modification_details: dict | None = None

router = APIRouter()

@router.get("/health")
def health_check():
    logger.debug("Health check endpoint called.")
    return {"status": "ok"}

@router.post("/process_query")
async def process_query(request: QueryRequest):
    logger.info(f"API - process_query called with query: '{request.natural_language_query}', session: {request.session_id}")
    logger.debug(f"API - Using chart save directory: {CHART_SAVE_DIRECTORY.resolve()}")

    if request.session_id and request.session_id in conversation_histories:
        session_id = request.session_id
        history = conversation_histories[session_id]
    else:
        session_id = request.session_id or str(uuid.uuid4())
        history = []
        conversation_histories[session_id] = history
        logger.info(f"API - Started new session {session_id} for query.")

    current_user_message = {"role": "user", "content": request.natural_language_query}
    limited_history = history[-(MAX_HISTORY_TURNS * 2):]

    sql_template: str | None = None; params: list | None = None; response_type: str = "data"; chart_type: str | None = None
    x_col_suggestion: str | None = None; y_col_suggestion: str | None = None; db_results: list | None = None
    status_msg: str = "success"; error_msg: str | None = None; ai_explanation: str | None = None
    chart_url_for_frontend: str | None = None

    try:
        action_type, action_details = await get_modification_intent(
            request.natural_language_query, limited_history
        )
        
        if action_type in ["record_sale", "add_stock"] and action_details:
            logger.info(f"API - Detected modification intent: {action_type}")
            return await process_modification(
                action_type, action_details, 
                request.natural_language_query, session_id, 
                current_user_message, history # Pass full history to modification
            )
        
        (sql_template, params, response_type, chart_type,
         x_col_suggestion, y_col_suggestion) = await get_sql_and_chart_info(
             request.natural_language_query, limited_history
         )
        logger.debug(f"API - AI response: sql='{sql_template}', params='{params}', response_type='{response_type}', chart_type='{chart_type}'")

        if sql_template is None:
            status_msg, error_msg, response_type = "error", "AI failed to generate a valid SQL response.", "data"
            logger.error(error_msg)
        elif sql_template in ["QUERY_UNABLE_TO_GENERATE", "QUERY_UNSAFE"]:
            status_msg, error_msg, response_type = "error", f"Query cannot be processed: AI responded '{sql_template}'.", "data"
            logger.warning(error_msg)
        else:
            if not validate_sql(sql_template):
                status_msg, error_msg, response_type = "error", "Generated SQL failed validation.", "data"
                logger.error(error_msg)
            else:
                try:
                    db_results = execute_query(sql_template, tuple(params or []))
                    logger.info(f"API - DB query successful. Results count: {len(db_results) if db_results is not None else 'None'}")
                except ValueError as db_ve:
                    status_msg, error_msg, response_type = "error", f"Database error: {db_ve}", "data"
                    logger.error(error_msg)

        if response_type == "chart" and status_msg == "success":
            actual_columns = list(db_results[0].keys()) if db_results and db_results[0] else []
            x_col, y_col = x_col_suggestion, y_col_suggestion
            if not actual_columns:
                logger.error("API - No columns in db_results for chart. Fallback to data.")
                response_type, status_msg, error_msg = "data", "error", "Cannot generate chart, data has no columns."
            else:
                if x_col is None or x_col not in actual_columns:
                    x_col = actual_columns[0]
                if y_col is None or y_col not in actual_columns or y_col == x_col:
                    y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
                logger.info(f"API - Using columns for plot: x='{x_col}', y='{y_col}'")
                plot_func = plot_func_map.get(chart_type)
                if not plot_func:
                    logger.warning(f"API - Unknown chart type '{chart_type}'. Fallback to data.")
                    response_type, status_msg, error_msg = "data", "warning", f"Unsupported chart type: '{chart_type}'."
                else:
                    plot_title = f"Chart: {chart_type.title()} of {y_col} vs {x_col}"
                    logger.info(f"API - Generating chart with title: {plot_title}")
                    image_buffer = plot_func(db_results, x_col=x_col, y_col=y_col, title=plot_title)
                    if image_buffer:
                        filename = f"chart_{session_id[:8]}_{uuid.uuid4().hex[:8]}.png"
                        file_path_to_save = CHART_SAVE_DIRECTORY / filename
                        try:
                            with open(file_path_to_save, "wb") as f:
                                f.write(image_buffer.getvalue())
                            logger.info(f"API - SUCCESS: Chart saved to: {file_path_to_save.resolve()}")
                            chart_url_for_frontend = f"/generated_charts/{filename}"
                            logger.info(f"API - Generated chart URL for frontend: {chart_url_for_frontend}")
                            ai_explanation = f"Generated a {chart_type} chart."
                            history.append(current_user_message)
                            history.append({"role": "assistant", "content": ai_explanation, "chart_url": chart_url_for_frontend})
                            conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]
                            response_obj = QueryResponse(
                                status="success", natural_query=request.natural_language_query,
                                explanation=ai_explanation, session_id=session_id, chart_url=chart_url_for_frontend
                            )
                            logger.debug(f"API - Returning chart response: {response_obj.model_dump_json(indent=2)}")
                            return response_obj
                        except IOError as e:
                            logger.error(f"API - ERROR: Failed to save chart image to {file_path_to_save}: {e}")
                            status_msg, error_msg, response_type = "error", "Failed to save chart image.", "data"
                            ai_explanation = error_msg
                    else:
                        logger.warning("API - Plotting function returned no image buffer. Fallback to data.")
                        status_msg = status_msg if status_msg == "error" else "warning"
                        error_msg = error_msg or "Failed to generate chart image data."
                        ai_explanation = error_msg
                        response_type = "data"

        # Data response or fallback
        if response_type == "data":
            if status_msg == "success" and not error_msg:
                ai_explanation = await get_ai_explanation(request.natural_language_query, sql_template, db_results, limited_history)
            else: # status_msg is "warning" or "error"
                ai_explanation = ai_explanation or error_msg or "Could not process the request as expected."
            
            assistant_response_content = ai_explanation
            history.append(current_user_message)
            history.append({"role": "assistant", "content": assistant_response_content})
            conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]

            response_obj = QueryResponse(
                status=status_msg, natural_query=request.natural_language_query,
                sql_query=f"Template: {sql_template} | Params: {params}" if sql_template else None,
                results=db_results, explanation=ai_explanation,
                error=error_msg if status_msg == "error" else None,
                session_id=session_id, chart_url=None
            )
            logger.debug(f"API - Returning data response: {response_obj.model_dump_json(indent=2)}")
            return response_obj

    except ValueError as ve:
        logger.error(f"API - ValueError in process_query: {ve}")
        status_msg, error_msg = "error", str(ve)
    except Exception as e:
        logger.exception("API - Unexpected exception in process_query:")
        status_msg, error_msg = "error", "An unexpected server error occurred."
    
    # Fallback error response
    assistant_response_content = error_msg or "Failed to process the request."
    history.append(current_user_message)
    history.append({"role": "assistant", "content": assistant_response_content})
    conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]

    response_obj = QueryResponse(
        status=status_msg, natural_query=request.natural_language_query,
        sql_query=f"Template: {sql_template} | Params: {params}" if sql_template and status_msg != "error" else None,
        results=None, explanation=None, error=error_msg, session_id=session_id, chart_url=None
    )
    logger.debug(f"API - Returning fallback error response: {response_obj.model_dump_json(indent=2)}")
    return response_obj

async def process_modification(
    action_type: str, 
    action_details: dict, 
    natural_query: str, 
    session_id: str, 
    current_user_message: dict, 
    history: list # Full history for saving
) -> QueryResponse:
    logger.info(f"API - Processing modification: {action_type} with details: {action_details}")
    
    item_name = action_details.get("item_name", "").upper()
    quantity = action_details.get("quantity", 0)
    action_details["item_name"] = item_name 

    sql_template: str | None = None; params: list = []; db_results_after_mod: list | None = None
    status: str = "success"; error_msg: str | None = None; ai_explanation: str | None = None
    
    try:
        if not check_item_exists(item_name):
            raise ValueError(f"Item '{item_name}' not found in inventory.")
        
        if action_type == "record_sale":
            available_quantity = get_item_quantity(item_name)
            if available_quantity < quantity:
                raise ValueError(f"Insufficient stock for sale: requested {quantity} of '{item_name}', available {available_quantity}.")
            sql_template = "UPDATE inventory SET quantity_sold = quantity_sold + ?, quantity_available = quantity_available - ? WHERE item = ?"
            params = [quantity, quantity, item_name]
        elif action_type == "add_stock":
            sql_template = "UPDATE inventory SET quantity_available = quantity_available + ? WHERE item = ?"
            params = [quantity, item_name]
        else:
            raise ValueError(f"Unknown modification action_type: {action_type}")

        if not validate_sql(sql_template):
            raise ValueError("SQL validation failed for the modification.")
        
        rows_affected, db_error = execute_modification(sql_template, tuple(params))
        
        if db_error: raise ValueError(f"DB error during modification: {db_error}")
        if rows_affected == 0:
            status = "warning"
            ai_explanation = error_msg = f"No rows affected for item '{item_name}'. Check if item exists with exact name."
        else:
            query_after_mod = "SELECT item, quantity_available, quantity_sold FROM inventory WHERE item = ?"
            db_results_after_mod = execute_query(query_after_mod, (item_name,))
            if db_results_after_mod and db_results_after_mod[0]:
                current_stock = db_results_after_mod[0].get('quantity_available', 'N/A')
                total_sold = db_results_after_mod[0].get('quantity_sold', 'N/A')
                ai_explanation = f"Successfully {action_type.replace('_', ' ')} for {quantity} unit(s) of '{item_name}'. Current stock: {current_stock}. Total sold: {total_sold}."
            else:
                status = "warning"
                ai_explanation = error_msg = f"Modification for '{item_name}' successful ({rows_affected} row(s) affected), but failed to retrieve updated stock details."

    except ValueError as ve:
        logger.error(f"API - ValueError in process_modification: {ve}")
        status, error_msg, ai_explanation = "error", str(ve), str(ve)
    except Exception as e:
        logger.exception("API - Unexpected exception in process_modification:")
        status, error_msg, ai_explanation = "error", "Unexpected server error during modification.", "Unexpected server error."
    
    assistant_response_content = ai_explanation or error_msg or "Modification processed."
    history.append(current_user_message)
    history.append({"role": "assistant", "content": assistant_response_content})
    conversation_histories[session_id] = history[-(MAX_HISTORY_TURNS * 2):]
    
    response_obj = QueryResponse(
        status=status, natural_query=natural_query,
        sql_query=f"Template: {sql_template} | Params: {params}" if sql_template else None,
        results=db_results_after_mod, explanation=ai_explanation,
        error=error_msg if status == "error" else None, session_id=session_id,
        modification_type=action_type if status == "success" else None,
        modification_details=action_details if status == "success" else None
    )
    logger.debug(f"API - Returning modification response: {response_obj.model_dump_json(indent=2)}")
    return response_obj
