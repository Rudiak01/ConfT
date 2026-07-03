from fastapi import APIRouter, Depends, HTTPException
from ..models import DeviceCredentials
from ..tools import run_discovery

router = APIRouter(prefix="/api", tags=["discovery"])

@router.post("/network/crawl")
async def start_discovery(credentials: DeviceCredentials):
    return run_discovery(credentials.host, credentials.model_dump())
