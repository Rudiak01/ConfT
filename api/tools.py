from backend.crud.user import User
from backend.crud.topology import DB
from .models import TopologyNode, TopologyLink, InterfaceSchema, TopologySyncRequest, TopologyLayoutUpdate

from api.auth import (
    get_password_hash,
    is_admin,
    get_user_username,
    update_password,
    login,
)
from fastapi import HTTPException, status
from back.extract_config import crawl_network, DeviceUnreachableError, DeviceAuthenticationError
from back.apply_config import apply_device_config
def topology_db():
    _db = DB()
    data = _db.topology_from_db()
    
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    
    topology_nodes = []
    node_id_to_ip = {}
    for n in nodes:
        topology_nodes.append(TopologyNode(
            id=n.id,
            ip_address=n.ip_address,
            hostname=n.hostname or "",
            device_type=n.device_type or "",
            x=n.x,
            y=n.y,
            fx=n.fx,
            fy=n.fy,
            is_locked=n.is_locked
        ))
        node_id_to_ip[n.id] = n.ip_address
        
    topology_links = []
    for l in links:
        topology_links.append(TopologyLink(
            source_ip=node_id_to_ip.get(l.source_id, ""),
            target_ip=l.target_ip,
            source_interface=l.source_interface,
            target_interface=l.target_interface
        ))
        
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
            allowed_vlans=i.allowed_vlans
        ) for i in node.interfaces
    ]



def update_interface(interface_id: int, data):
    _db = DB()
    try:
        updated_iface = _db.update_interface(interface_id, data.model_dump(exclude_unset=True))
        if not updated_iface:
            raise HTTPException(status_code=404, detail="Interface not found")
        return {"status": "success", "message": "Interface updated"}
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

def token(form_data):
    """
    return the token of the user
    """
    access_token, operator_id = login(
        form_data.username, form_data.password
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# Users
def get_admin_account():
    """
    Return true if the user "admin" already exists
    """
    u = User()
    res = u.get_admin_account()
    return res


def get_users(token):
    """
    Return list of users
    """
    # New user
    u = User()
    res = u.get_users()
    return res


def get_user_by_token(token):
    """
    Get user by id
    """
    # New user
    u = User()
    print(type(token))
    print(token)
    print(token.model_dump())
    res = u.get_user(token.rowid)
    if res is None:
        # Token is valid but the user no longer exists (e.g. DB reset):
        # force the frontend to re-authenticate instead of crashing with a 500.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return res


def add_user(dataModel, token):
    """
    Add user to users table
    Return row id
    """
    data = dataModel.model_dump()
    hashed_password = get_password_hash(data["password"])
    data["password"] = hashed_password
    # New user
    u = User()
    if get_user_username(data["login"]) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    else:
        res = u.add_user(data)
        return res


def add_admin_account(dataModel):
    """
    Add user admin
    Return row id
    """
    data = dataModel.model_dump()
    hashed_password = get_password_hash(dataModel.password)
    data["password"] = hashed_password
    u = User()
    _ = data
    # Add user
    res = u.add_user(_)
    # Flush value
    _ = None
    del _
    # Return
    return res


def update_user(data, token, operator_id=None):
    """
    update user infos
    """
    # Dummy res ?
    res = None
    u = User()
    data = data.model_dump(exclude_none=True)
    if is_admin(token) and operator_id is not None:
        if "password" in data:
            hashed_password = get_password_hash(data["password"])
            data["password"] = hashed_password
        res = u.update_user(data, operator_id)
    else:
        if "password" in data:
            current_password = data.pop("current_password", None)
            update_password(current_password, token)
            hashed_password = get_password_hash(data["password"])
            data["password"] = hashed_password
        res = u.update_user(data, token.rowid)
    return res


def update_expired_password(password, token):
    """
    update user password if expired
    """
    data = {}
    u = User()
    hashed_password = get_password_hash(password)
    data["password"] = hashed_password
    res = u.update_user(data, token.rowid)
    u.update_user_password_change_date(token.rowid)
    return res


def user_role(UserRole, user_id, token):
    """
    Update user role to users table
    Return True or False
    """
    # New user
    u = User()

    if user_id == token.rowid and is_admin(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Can't self change role",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif user_id == token.rowid:
        u.update_user_role(user_id, UserRole.role)
        return True
    elif user_id is not None and is_admin(token):
        u.update_user_role(user_id, UserRole.role)
        return True
    else:
        return False


def delete_user(user_id, token):
    """
    Delete user to users table
    Return True or False
    """
    u = User()
    if user_id is None and is_admin(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden, can't self delete account if admin",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not is_admin(token):
        res = u.update_user_role(token.rowid, "inactive")
        return res
    else:
        return False


def run_discovery(credentials_host: str, credentials_data: dict):
    try:
        result = crawl_network(credentials_host, credentials_data)
        if not result:
            raise HTTPException(status_code=400, detail="Discovery failed")
        _db = DB()
        nodes_created = _db.upsert_discovered_nodes(result.get("nodes", {}), result.get("edges", []))

        return {
            "status": "success",
            "nodes_discovered": len(nodes_created),
            "details": nodes_created
        }
    except DeviceAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except DeviceUnreachableError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def push_config(device_ip: str, config_data: dict):
    db = DB()
    node = db.get_node_by_ip(device_ip)
    
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


def get_settings():
    from back.config import SWITCH
    return {
        "host": SWITCH.get("host", ""),
        "username": SWITCH.get("username", ""),
        "password": SWITCH.get("password", ""),
        "device_type": SWITCH.get("device_type", "cisco_ios")
    }


def update_settings(settings: dict):
    import json
    import os
    import importlib
    
    config_json_path = os.path.join("back", "config.json")
    data = {}
    if os.path.exists(config_json_path):
        try:
            with open(config_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    if "SWITCH" not in data:
        data["SWITCH"] = {}
        
    data["SWITCH"].update({
        "host": settings.get("host"),
        "username": settings.get("username"),
        "password": settings.get("password"),
        "device_type": settings.get("device_type", "cisco_ios")
    })
    
    with open(config_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    # Force reload of back.config to propagate settings changes
    import back.config
    importlib.reload(back.config)
    return {"status": "success", "message": "Paramètres mis à jour."}


def rediscover_network():
    from back.config import SWITCH
    seed_ip = SWITCH.get("host")
    if not seed_ip:
        raise HTTPException(status_code=400, detail="Aucune adresse IP de seed n'est configurée.")
        
    credentials = {
        "host": seed_ip,
        "username": SWITCH.get("username", ""),
        "password": SWITCH.get("password", ""),
        "device_type": SWITCH.get("device_type", "cisco_ios")
    }
    return run_discovery(seed_ip, credentials)


def deploy_topology_to_network():
    _db = DB()
    topology_data = _db.topology_from_db()
    nodes = topology_data.get("nodes", [])
    
    from back.config import SWITCH
    
    results = []
    for node in nodes:
        node_detail = _db.get_node_interfaces(node.id)
        if not node_detail:
            continue
            
        if node.vendor == "simulated":
            results.append({
                "hostname": node.hostname,
                "ip_address": node.ip_address,
                "success": True,
                "message": "Configuration simulée avec succès (nœud de démonstration)."
            })
            continue
            
        vlans = []
        interfaces = []
        for iface in node_detail.interfaces:
            # Check if it's a VLAN database entry (e.g. VLAN10)
            if iface.name.upper().startswith("VLAN") and iface.name[4:].isdigit():
                vlans.append({
                    "vlan_id": iface.vlan_id,
                    "name": iface.description or f"VLAN_{iface.vlan_id}"
                })
            else:
                interfaces.append({
                    "interface": iface.name,
                    "description": iface.description or "",
                    "mode": iface.mode,
                    "vlan": iface.vlan_id,
                    "allowed_vlans": iface.allowed_vlans
                })
                
        config_data = {
            "vlans": vlans,
            "interfaces": interfaces
        }
        
        connection_params = {
            "host": node.ip_address,
            "device_type": node.device_type or "cisco_ios",
            "username": SWITCH.get("username", "admin"),
            "password": SWITCH.get("password", "")
        }
        
        success, msg = apply_device_config(connection_params, config_data)
        results.append({
            "hostname": node.hostname,
            "ip_address": node.ip_address,
            "success": success,
            "message": msg
        })
        
    return {"status": "success", "results": results}


def reset_database_and_app():
    from backend.db import SessionLocal
    from backend.db.models import Node, Interface, Link, TableUser
    import os
    import importlib
    
    with SessionLocal() as session:
        # Clear topology tables
        session.query(Link).delete()
        session.query(Interface).delete()
        session.query(Node).delete()
        session.query(TableUser).delete()
        session.commit()
        
    # Re-create default admin user
    from api.models import ModelUser
    from api.tools import add_admin_account
    dataModel = {
        "first_name": "administrateur",
        "email": os.environ.get("SOCIETY_ADMIN_EMAIL") or "admin@example.com",
        "login": "admin",
        "password": "admin123",
        "role": "admin",
    }
    add_admin_account(ModelUser(**dataModel))
    
    # Remove custom settings override
    config_json_path = os.path.join("back", "config.json")
    if os.path.exists(config_json_path):
        try:
            os.remove(config_json_path)
        except Exception:
            pass
            
    # Reload config
    import back.config
    importlib.reload(back.config)
    
    return {"status": "success", "message": "Base de données supprimée et application réinitialisée."}


