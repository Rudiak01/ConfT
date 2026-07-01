from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from backend.db.models import Node as DBNode, Interface as DBInterface
from ..models import DeviceCredentials
from back.extract_config import crawl_network

router = APIRouter(prefix="/api", tags=["discovery"])

@router.post("/network/crawl")
async def start_discovery(credentials: DeviceCredentials, db: Session = Depends(get_db)):
    try:
        result = crawl_network(credentials.host, credentials.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Discovery failed")
        
        # Stockage dans la BDD
        nodes_created = []
        for ip, data in result.get("nodes", {}).items():
            node = db.query(DBNode).filter(DBNode.ip_address == ip).first()
            if not node:
                node = DBNode(
                    ip_address=ip,
                    hostname=data.get("hostname"),
                    device_type=data.get("device_type")
                )
                db.add(node)
                db.commit()
                db.refresh(node)
            else:
                node.hostname = data.get("hostname")
                node.device_type = data.get("device_type")
                db.commit()

            # Interfaces (optionnel — ici on stocke les VLANs comme interfaces virtuelles)
            for vlan in data.get("vlans", []):
                iface = db.query(DBInterface).filter(
                    DBInterface.node_id == node.id, 
                    DBInterface.vlan_id == int(vlan["vlan_id"])
                ).first()
                
                if not iface:
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
