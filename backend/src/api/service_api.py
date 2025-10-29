from fastapi import APIRouter, HTTPException
from src.core.app_state import scheduler

router = APIRouter(prefix="/services", tags=["Services"])

@router.get("/")
async def list_services():
    """List all services with their current running status"""
    return scheduler.get_status()


@router.post("/{name}/start")
async def start_service(name: str):
    """Start a single service"""
    success = await scheduler.start_service(name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Service '{name}' not found or already running.")
    return {"message": f"✅ Service '{name}' started successfully."}


@router.post("/{name}/stop")
async def stop_service(name: str):
    """Stop a single service"""
    success = await scheduler.stop_service(name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Service '{name}' not found or not running.")
    return {"message": f"🛑 Service '{name}' stopped successfully."}
