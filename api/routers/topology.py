from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Node, Interface
from ..schemas.network import TopologyNode, TopologyLink, TopologyGraph, InterfaceSchema

router = APIRouter(prefix="/api/network", tags=["topology"])

@router.get("/topology", response_model=TopologyGraph)
def get_topology(db: Session = Depends(get_db)):
    nodes = db.query(Node).all()
    
    topology_nodes = [
        TopologyNode(
            id=n.id,
            ip_address=n.ip_address,
            hostname=n.hostname or "",
            device_type=n.device_type or ""
        ) for n in nodes
    ]
    
    # Liens : on utilise les interfaces trunk comme liens (ex: Gi0/1 → 192.168.2.1)
    links = []
    for node in nodes:
        for iface in node.interfaces:
            if iface.mode == "trunk":
                # Exemple simplifié : on suppose que l'IP cible est connue via un champ `target_ip` dans Interface
                # Ici, on simule avec une logique temporaire (à adapter selon votre besoin)
                pass
    
    return TopologyGraph(nodes=topology_nodes, links=links)

@router.get("/nodes", response_model=dict[str, list[TopologyNode]])
def get_nodes(db: Session = Depends(get_db)):
    nodes = db.query(Node).all()
    
    routers = [n for n in nodes if "router" in (n.device_type or "").lower()]
    switches = [n for n in nodes if "switch" in (n.device_type or "").lower()]
    hosts = []  # À compléter selon votre logique métier

    return {
        "Routers": [
            TopologyNode(id=n.id, ip_address=n.ip_address, hostname=n.hostname or "", device_type=n.device_type or "")
            for n in routers
        ],
        "Switches": [
            TopologyNode(id=n.id, ip_address=n.ip_address, hostname=n.hostname or "", device_type=n.device_type or "")
            for n in switches
        ],
        "Hosts": hosts
    }

@router.get("/node/{id}/interfaces", response_model=list[InterfaceSchema])
def get_node_interfaces(id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return [
        InterfaceSchema(
            id=i.id,
            name=i.name,
            description=i.description,
            mode=i.mode,
            vlan_id=i.vlan_id,
            allowed_vlans=i.allowed_vlans
        ) for i in node.interfaces
    ]
