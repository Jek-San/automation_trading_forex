from fastapi import APIRouter
from src.core.telegram import telegram_handler as tg

router = APIRouter(prefix="/telegram", tags=["Telegram"])

@router.get("/status")
def status():
    return tg.get_status()

@router.post("/start")
def start():
    tg.start_listener()
    return {"message": "Telegram started"}

@router.post("/stop")
def stop():
    tg.stop_listener()
    return {"message": "Telegram stopped"}

@router.post("/pause")
def pause():
    return tg.pause_listener()

@router.post("/resume")
def resume():
    return tg.resume_listener()
