# main.py (Located in your project root)

# --- Environment Variable Loading & Initial Setup (VERY TOP) ---
import os
import sys
import pathlib
from dotenv import load_dotenv, find_dotenv, set_key

# Determine base directory - works for both script and PyInstaller executable
if getattr(sys, 'frozen', False):
    BASE_DIR = pathlib.Path(sys._MEIPASS) # PyInstaller bundle
else:
    BASE_DIR = pathlib.Path(__file__).resolve().parent # Running as script from project root

ENV_FILE = BASE_DIR / ".env"

# --- Helper Function for Environment Setup (defined early) ---
def setup_environment():
    print("--- Environment Setup ---")
    if ENV_FILE.exists():
        print(f"Found existing .env file at {ENV_FILE}")
        overwrite_response = input("An .env file already exists. Do you want to overwrite it? (y/n): ").strip().lower()
        if overwrite_response != 'y':
            print("Setup canceled. Your existing .env file was not modified.")
            if not load_dotenv(ENV_FILE):
                 print(f"Warning: Could not load existing .env file: {ENV_FILE}")
            return
    api_key = input("Please enter your OpenAI API key: ").strip()
    if not api_key:
        print("ERROR: No API key provided. Cannot proceed.")
        sys.exit(1)
    try:
        # Using set_key from python-dotenv to create/update .env
        set_key(str(ENV_FILE), "OPENAI_API_KEY", api_key, quote_mode="always")
        print(f"OpenAI API key has been saved/updated in {ENV_FILE}")
        if not load_dotenv(ENV_FILE): # Reload
            print(f"ERROR: Failed to load .env file after saving: {ENV_FILE}")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error writing to .env file: {e}")
        sys.exit(1)

# --- Actual .env loading attempt ---
if not load_dotenv(find_dotenv(filename=str(ENV_FILE), usecwd=True, raise_error_if_not_found=False)):
    print(f"Warning: .env file not found at '{ENV_FILE}'. Proceeding to environment setup.")
    setup_environment()

# --- Path Definitions & Logging Configuration (EARLY) ---
import logging # Import logging now

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for verbose output during debugging
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s', # Added filename/lineno
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "app.log", mode="w") # "w" for fresh log each run
    ]
)
logger = logging.getLogger(__name__) # Logger for main.py

logger.critical("MAIN.PY: Logging configured. CRITICAL.")
logger.error("MAIN.PY: Logging configured. ERROR.")
logger.warning("MAIN.PY: Logging configured. WARNING.")
logger.info("MAIN.PY: Logging configured. INFO.")
logger.debug("MAIN.PY: Logging configured. DEBUG.")

if find_dotenv(usecwd=True, filename=str(ENV_FILE)):
    logger.info(f"Successfully loaded .env file: {find_dotenv(usecwd=True, filename=str(ENV_FILE))}")
else:
    logger.info(".env file was created or confirmed during initial setup, or not found initially.")

# --- Standard Imports (after logging and .env) ---
import uvicorn
import socket
import webbrowser
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# --- Import application-specific modules ---
try:
    from app.routes import api as api_router_module
    from app.db import init_db
except ImportError as e:
    logger.error(f"Failed to import application modules (app.routes.api or app.db): {e}")
    logger.error(f"BASE_DIR: {BASE_DIR.resolve()}, sys.path: {sys.path}")
    input("Press Enter to exit...")
    sys.exit(1)

# --- Path Definitions for Static Content ---
# For backend-generated charts, saved into project_root/static/
ROOT_STATIC_DIR_FOR_CHARTS = BASE_DIR / "static"

# React app's build output directory
REACT_PROJECT_DIR = BASE_DIR / "chatbot-ui" # This was already in your main.py
REACT_BUILD_DIR = REACT_PROJECT_DIR / "build"
# React app's own static assets subfolder (e.g., chatbot-ui/build/static/ for CRA)
REACT_APP_INTERNAL_STATIC_SUBDIR = REACT_BUILD_DIR / "static"


# --- Check for OpenAI API key ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("ERROR: OpenAI API key not found in environment variables.")
    input("Press Enter to exit...")
    sys.exit(1)
else:
    logger.info("OpenAI API Key found and loaded.")


# --- FastAPI Lifespan Manager ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info("Application starting up...")
    ROOT_STATIC_DIR_FOR_CHARTS.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directory for generated charts exists: {ROOT_STATIC_DIR_FOR_CHARTS.resolve()}")

    if not REACT_BUILD_DIR.is_dir():
        logger.warning(f"React build directory '{REACT_BUILD_DIR.resolve()}' not found. Frontend may not load. Run 'npm run build' in '{REACT_PROJECT_DIR}'.")
    elif not (REACT_BUILD_DIR / "index.html").exists():
        logger.warning(f"React 'index.html' not found in '{REACT_BUILD_DIR.resolve()}'. Frontend will not load. Please run 'npm run build'.")
    if not REACT_APP_INTERNAL_STATIC_SUBDIR.is_dir():
         logger.warning(f"React app's internal static assets folder '{REACT_APP_INTERNAL_STATIC_SUBDIR.resolve()}' not found. Frontend styles/scripts might be missing.")

    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    yield
    logger.info("Application shutting down...")

# --- FastAPI App Instance Creation ---
app = FastAPI(
    title="Inventory AI Agent",
    description="AI assistant for managing inventory via natural language.",
    version="0.1.0",
    lifespan=lifespan
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", f"http://localhost:{os.getenv('PORT', 8000)}", f"http://127.0.0.1:{os.getenv('PORT', 8000)}"], # Allow access from common dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static File Mounts ---

# 1. Mount React app's internal static assets (JS, CSS from chatbot-ui/build/static/)
#    Your index.html requests assets from "/static/..."
if REACT_APP_INTERNAL_STATIC_SUBDIR.exists() and REACT_APP_INTERNAL_STATIC_SUBDIR.is_dir():
    app.mount("/static", StaticFiles(directory=REACT_APP_INTERNAL_STATIC_SUBDIR), name="react-app-static-assets")
    logger.info(f"Serving React app's internal static assets from '{REACT_APP_INTERNAL_STATIC_SUBDIR.resolve()}' under URL '/static'")
else:
    logger.error(f"CRITICAL: React app's static assets directory '{REACT_APP_INTERNAL_STATIC_SUBDIR.resolve()}' NOT FOUND. UI will be broken. Ensure 'npm run build' was run in '{REACT_PROJECT_DIR}'.")

# 2. Mount for backend-generated charts (saved by api.py into project_root/static/)
#    Served from a distinct URL path to avoid collision with React's /static.
CHARTS_URL_PATH = "/generated_charts" # Distinct URL path
app.mount(CHARTS_URL_PATH, StaticFiles(directory=ROOT_STATIC_DIR_FOR_CHARTS), name="generated-charts-static")
logger.info(f"Serving generated charts from '{ROOT_STATIC_DIR_FOR_CHARTS.resolve()}' under URL '{CHARTS_URL_PATH}'")


# --- API Routes ---
app.include_router(api_router_module.router, prefix="/api")

# --- Serve React App (index.html catch-all) ---
# This must be LAST among GET routes
@app.get("/{full_path:path}")
async def serve_react_app_catch_all(full_path: str):
    index_file = REACT_BUILD_DIR / "index.html"
    logger.debug(f"Catch-all route: Requested path: '{full_path}', attempting to serve '{index_file.resolve()}'")
    if not index_file.exists():
        logger.error(f"React index.html not found at: {index_file.resolve()}. Did you run 'npm run build' in '{REACT_PROJECT_DIR}'?")
        if not REACT_BUILD_DIR.is_dir():
             logger.error(f"React build directory '{REACT_BUILD_DIR.resolve()}' does not exist.")
        raise HTTPException(status_code=404, detail="Frontend entry point (index.html) not found. Build the React app.")
    return FileResponse(index_file)


# --- Server Execution ---
def run_fastapi_server():
    logger.info("Attempting to start Inventory AI Agent FastAPI server...")
    available_port = None
    for port_to_try in [8000, 8001, 8002, 8003]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex(('127.0.0.1', port_to_try))
            if result != 0:
                available_port = port_to_try
                logger.info(f"Port {port_to_try} is available.")
                break
            else:
                logger.warning(f"Port {port_to_try} is already in use.")
        except socket.error as e:
            logger.debug(f"Socket error checking port {port_to_try}: {e}")
        finally:
            sock.close()

    if available_port is None:
        logger.error("No available backend ports found in range 8000-8003. Exiting.")
        input("Press Enter to exit...")
        sys.exit(1)

    os.environ['PORT'] = str(available_port) # For CORS if needed, though already handled above
    logger.info(f"FastAPI server will run on http://localhost:{available_port}")

    def open_browser_after_delay(port: int):
        try:
            import time
            time.sleep(2)
            webbrowser.open_new_tab(f"http://localhost:{port}")
            logger.info(f"Attempted to open web browser to http://localhost:{port}")
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}")

    browser_thread = threading.Thread(target=open_browser_after_delay, args=(available_port,), daemon=True)
    browser_thread.start()

    try:
        uvicorn.run(
            app, # Pass the app instance directly
            host="0.0.0.0",
            port=available_port,
            log_level="info" # Uvicorn's own log level
        )
    except SystemExit: # Catches Ctrl+C from Uvicorn
        logger.info("Uvicorn server shut down (SystemExit).")
    except Exception as e:
        logger.error(f"Error starting FastAPI server: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

# --- Main Execution Guard ---
if __name__ == "__main__":
    run_fastapi_server()