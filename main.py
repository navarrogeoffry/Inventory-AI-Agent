# main.py (Located in your project root)

# --- Core Imports & Initial Definitions (VERY TOP) ---
import os
import sys
import subprocess
import pathlib
import logging # Import logging early for potential setup issues

# --- Constants and Base Directory ---
# This assumes main.py and setup.py are in the same project root directory.
try:
    if getattr(sys, 'frozen', False): # PyInstaller bundle
        BASE_DIR = pathlib.Path(sys._MEIPASS)
    else: # Running as script
        BASE_DIR = pathlib.Path(__file__).resolve().parent
except Exception as e:
    # Fallback if __file__ is not defined (e.g. interactive interpreter, though unlikely for this script)
    BASE_DIR = pathlib.Path(os.getcwd())
    # Initial minimal logging for this critical path determination
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.warning(f"Could not reliably determine script path, using CWD as BASE_DIR: {BASE_DIR}. Error: {e}")


SETUP_SCRIPT_NAME = "setup.py"
VENV_DIR_NAME = ".venv"  # Name of the venv directory, matches setup.py
VENV_PATH = BASE_DIR / VENV_DIR_NAME

# Platform-specific Python executable within the virtual environment
if os.name == 'nt':
    VENV_PYTHON_EXEC = VENV_PATH / "Scripts" / "python.exe"
else:
    VENV_PYTHON_EXEC = VENV_PATH / "bin" / "python"

# --- Helper Functions ---
def is_running_in_venv():
    """
    Checks if the current Python script is running within an activated virtual environment
    that matches our project's VENV_PATH.
    """
    # Standard checks for any venv
    standard_venv_active = (hasattr(sys, 'real_prefix') or
                            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
    
    # Check if the VIRTUAL_ENV environment variable is set and points to our project's venv
    project_venv_env_var = os.environ.get("VIRTUAL_ENV")
    if project_venv_env_var:
        try:
            # Normalize paths for comparison
            return pathlib.Path(project_venv_env_var).resolve() == VENV_PATH.resolve()
        except Exception: # Handle potential errors with path resolution
            return False # If path is invalid, it's not our venv

    # Fallback to standard checks if VIRTUAL_ENV is not set (e.g., venv activated but VIRTUAL_ENV somehow unset)
    # This part is less specific to *our* venv but indicates *a* venv is active.
    # For re-launch logic, we primarily care that sys.executable points to VENV_PYTHON_EXEC.
    if standard_venv_active and sys.executable == str(VENV_PYTHON_EXEC.resolve()):
        return True
        
    return False


def trigger_setup_script(base_dir_path: pathlib.Path):
    """
    Runs the setup.py script to ensure the environment is configured.
    Returns True if setup script ran (or was checked) successfully, False otherwise.
    """
    setup_script_full_path = base_dir_path / SETUP_SCRIPT_NAME
    print(f"--- main.py: Ensuring development environment via '{setup_script_full_path.resolve()}' ---")
    
    if not setup_script_full_path.exists():
        print(f"CRITICAL ERROR: '{SETUP_SCRIPT_NAME}' not found at '{setup_script_full_path.resolve()}'.")
        print(f"BASE_DIR is currently: {base_dir_path.resolve()}")
        print(f"Current working directory is: {os.getcwd()}")
        print("Please ensure 'setup.py' is in the same directory as 'main.py'.")
        return False
    
    try:
        # Run setup.py using the current Python interpreter (sys.executable).
        # setup.py itself handles using system Python for initial venv creation if needed.
        command = [sys.executable, str(setup_script_full_path)] + sys.argv[1:]
        print(f"main.py: Executing command: {' '.join(command)}")
        process = subprocess.run(command, check=True, cwd=base_dir_path) # Run with cwd as BASE_DIR
        print(f"--- main.py: '{SETUP_SCRIPT_NAME}' execution finished successfully. ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR in main.py: '{SETUP_SCRIPT_NAME}' failed with exit code {e.returncode}.")
        if e.stdout: print(f"Stdout:\n{e.stdout}")
        if e.stderr: print(f"Stderr:\n{e.stderr}")
        return False
    except FileNotFoundError: # Should be caught by the exists() check, but as a safeguard
        print(f"ERROR in main.py: Could not execute '{SETUP_SCRIPT_NAME}'. File not found during subprocess call.")
        return False
    except Exception as e:
        print(f"ERROR in main.py: An unexpected error occurred while trying to run '{SETUP_SCRIPT_NAME}': {e}")
        return False


def application_startup_and_logic():
    """
    Contains all application-specific startup (dotenv, logging) and the main application logic (FastAPI).
    This function is called only after main.py is confirmed to be running in the correct venv.
    """
    print("--- main.py: Application startup and logic begins (running in venv) ---")

    # --- Environment Variable Loading & Initial Setup ---
    from dotenv import load_dotenv, find_dotenv, set_key # Import here, as venv should provide it

    ENV_FILE = BASE_DIR / ".env" # .env file in the project root

    # Attempt to load existing .env file. If it doesn't exist, find_dotenv returns "" (empty string)
    # raise_error_if_not_found=False prevents crashing if it's not there yet.
    # usecwd=True might be problematic if main.py is not run from BASE_DIR, so ensure paths are absolute.
    loaded_env_path = load_dotenv(dotenv_path=ENV_FILE, override=False) # override=False won't overwrite existing env vars

    if loaded_env_path: # True if a .env file was found and loaded
        print(f"main.py: Loaded environment variables from: {loaded_env_path}")
    else:
        print(f"main.py: .env file not found at '{ENV_FILE.resolve()}' or could not be loaded.")

    # API Key Setup - only if not already set by OS environment or a pre-existing .env file
    if not os.getenv("OPENAI_API_KEY"):
        print("main.py: OPENAI_API_KEY not found in current environment.")
        if ENV_FILE.exists():
            print(f"main.py: Existing .env file found at {ENV_FILE.resolve()}")
            # No overwrite prompt here, assuming setup.py or manual setup handles initial key
            # Or, you can add the overwrite prompt back if desired.
        
        api_key_input = input("Please enter your OpenAI API key (or press Enter to skip if already set elsewhere): ").strip()
        if api_key_input:
            try:
                set_key(str(ENV_FILE), "OPENAI_API_KEY", api_key_input, quote_mode="always")
                print(f"main.py: OpenAI API key has been saved to {ENV_FILE.resolve()}")
                # Reload .env to make the new key available in the current session
                if not load_dotenv(dotenv_path=ENV_FILE, override=True): # Override to load the new key
                     print(f"main.py: WARNING: Failed to reload .env file after saving API key: {ENV_FILE.resolve()}")
            except Exception as e:
                print(f"main.py: ERROR: Error writing API key to .env file: {e}")
        elif not loaded_env_path and not os.getenv("OPENAI_API_KEY"): # No key provided, no .env loaded, and still no key
             print("main.py: WARNING: No OpenAI API key provided and none found in environment. Application might not function correctly.")


    # --- Logging Configuration (after .env is potentially loaded) ---
    # Logging is imported at the top, basicConfig is applied here.
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Reconfigure logging with file handler now that BASE_DIR is solid
    # Get existing root logger and remove handlers if any were added by basicConfig earlier
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close() # Important to close handlers before removing

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(), # Allow LOG_LEVEL from .env
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOGS_DIR / "app.log", mode="a") # "a" to append to log
        ]
    )
    logger = logging.getLogger(__name__) # Logger for main.py (this module)

    logger.info(f"MAIN.PY: Logging configured. Running with Python: {sys.executable}")
    logger.info(f"MAIN.PY: BASE_DIR determined as: {BASE_DIR.resolve()}")
    logger.info(f"MAIN.PY: Current working directory: {os.getcwd()}")
    if loaded_env_path:
        logger.info(f"MAIN.PY: Successfully loaded .env file from: {loaded_env_path}")
    else:
        logger.info(f"MAIN.PY: .env file was not found at '{ENV_FILE.resolve()}' or not loaded initially by python-dotenv.")


    # --- Standard & Application-Specific Imports (now that we are in venv) ---
    import uvicorn
    import socket
    import webbrowser
    import threading
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi.middleware.cors import CORSMiddleware

    try:
        from app.routes import api as api_router_module
        from app.db import init_db
        logger.info("MAIN.PY: Successfully imported application modules (app.routes.api, app.db).")
    except ImportError as e:
        logger.error(f"MAIN.PY: Failed to import application modules (app.routes.api or app.db): {e}")
        logger.error(f"MAIN.PY: This usually means the virtual environment is not set up correctly or packages are missing.")
        logger.error(f"MAIN.PY: Python executable: {sys.executable}")
        logger.error(f"MAIN.PY: sys.path: {sys.path}")
        input("Press Enter to exit...")
        sys.exit(1)

    # --- Path Definitions for Static Content ---
    ROOT_STATIC_DIR_FOR_CHARTS = BASE_DIR / "static"
    REACT_PROJECT_DIR = BASE_DIR / "chatbot-ui"
    REACT_BUILD_DIR = REACT_PROJECT_DIR / "build"
    REACT_APP_INTERNAL_STATIC_SUBDIR = REACT_BUILD_DIR / "static"

    # --- Check for OpenAI API key (final check) ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.error("MAIN.PY: CRITICAL: OpenAI API key not found in environment variables after all setup attempts.")
        # Decide if you want to exit or let the app try to run without it.
        # For now, we'll log and continue, but parts of your app will fail.
    else:
        logger.info("MAIN.PY: OpenAI API Key confirmed to be loaded for the application.")

    # --- FastAPI Lifespan Manager ---
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        logger.info("MAIN.PY: FastAPI application starting up...")
        logger.info(f"MAIN.PY: Ensured directory for generated charts exists: {ROOT_STATIC_DIR_FOR_CHARTS.resolve()}")

        if not REACT_BUILD_DIR.is_dir():
            logger.warning(f"MAIN.PY: React build directory '{REACT_BUILD_DIR.resolve()}' not found. Frontend may not load. Run 'npm run build' in '{REACT_PROJECT_DIR}'.")
        elif not (REACT_BUILD_DIR / "index.html").exists():
            logger.warning(f"MAIN.PY: React 'index.html' not found in '{REACT_BUILD_DIR.resolve()}'. Frontend will not load. Please run 'npm run build'.")
        if not REACT_APP_INTERNAL_STATIC_SUBDIR.is_dir():
            logger.warning(f"MAIN.PY: React app's internal static assets folder '{REACT_APP_INTERNAL_STATIC_SUBDIR.resolve()}' not found. Frontend styles/scripts might be missing.")

        try:
            init_db() # Initialize database
            logger.info("MAIN.PY: Database initialized successfully.")
        except Exception as e:
            logger.error(f"MAIN.PY: Error initializing database: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
        yield
        logger.info("MAIN.PY: FastAPI application shutting down...")

    # --- FastAPI App Instance Creation ---
    app = FastAPI(
        title="Inventory AI Agent",
        description="AI assistant for managing inventory via natural language.",
        version="0.1.0",
        lifespan=lifespan
    )

    # --- CORS Middleware ---
    # Determine allowed origins dynamically based on current backend port
    backend_port = int(os.getenv('PORT', 8000)) # Default to 8000 if not set
    allowed_origins = [
        "http://localhost:3000", "http://127.0.0.1:3000", # Common React dev port
        "http://localhost:3001", "http://127.0.0.1:3001", # Another common dev port
        f"http://localhost:{backend_port}",
        f"http://127.0.0.1:{backend_port}"
    ]
    logger.info(f"MAIN.PY: CORS allowed origins: {allowed_origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Static File Mounts ---
    if REACT_APP_INTERNAL_STATIC_SUBDIR.exists() and REACT_APP_INTERNAL_STATIC_SUBDIR.is_dir():
        app.mount("/static", StaticFiles(directory=REACT_APP_INTERNAL_STATIC_SUBDIR), name="react-app-static-assets")
        logger.info(f"MAIN.PY: Serving React app's internal static assets from '{REACT_APP_INTERNAL_STATIC_SUBDIR.resolve()}' under URL '/static'")
    else:
        logger.error(f"MAIN.PY: CRITICAL: React app's static assets directory '{REACT_APP_INTERNAL_STATIC_SUBDIR.resolve()}' NOT FOUND. UI will be broken. Ensure 'npm run build' was run in '{REACT_PROJECT_DIR}'.")

    CHARTS_URL_PATH = "/generated_charts"  # Distinct URL path
    app.mount(CHARTS_URL_PATH, StaticFiles(directory=ROOT_STATIC_DIR_FOR_CHARTS), name="static")
    logger.info(f"MAIN.PY: Serving generated charts from '{ROOT_STATIC_DIR_FOR_CHARTS.resolve()}' under URL '{ROOT_STATIC_DIR_FOR_CHARTS}'")

    # --- API Routes ---
    app.include_router(api_router_module.router, prefix="/api")

    # --- Serve React App (index.html catch-all) ---
    @app.get("/{full_path:path}")
    async def serve_react_app_catch_all(full_path: str):
        index_file = REACT_BUILD_DIR / "index.html"
        logger.debug(f"MAIN.PY: Catch-all route: Requested path: '{full_path}', attempting to serve '{index_file.resolve()}'")
        if not index_file.exists():
            logger.error(f"MAIN.PY: React index.html not found at: {index_file.resolve()}. Did you run 'npm run build' in '{REACT_PROJECT_DIR}'?")
            if not REACT_BUILD_DIR.is_dir():
                logger.error(f"MAIN.PY: React build directory '{REACT_BUILD_DIR.resolve()}' does not exist.")
            raise HTTPException(status_code=404, detail="Frontend entry point (index.html) not found. Build the React app.")
        return FileResponse(index_file)

    # --- Server Execution ---
    def run_fastapi_server_logic(): # Renamed to avoid conflict
        logger.info("MAIN.PY: Attempting to start Inventory AI Agent FastAPI server...")
        available_port = None
        # Use a port range or a specific port from environment variable
        start_port = int(os.getenv("FASTAPI_PORT", 8000))
        for i in range(4): # Try 4 ports starting from FASTAPI_PORT
            port_to_try = start_port + i
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5) # Shorter timeout
            try:
                if sock.connect_ex(('127.0.0.1', port_to_try)) != 0: # Port is available
                    available_port = port_to_try
                    logger.info(f"MAIN.PY: Port {port_to_try} is available.")
                    break
                else:
                    logger.warning(f"MAIN.PY: Port {port_to_try} is already in use.")
            except socket.error as e:
                logger.debug(f"MAIN.PY: Socket error checking port {port_to_try}: {e}")
            finally:
                sock.close()

        if available_port is None:
            logger.error(f"MAIN.PY: No available backend ports found starting from {start_port}. Exiting.")
            input("Press Enter to exit...")
            sys.exit(1)

        os.environ['PORT'] = str(available_port) # Update PORT for CORS and browser opening
        logger.info(f"MAIN.PY: FastAPI server will run on http://localhost:{available_port}")

        def open_browser_after_delay(port: int):
            try:
                import time
                time.sleep(2) # Give server a moment to start
                webbrowser.open_new_tab(f"http://localhost:{port}")
                logger.info(f"MAIN.PY: Attempted to open web browser to http://localhost:{port}")
            except Exception as e:
                logger.warning(f"MAIN.PY: Could not open browser automatically: {e}")

        if os.getenv("AUTO_OPEN_BROWSER", "true").lower() == "true":
            browser_thread = threading.Thread(target=open_browser_after_delay, args=(available_port,), daemon=True)
            browser_thread.start()

        try:
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=available_port,
                log_level=os.getenv("UVICORN_LOG_LEVEL", "info").lower()
            )
        except SystemExit:
            logger.info("MAIN.PY: Uvicorn server shut down (SystemExit).")
        except Exception as e:
            logger.error(f"MAIN.PY: Error starting FastAPI server: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

    run_fastapi_server_logic() # Call the server run logic


# --- Main Execution Guard ---
if __name__ == "__main__":
    # Minimal initial logging until proper config is loaded
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"--- main.py started. Initial Python: {sys.executable} ---")
    logging.info(f"--- Determined BASE_DIR: {BASE_DIR.resolve()} ---")
    logging.info(f"--- Expected VENV_PYTHON_EXEC: {VENV_PYTHON_EXEC.resolve()} ---")
    logging.info(f"--- Current sys.executable: {pathlib.Path(sys.executable).resolve()} ---")


    if not is_running_in_venv():
        logging.warning("main.py: Not currently running in the project's virtual environment.")
        
        if not trigger_setup_script(BASE_DIR): # Pass BASE_DIR to the function
            logging.error("main.py: Setup script failed. Please check errors. Exiting main.py.")
            sys.exit(1)

        if VENV_PYTHON_EXEC.exists():
            logging.info(f"main.py: Virtual environment Python found at: {VENV_PYTHON_EXEC.resolve()}")
            logging.info(f"main.py: Attempting to re-launch main.py using this interpreter...")
            try:
                # Ensure all paths passed to execv are strings
                args_for_execv = [str(VENV_PYTHON_EXEC.resolve()), str(BASE_DIR / __file__)] + sys.argv[1:]
                logging.info(f"main.py: Re-launching with: {args_for_execv}")
                os.execv(str(VENV_PYTHON_EXEC.resolve()), args_for_execv)
                # os.execv replaces the current process, so code below this won't run if successful
            except Exception as e:
                logging.error(f"main.py: Failed to re-launch main.py with venv Python: {e}")
                logging.error("main.py: Please try activating the virtual environment manually and re-running the script.")
                logging.error(f"Attempted to use: {VENV_PYTHON_EXEC.resolve()}")
                sys.exit(1)
        else:
            logging.error(f"main.py: Error: Virtual environment Python executable not found at '{VENV_PYTHON_EXEC.resolve()}' even after running setup.")
            logging.error("main.py: Please check 'setup.py' for errors. Cannot re-launch.")
            sys.exit(1)
    else:
        logging.info("main.py: Already running in the project's virtual environment.")
        # Even if in venv, run setup.py to catch any updates to requirements.
        # setup.py is idempotent, so it will be quick if no changes are needed.
        if not trigger_setup_script(BASE_DIR): # Pass BASE_DIR
            logging.error("main.py: Setup script check/update failed. Please review errors. Exiting main.py.")
            sys.exit(1)
        
        application_startup_and_logic() # Proceed to application

