from fastapi import FastAPI
from app.routes import api

app = FastAPI(title="Warehouse AI Agent")

app.include_router(api.router)

# Run with: uvicorn app.main:app --reload
