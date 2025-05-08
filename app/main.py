# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import api # Make sure api router is imported
from app.db import init_db # Import init_db if you want DB init on startup
import logging
import os
import sys
import uvicorn
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv # Import if using .env file

#allow CORS
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)

# Make sure logs directory exists
os.makedirs("logs", exist_ok=True)

# Load .env file if it exists (for OPENAI_API_KEY)
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    logger.error("ERROR: OpenAI API key not found in environment variables.")
    logger.error("Please set the OPENAI_API_KEY environment variable or create a .env file.")
    sys.exit(1)

# Lifespan manager for startup tasks (like DB init)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    try:
        init_db() # Initialize the database
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        sys.exit(1)
    yield
    logger.info("Application shutting down...")

# Create FastAPI app instance
app = FastAPI(
    title="Inventory AI Agent",
    description="AI assistant for managing inventory via natural language.",
    version="0.1.0",
    lifespan=lifespan # Include lifespan manager
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Include the API router WITH the prefix ---
# This makes routes in api.py available under /api/...
app.include_router(api.router, prefix="/api")

# Add a root endpoint for basic info/welcome message
@app.get("/")
async def root():
    # Update message to reflect the correct docs path
    return {"message": "Welcome to the Inventory AI Agent API. See /api/docs for details."}

# Run the server if this file is executed directly (not imported)
if __name__ == "__main__":
    logger.info("Starting Inventory AI Agent server...")
    
    # Try ports in sequence if previous ones are unavailable
    available_port = None
    for port in [8000, 8001, 8002, 8003]:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result != 0:  # Port is available
            available_port = port
            break
    
    if available_port is None:
        logger.error("No available ports found in range 8000-8003. Exiting.")
        sys.exit(1)
    
    logger.info(f"Using port {available_port} for the backend server")
    
    try:
        uvicorn.run(
            "app.main:app", 
            host="0.0.0.0", 
            port=available_port, 
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)
