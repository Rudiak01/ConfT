from fastapi import FastAPI, BackgroundTasks, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from models import Base, Device, Interface, Neighbor
from discovery.ssh_discovery import discover_device
from config import Config

import ipaddress
import threading
import queue
import logging
import sys
import os

# Ajouter le répertoire parent au path pour importer le module back/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from back.extract_config import fetch_device_config, crawl_network
from back.apply_config import apply_device_config, build_commands
from back.diff_tool import compare_configs_in_memory
from back.vendor_syntax import VENDOR_SYNTAX

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB setup
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables exist
Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---

class DiscoverRequest(BaseModel):
    start_ip: str = "192.168.1.1"
    end_ip: str = "192.168.1.254"
    mock: bool = False

class ConfigExtractRequest(BaseModel):
    host: str
    device_type: str = "cisco_ios"
    username: str
    password: str
    mock: bool = False

class ConfigApplyRequest(BaseModel):
    host: str
    device_type: str = "cisco_ios"
    username: str
    password: str
    config: Dict[str, Any]
    dry_run: bool = False
    mock: bool = False

class ConfigDiffRequest(BaseModel):
    target_ip: str
    desired_config: Dict[str, Any]
    current_state: Optional[Dict[str, Any]] = None
    host: Optional[str] = None
    device_type: str = "cisco_ios"
    username: Optional[str] = None
    password: Optional[str] = None
    mock: bool = False

class ConfigCrawlRequest(BaseModel):
    seed_ip: str
    device_type: str = "cisco_ios"
    username: str
    password: str
    mock: bool = False

# --- Functions ---

def device_to_dict(dev):
    return {
        "id": dev.id,
        "ip": dev.ip,
        "hostname": dev.hostname,
        "os_type": dev.os_type,
        "model": dev.model,
        "mac_address": dev.mac_address,
        "uptime": dev.uptime,
        "interfaces": [
            {
                "name": i.name,
                "ip_address": i.ip_address,
                "mac_address": i.mac_address,
                "status": i.status
            } for i in dev.interfaces
        ],
        "neighbors": [
            {
                "neighbor_ip": n.neighbor_ip,
                "neighbor_hostname": n.neighbor_hostname,
                "local_interface": n.local_interface,
                "remote_interface": n.remote_interface,
                "protocol": n.protocol
            } for n in dev.neighbors
        ]
    }

def discover_network(start_ip: str, end_ip: str):
    """Scan IP range via SSH (threaded)"""
    start = int(ipaddress.ip_address(start_ip))
    end = int(ipaddress.ip_address(end_ip))

    results_queue = queue.Queue()

    def worker(ip_int):
        ip_str = str(ipaddress.ip_address(ip_int))
        result = discover_device(ip_str)
        results_queue.put((ip_str, result))

    threads = []
    for ip_int in range(start, end + 1):
        t = threading.Thread(target=worker, args=(ip_int,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Store results
    db = SessionLocal()
    try:
        while not results_queue.empty():
            ip_str, data = results_queue.get()
            store_device(db, ip_str, data)
    finally:
        db.close()

def store_device(session: Session, ip: str, data: dict):
    if "error" in data:
        logger.warning(f"[Discovery] Skipping {ip}: {data['error']}")
        return

    try:
        dev = session.query(Device).filter_by(ip=ip).first()
        if not dev:
            dev = Device(
                ip=data["ip"],
                hostname=data.get("hostname", ""),
                os_type=data.get("os_type", "unknown"),
                model=data.get("model", ""),
                mac_address=data.get("mac_address", ""),
                uptime=data.get("uptime", "")
            )
            session.add(dev)
            session.flush()

        for iface in data.get("interfaces", []):
            existing = session.query(Interface).filter_by(
                device_id=dev.id, name=iface["name"]
            ).first()
            if not existing:
                existing = Interface(device_id=dev.id)
                session.add(existing)
            existing.name = iface["name"]
            existing.ip_address = iface.get("ip_address", "")
            existing.mac_address = iface.get("mac_address", "")
            existing.status = iface.get("status", "unknown")
        
        current_ifaces = {i["name"] for i in data.get("interfaces", [])}
        for iface in list(dev.interfaces):
            if iface.name not in current_ifaces:
                session.delete(iface)

        for nb in data.get("neighbors", []):
            existing_nb = session.query(Neighbor).filter_by(
                device_id=dev.id,
                neighbor_ip=nb["neighbor_ip"],
                local_interface=nb["local_interface"]
            ).first()
            if not existing_nb:
                existing_nb = Neighbor(device_id=dev.id)
                session.add(existing_nb)
            existing_nb.neighbor_hostname = nb.get("neighbor_hostname", "")
            existing_nb.remote_interface = nb.get("remote_interface", "")
            existing_nb.protocol = nb.get("protocol", "lldp")
        
        current_neighbors = {(nb["neighbor_ip"], nb["local_interface"]) for nb in data.get("neighbors", [])}
        for nb in list(dev.neighbors):
            if (nb.neighbor_ip, nb.local_interface) not in current_neighbors:
                session.delete(nb)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"[ERROR] Failed to store device {ip}: {e}")

def mock_discover_network():
    """Inject mock devices into DB"""
    db = SessionLocal()
    try:
        from mock_data import MOCK_DISCOVERY_DEVICES
        for data in MOCK_DISCOVERY_DEVICES:
            store_device(db, data["ip"], data)
    finally:
        db.close()

# --- Endpoints ---

@app.post("/api/discover", status_code=202)
def discover(req: DiscoverRequest, background_tasks: BackgroundTasks):
    try:
        ipaddress.ip_address(req.start_ip)
        ipaddress.ip_address(req.end_ip)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid IP address: {e}")

    if int(ipaddress.ip_address(req.start_ip)) > int(ipaddress.ip_address(req.end_ip)):
        raise HTTPException(status_code=400, detail="start_ip must be <= end_ip")

    if req.mock:
        background_tasks.add_task(mock_discover_network)
    else:
        background_tasks.add_task(discover_network, req.start_ip, req.end_ip)

    return {
        "status": "discovery started",
        "range": f"{req.start_ip} - {req.end_ip}"
    }

@app.get("/api/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    return [device_to_dict(dev) for dev in devices]

@app.get("/api/device/{ip}")
def get_device(ip: str, db: Session = Depends(get_db)):
    dev = db.query(Device).filter_by(ip=ip).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_to_dict(dev)

@app.get("/api/topology")
def get_topology(db: Session = Depends(get_db)):
    try:
        devices = db.query(Device).all()
        if not devices:
            return {"nodes": [], "links": []}

        node_map = {}
        nodes = []
        links = set()
        next_node_id = 1

        for dev in devices:
            node_id = f"n{next_node_id}"
            label = dev.hostname or dev.ip.split('.')[-1]
            node_type = "switch"
            if "router" in (dev.model or "").lower() or "router" in (dev.os_type or "").lower():
                node_type = "router"
            elif "host" in (dev.model or "").lower() or dev.os_type == "linux":
                if len(dev.interfaces) <= 2:
                    node_type = "host"

            node_map[dev.ip] = {
                "id": node_id,
                "ip": dev.ip,
                "label": label,
                "type": node_type,
                "interfaces": [i.name for i in dev.interfaces]
            }
            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type,
                "ip": dev.ip
            })
            next_node_id += 1

        for dev in devices:
            src_id = node_map[dev.ip]["id"]
            for neighbor in dev.neighbors:
                if neighbor.neighbor_ip not in node_map:
                    continue
                dst_id = node_map[neighbor.neighbor_ip]["id"]
                link_key = tuple(sorted([src_id, dst_id]))
                links.add(link_key)

        for dev in devices:
            if len(dev.interfaces) <= 2 and not dev.neighbors:
                for other_dev in devices:
                    if other_dev == dev or len(other_dev.interfaces) < 3:
                        continue
                    try:
                        dev_ip = ipaddress.ip_address(dev.ip.split('/')[0])
                        other_ip = ipaddress.ip_address(other_dev.ip.split('/')[0])
                        for iface in other_dev.interfaces:
                            if not iface.ip_address or '/' in iface.ip_address:
                                continue
                            try:
                                net = ipaddress.ip_network(f"{iface.ip_address}/24", strict=False)
                                if dev_ip in net:
                                    src_id = node_map[dev.ip]["id"]
                                    dst_id = node_map[other_dev.ip]["id"]
                                    link_key = tuple(sorted([src_id, dst_id]))
                                    links.add(link_key)
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue

        d3_links = [{"source": src, "target": dst} for src, dst in sorted(links)]

        return {"nodes": nodes, "links": d3_links}

    except Exception as e:
        logger.error(f"[Topology] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vendors")
def get_vendors():
    vendors = []
    for key, syntax in VENDOR_SYNTAX.items():
        vendors.append({
            "device_type": key,
            "read_commands": list(syntax.get("read", {}).keys()),
            "write_commands": list(syntax.get("write", {}).keys()),
        })
    return vendors

@app.post("/api/config/extract")
def extract_config(req: ConfigExtractRequest):
    params = {
        "host": req.host,
        "device_type": req.device_type,
        "username": req.username,
        "password": req.password
    }

    try:
        if req.mock:
            from mock_data import MOCK_EXTRACT_RESULT
            result = MOCK_EXTRACT_RESULT
        else:
            result = fetch_device_config(params)
            if result is None:
                raise HTTPException(status_code=502, detail=f"Impossible de se connecter à {req.host}")
        
        if "running_config" in result:
            config_lines = result["running_config"].split("\n")
            result["running_config_lines"] = len(config_lines)
            result["running_config_preview"] = "\n".join(config_lines[:50])
            if len(config_lines) > 50:
                result["running_config_preview"] += f"\n... ({len(config_lines) - 50} lignes supplémentaires)"
        
        return {
            "status": "success",
            "host": req.host,
            "device_type": req.device_type,
            "data": result
        }
    except Exception as e:
        logger.error(f"[Config Extract] Error for {req.host}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/apply")
def apply_config(req: ConfigApplyRequest):
    connection_params = {
        "host": req.host,
        "device_type": req.device_type,
        "username": req.username,
        "password": req.password
    }

    preview_commands = build_commands(req.config, req.device_type)

    if req.mock:
        return {
            "status": "dry_run" if req.dry_run else "success",
            "host": req.host,
            "device_type": req.device_type,
            "commands": preview_commands,
            "command_count": len(preview_commands),
            "output": f"Mock commands successfully {'previewed' if req.dry_run else 'executed'} on {req.host}." if not req.dry_run else None,
            "commands_sent": preview_commands if not req.dry_run else None
        }

    if req.dry_run:
        return {
            "status": "dry_run",
            "host": req.host,
            "device_type": req.device_type,
            "commands": preview_commands,
            "command_count": len(preview_commands)
        }

    try:
        success, output = apply_device_config(connection_params, req.config)
        if success:
            return {
                "status": "success",
                "host": req.host,
                "commands_sent": preview_commands,
                "output": output
            }
        else:
            raise HTTPException(status_code=500, detail=output)
    except Exception as e:
        logger.error(f"[Config Apply] Error for {req.host}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/diff")
def diff_config(req: ConfigDiffRequest):
    if req.current_state is not None:
        current_state = req.current_state
    elif req.mock:
        from mock_data import MOCK_CRAWL_RESULT
        current_state = MOCK_CRAWL_RESULT
    elif req.host and req.username and req.password:
        params = {
            "host": req.host,
            "device_type": req.device_type,
            "username": req.username,
            "password": req.password
        }
        try:
            crawl_result = crawl_network(req.host, params)
            if crawl_result is None:
                raise HTTPException(status_code=502, detail=f"Impossible de se connecter à {req.host}")
            current_state = crawl_result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction échouée: {e}")
    else:
        raise HTTPException(status_code=400, detail="Fournir 'current_state' ou les credentials SSH (host, username, password)")

    try:
        diff_result = compare_configs_in_memory(current_state, req.desired_config, req.target_ip)
        return {
            "status": "success",
            "diff": diff_result
        }
    except Exception as e:
        logger.error(f"[Config Diff] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/crawl")
def crawl_config(req: ConfigCrawlRequest):
    credentials = {
        "device_type": req.device_type,
        "username": req.username,
        "password": req.password
    }

    try:
        if req.mock:
            from mock_data import MOCK_CRAWL_RESULT
            result = MOCK_CRAWL_RESULT
        else:
            result = crawl_network(req.seed_ip, credentials)
            if result is None:
                raise HTTPException(status_code=502, detail=f"Impossible de crawler depuis {req.seed_ip}")
        
        return {
            "status": "success",
            "seed_ip": req.seed_ip,
            "nodes_found": len(result.get("nodes", {})),
            "edges_found": len(result.get("edges", [])),
            "data": result
        }
    except Exception as e:
        logger.error(f"[Config Crawl] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend at the root, after all API routes
front_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'front'))
app.mount("/", StaticFiles(directory=front_dir, html=True), name="static")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app:app", host='0.0.0.0', port=8000, reload=True)
