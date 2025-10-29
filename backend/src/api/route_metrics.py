from fastapi import APIRouter
# from core.database import signals_db
from src.core.db.connection import get_connection


router = APIRouter(prefix="/metrics", tags=["Metrics"])
@router.get("/latest")
def get_latest_signals(limit: int = 1):
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT * FROM daily_metrics ORDER BY date DESC LIMIT %s""", (limit,))
        metrics = cursor.fetchall()
        
        return metrics
