from fastapi import APIRouter
from app.utils.utils import model

router = APIRouter()

@router.get("/health")
def health():
    try:
        # Test Google AI
        test_response = model.generate_content("Hello")
        return {"status": "healthy", "google_ai": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}