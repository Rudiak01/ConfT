from backend.crud.user import User
from backend.crud.topology import DB
from models import TopologyNode, InterfaceSchema

from api.auth import (
    get_password_hash,
    is_admin,
    get_user_username,
    update_password,
    login,
)
from fastapi import HTTPException, status
from back.extract_config import crawl_network
from back.apply_config import apply_device_config
def topology_db():
    _db = DB()
    res = _db.topology_from_db()
    return res

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
        nodes_created = _db.upsert_discovered_nodes(result.get("nodes", {}))

        return {
            "status": "success",
            "nodes_discovered": len(nodes_created),
            "details": nodes_created
        }
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

