from fastapi import APIRouter
# from core.database import signals_db

router = APIRouter()

@router.get("/latest")
def get_latest_signals(limit: int = 10):
    return {"message": "latest signals endpoint"}
