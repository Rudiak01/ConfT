from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import Node, Interface
from ..models import TopologyNode, TopologyLink, TopologyGraph, InterfaceSchema

from ..tools import topology_db, get_nodes, get_node_interfaces

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
