from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import json
import io
import contextlib

from api.dependencies import get_db
from backend.db.models import Node
from ..models import DeviceCredentials
from back.diff_tool import compare_configs
from back.apply_config import apply_device_config

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


@router.post("/push")
async def push(device_ip: str, config_data: dict, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.ip_address == device_ip).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    connection_params = {
        "host": device_ip,
        "device_type": node.device_type or "cisco_ios",
        "username": "admin", # Default username, should be fetched from config or request ideally
        "password": "password" # Default password
    }
    
    success, msg = apply_device_config(connection_params, config_data)
    
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    
    return {"status": "success", "message": msg}
