# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import api # Make sure api router is imported
from app.db import init_db # Import init_db if you want DB init on startup
import logging
import os
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv # Import if using .env file

#allow CORS
from fastapi.middleware.cors import CORSMiddleware

# Load .env file if it exists (for OPENAI_API_KEY)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan manager for startup tasks (like DB init)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    init_db() # Initialize the database
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
    allow_origins=["http://localhost:3000"],
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

# Example run command (as comment):
# uvicorn app.main:app --reload --port 8000
