# Updated app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import api
from app.db import init_db
import logging
import os
from dotenv import load_dotenv # <-- Import load_dotenv

# ---> Load variables from .env file BEFORE they are needed <---
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info("Application starting up...")
    init_db() # Initialize the database and tables
    yield
    # Code to run on shutdown (if any)
    logger.info("Application shutting down...")

# Check if the API key loaded (optional, for debugging startup)
# api_key = os.getenv("OPENAI_API_KEY")
# if not api_key:
#    logger.warning("OPENAI_API_KEY environment variable not found.")
# else:
#    logger.info("OpenAI API Key loaded successfully (first few chars): " + api_key[:5] + "...")


app = FastAPI(
    title="Inventory AI Agent", # Changed title back, adjust as needed
    description="AI assistant for managing inventory via natural language.",
    version="0.1.0",
    lifespan=lifespan
)

# Use the /api prefix again if you prefer, otherwise remove it
# If you keep the prefix, docs are at /api/docs
# If you remove the prefix, docs are at /docs
app.include_router(api.router, prefix="/api") # Or app.include_router(api.router)

@app.get("/")
async def root():
    # Update message based on whether you use the /api prefix for docs
    return {"message": "Welcome to the Inventory AI Agent API. See /api/docs for details."}