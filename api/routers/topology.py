from fastapi import APIRouter

from ..models import (
    TopologyNode,
    TopologyGraph,
    InterfaceSchema,
    TopologySyncRequest,
    InterfaceUpdate,
    TopologyLayoutUpdate,
    DeviceCredentials,
    NodeUpdate,
    InterfaceCreate
)

from ..tools import (
    topology_db,
    get_nodes,
    get_node_interfaces,
    sync_random_topology,
    update_layout,
    get_settings,
    update_settings,
    rediscover_network,
    deploy_topology_to_network,
    reset_database_and_app
)

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

@router.post("/node/{node_id}/interface")
def create_interface_route(node_id: int, data: InterfaceCreate):
    from api.tools import create_interface
    return create_interface(node_id, data)

@router.delete("/interface/{interface_id}")
def delete_interface_route(interface_id: int):
    from api.tools import delete_interface
    return delete_interface(interface_id)

@router.put("/node/{node_id}")
def update_node_route(node_id: int, data: NodeUpdate):
    from api.tools import update_node
    return update_node(node_id, data)

@router.put("/topology/layout")
def _update_layout(data: TopologyLayoutUpdate):
    return update_layout(data)

@router.get("/settings", response_model=DeviceCredentials)
def _get_settings():
    return get_settings()

@router.post("/settings")
def _update_settings(data: DeviceCredentials):
    return update_settings(data.model_dump())

@router.post("/rediscover")
def _rediscover_network():
    return rediscover_network()

@router.post("/deploy")
def _deploy_topology():
    return deploy_topology_to_network()

@router.post("/reset")
def _reset_app():
    return reset_database_and_app()

