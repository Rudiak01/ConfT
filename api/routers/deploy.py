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

@router.post("/topology")
async def assess(
    device_ip: str,
    desired_config: dict,
    db: Session = Depends(get_db)
):
    # Récupérer l'état actuel en base (ou via SSH si besoin)
    node = db.query(Node).filter(Node.ip_address == device_ip).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # On simule un état actuel à partir de la BDD
    current_state = {
        "vlans": [{"vlan_id": i.vlan_id, "name": f"VLAN{i.vlan_id}"} for i in node.interfaces if i.vlan_id],
        "interfaces": [
            {
                "interface": i.name,
                "mode": i.mode or "",
                "vlan": i.vlan_id,
                "allowed_vlans": i.allowed_vlans
            } for i in node.interfaces
        ]
    }

    with open("back/current_state_temp.json", "w", encoding="utf-8") as f:
        json.dump(current_state, f)
    with open("back/desired_config_temp.json", "w", encoding="utf-8") as f:
        json.dump(desired_config, f)

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        compare_configs("current_state_temp.json", "desired_config_temp.json")
    
    report = f.getvalue()

    if os.path.exists("back/current_state_temp.json"):
        os.remove("back/current_state_temp.json")
    if os.path.exists("back/desired_config_temp.json"):
        os.remove("back/desired_config_temp.json")

    return {"audit_report": report}

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
