from backend.crud.topology import DB
from .models import (
    TopologyNode,
    TopologyLink,
    InterfaceSchema,
    TopologySyncRequest,
    TopologyLayoutUpdate,
)

from fastapi import HTTPException
from back.extract_config import (
    crawl_network,
    DeviceUnreachableError,
    DeviceAuthenticationError,
)
from back.apply_config import apply_device_config
import back.config
from back.config import SWITCH
import os
import importlib
import json

def topology_db():
    _db = DB()
    data = _db.topology_from_db()

    nodes = data.get("nodes", [])
    links = data.get("links", [])

    topology_nodes = []
    node_id_to_ip = {}
    for n in nodes:
        topology_nodes.append(
            TopologyNode(
                id=n.id,
                ip_address=n.ip_address,
                hostname=n.hostname or "",
                device_type=n.device_type or "",
                x=n.x,
                y=n.y,
                fx=n.fx,
                fy=n.fy,
                is_locked=n.is_locked,
            )
        )
        node_id_to_ip[n.id] = n.ip_address

    topology_links = []
    for l in links:
        topology_links.append(
            TopologyLink(
                source_ip=node_id_to_ip.get(l.source_id, ""),
                target_ip=l.target_ip,
                source_interface=l.source_interface,
                target_interface=l.target_interface,
            )
        )

    return {"nodes": topology_nodes, "links": topology_links}


def sync_random_topology(data: TopologySyncRequest):
    _db = DB()
    try:
        _db.reset_and_save_topology(data)
        return {"status": "success", "message": "Topology synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def update_layout(data: TopologyLayoutUpdate):
    _db = DB()
    try:
        _db.update_node_layout(data.nodes)
        return {"status": "success", "message": "Layout updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_nodes():
    _db = DB()
    nodes = _db.get_nodes()
    routers = [n for n in nodes if "router" in (n.device_type or "").lower()]
    hosts = [
        TopologyNode(
            id=n.id,
            ip_address=n.ip_address,
            hostname=n.hostname or "",
            device_type=n.device_type or "",
        )
        for n in nodes if "host" in (n.device_type or "").lower()
    ]
    switches = []
    for n in nodes:
        dt_lower = (n.device_type or "").lower()
        if "router" in dt_lower or "host" in dt_lower or "external" in dt_lower:
            continue
        switches.append(n)

    return {
        "Routers": [
            TopologyNode(
                id=n.id,
                ip_address=n.ip_address,
                hostname=n.hostname or "",
                device_type=n.device_type or "",
            )
            for n in routers
        ],
        "Switches": [
            TopologyNode(
                id=n.id,
                ip_address=n.ip_address,
                hostname=n.hostname or "",
                device_type=n.device_type or "",
            )
            for n in switches
        ],
        "Hosts": hosts,
    }


def get_node_interfaces(id: int):
    _db = DB()
    node = _db.get_node_interfaces(id)

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return [
        InterfaceSchema(
            id=i.id,
            name=i.name,
            description=i.description,
            mode=i.mode,
            vlan_id=i.vlan_id,
            allowed_vlans=i.allowed_vlans,
            mac_address=i.mac_address,
        )
        for i in node.interfaces
    ]


def update_interface(interface_id: int, data):
    _db = DB()
    try:
        updated_iface = _db.update_interface(
            interface_id, data.model_dump(exclude_unset=True)
        )
        if not updated_iface:
            raise HTTPException(status_code=404, detail="Interface not found")
        return {"status": "success", "message": "Interface updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_interface(node_id: int, data):
    _db = DB()
    try:
        new_iface = _db.create_interface(
            node_id=node_id,
            name=data.name,
            mode=data.mode,
            vlan_id=data.vlan_id,
            description=data.description,
            allowed_vlans=data.allowed_vlans,
            mac_address=data.mac_address,
        )
        return {
            "status": "success",
            "message": "Interface created",
            "interface": new_iface,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_interface(interface_id: int):
    _db = DB()
    try:
        success = _db.delete_interface(interface_id)
        if not success:
            raise HTTPException(status_code=404, detail="Interface not found")
        return {"status": "success", "message": "Interface deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def update_node(node_id: int, data):
    _db = DB()
    try:
        updated_node = _db.update_node(node_id, data.model_dump(exclude_unset=True))
        if not updated_node:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "success", "message": "Node updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_discovery(credentials_host: str, credentials_data: dict):
    try:
        result = crawl_network(credentials_host, credentials_data)
        if not result:
            raise HTTPException(status_code=400, detail="Discovery failed")
        _db = DB()
        _db.clear_database()  # Reset the DB before inserting the newly discovered topology to avoid conflicts
        nodes_created = _db.upsert_discovered_nodes(
            result.get("nodes", {}), result.get("edges", [])
        )

        # Update connection settings to persist discovery credentials
        update_settings(credentials_data)

        return {
            "status": "success",
            "nodes_discovered": len(nodes_created),
            "details": nodes_created,
        }
    except DeviceAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except DeviceUnreachableError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_settings():

    return {
        "host": SWITCH.get("host", ""),
        "username": SWITCH.get("username", ""),
        "password": SWITCH.get("password", ""),
        "device_type": SWITCH.get("device_type", "cisco_ios"),
        "enable_vlan_feasibility": SWITCH.get("enable_vlan_feasibility", False),
    }


def update_settings(settings: dict):


    import back.config
    _dir = os.path.dirname(os.path.abspath(back.config.__file__))
    config_json_path = os.path.join(_dir, "config.json")
    data = {}
    if os.path.exists(config_json_path):
        try:
            with open(config_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    if "SWITCH" not in data:
        data["SWITCH"] = {}

    data["SWITCH"].update(
        {
            "host": settings.get("host"),
            "username": settings.get("username"),
            "password": settings.get("password"),
            "device_type": settings.get("device_type", "cisco_ios"),
        }
    )

    with open(config_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    # Force reload of back.config to propagate settings changes


    importlib.reload(back.config)
    return {"status": "success", "message": "Paramètres mis à jour."}


def rediscover_network():

    seed_ip = SWITCH.get("host")
    if not seed_ip:
        raise HTTPException(
            status_code=400, detail="Aucune adresse IP de seed n'est configurée."
        )

    credentials = {
        "host": seed_ip,
        "username": SWITCH.get("username", ""),
        "password": SWITCH.get("password", ""),
        "device_type": SWITCH.get("device_type", "cisco_ios"),
    }
    return run_discovery(seed_ip, credentials)


def deploy_topology_to_network():
    _db = DB()
    topology_data = _db.topology_from_db()
    nodes = topology_data.get("nodes", [])


    results = []
    for node in nodes:
        node_detail = _db.get_node_interfaces(node.id)
        if not node_detail:
            continue

        if node.vendor == "simulated":
            results.append(
                {
                    "hostname": node.hostname,
                    "ip_address": node.ip_address,
                    "success": True,
                    "message": "Configuration simulée avec succès (nœud de démonstration).",
                }
            )
            continue

        if node.device_type == "host" or node.vendor == "host" or (node.device_type or "").lower() == "host":
            # Skip host nodes since they are unmanaged endpoints and don't accept configuration
            continue

        vlans = []
        interfaces = []
        for iface in node_detail.interfaces:
            # Check if it's a VLAN database entry (e.g. VLAN10)
            if iface.name.upper().startswith("VLAN") and iface.name[4:].isdigit():
                vlans.append(
                    {
                        "vlan_id": iface.vlan_id,
                        "name": iface.description or f"VLAN_{iface.vlan_id}",
                    }
                )
            else:
                interfaces.append(
                    {
                        "interface": iface.name,
                        "description": iface.description or "",
                        "mode": iface.mode,
                        "vlan": iface.vlan_id,
                        "allowed_vlans": iface.allowed_vlans,
                    }
                )

        config_data = {"vlans": vlans, "interfaces": interfaces}

        connection_params = {
            "host": node.ip_address,
            "device_type": node.device_type or "cisco_ios",
            "username": SWITCH.get("username", "admin"),
            "password": SWITCH.get("password", ""),
        }

        success, msg = apply_device_config(connection_params, config_data)
        results.append(
            {
                "hostname": node.hostname,
                "ip_address": node.ip_address,
                "success": success,
                "message": msg,
            }
        )

    return {"status": "success", "results": results}


def reset_database_and_app():

    _db = DB()
    _db.clear_database()

    # Remove custom settings override
    config_json_path = os.path.join("back", "config.json")
    if os.path.exists(config_json_path):
        try:
            os.remove(config_json_path)
        except Exception:
            pass

    # Reload config

    importlib.reload(back.config)

    return {
        "status": "success",
        "message": "Base de données supprimée et application réinitialisée.",
    }
