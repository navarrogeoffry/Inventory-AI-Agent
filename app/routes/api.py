from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/process_query")
def process_query(query: dict):
    # Placeholder logic
    return {"message": "Processing query", "query": query}
