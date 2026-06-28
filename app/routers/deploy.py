from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Node
from ..schemas.network import DeviceCredentials
from ..services.diff_tool import assess_changes
from ..services.apply_config import deploy_config

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

@router.post("/assess")
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

    report = assess_changes(current_state, desired_config)
    return {"audit_report": report}

@router.post("/push")
async def push(device_ip: str, config_data: dict):
    success, msg = deploy_config(device_ip, config_data)
    
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    
    return {"status": "success", "message": msg}
