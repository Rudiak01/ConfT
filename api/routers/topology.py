from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import Node, Interface
from ..models import TopologyNode, TopologyLink, TopologyGraph, InterfaceSchema, TopologySyncRequest, InterfaceUpdate, TopologyLayoutUpdate

from ..tools import topology_db, get_nodes, get_node_interfaces, sync_random_topology, update_layout

router = APIRouter(prefix="/db", tags=["topology"])

@router.get("/topology", response_model=TopologyGraph)
def _get_topology():
    """
    get the topology from the db
    """
    return topology_db()

@router.get("/nodes", response_model=dict[str, list[TopologyNode]])
def _get_nodes():
    return get_nodes()

@router.get("/node/{id}/interfaces", response_model=list[InterfaceSchema])
def _get_node_interfaces(id: int):
    return get_node_interfaces(id)

@router.post("/topology/random")
def _sync_random_topology(data: TopologySyncRequest):
    """
    Sync randomly generated topology with the database
    """
    return sync_random_topology(data)

@router.put("/interface/{interface_id}")
def update_interface_route(interface_id: int, data: InterfaceUpdate):
    from api.tools import update_interface
    return update_interface(interface_id, data)

@router.put("/topology/layout")
def _update_layout(data: TopologyLayoutUpdate):
    return update_layout(data)
