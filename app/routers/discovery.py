from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Node as DBNode, Interface as DBInterface
from ..schemas.network import DeviceCredentials
from app.services.extract_config import discover_network

router = APIRouter(prefix="/api", tags=["discovery"])

@router.post("/discovery/start")
async def start_discovery(credentials: DeviceCredentials, db: Session = Depends(get_db)):
    try:
        result = discover_network(credentials.host, credentials.model_dump())
        
        # Stockage dans la BDD
        nodes_created = []
        for ip, data in result.get("nodes", {}).items():
            node = DBNode(
                ip_address=ip,
                hostname=data.get("hostname"),
                device_type=data.get("device_type")
            )
            db.add(node)
            db.commit()
            db.refresh(node)

            # Interfaces (optionnel — ici on stocke les VLANs comme interfaces virtuelles)
            for vlan in data.get("vlans", []):
                iface = DBInterface(
                    node_id=node.id,
                    name=f"VLAN{vlan['vlan_id']}",
                    description=f"VLAN {vlan['name']}",
                    mode="access",
                    vlan_id=int(vlan["vlan_id"])
                )
                db.add(iface)
            
            db.commit()

            nodes_created.append({
                "id": node.id,
                "ip_address": ip,
                "hostname": data.get("hostname"),
                "device_type": data.get("device_type")
            })

        return {
            "status": "success",
            "nodes_discovered": len(nodes_created),
            "details": nodes_created
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
