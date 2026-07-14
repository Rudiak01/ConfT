from fastapi import APIRouter, Depends, HTTPException
from ..tools import push_config

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


@router.post("/push")
async def push(device_ip: str, config_data: dict):
    return push_config(device_ip, config_data)
