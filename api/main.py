from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from pathlib import Path
import json
import os
import sys

from .models import NetworkSchema, PortConfigSchema, DBNode, DBEdge, DBPortConfig, SessionLocal, DBVlan
from .db import get_db, get_network, update_edge_config

app = FastAPI()

# Get the base directory (ConfT)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Load .env file manually if it exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k] = v

from api.security import decrypt_password

def ensure_db_initialized(db: Session):
    # If DB is empty, initialize it using the JSON topology files
    if db.query(DBNode).count() == 0:
        nodes_file = BASE_DIR / "node_edge" / "outputnodes.json"
        edges_file = BASE_DIR / "node_edge" / "outputedges.json"
        
        if not nodes_file.exists() or not edges_file.exists():
            return
            
        with open(nodes_file, "r") as f:
            nodes_data = json.load(f)
            
        with open(edges_file, "r") as f:
            edges_data = json.load(f)
            
        db.query(DBPortConfig).delete()
        db.query(DBEdge).delete()
        db.query(DBNode).delete()
        
        for n in nodes_data:
            db.add(DBNode(id=n["id"], label=n.get("label", n["id"]), link_count=n.get("link_count", 0), color=n.get("color", "#7f7f7f"), discovery_status="pending"))
            
        db.commit()
        
        for i, e in enumerate(edges_data):
            port_id = f"port-{i + 1}"
            edge = DBEdge(source_id=e["source"], target_id=e["target"], port_id=port_id)
            db.add(edge)
            db.flush()
            db.add(DBPortConfig(
                edge_id=edge.id,
                ipv4=f"192.168.{i%10}.{i+1}",
                ipv6=f"fe80::{i*100}",
                vlan=str((i%20)+1)
            ))
            
        db.commit()

def run_dynamic_discovery(seed_data):
    db = SessionLocal()
    try:
        from back.extract_config import crawl_network
        from api.security import encrypt_password
        
        credentials = {
            "device_type": seed_data["device_type"],
            "username": seed_data["ssh_username"],
            "password": seed_data["ssh_password"]
        }
        
        # Clear existing
        db.query(DBPortConfig).delete()
        db.query(DBEdge).delete()
        db.query(DBVlan).delete()
        db.query(DBNode).delete()
        
        # Add a dummy pending node so UI shows progress
        seed_node = DBNode(
            id="seed", 
            label=f"Discovering from {seed_data['seed_ip']}...", 
            discovery_status="pending",
            link_count=0,
            color="#7f7f7f"
        )
        db.add(seed_node)
        db.commit()
        
        data = crawl_network(seed_data["seed_ip"], credentials)
        
        # Remove dummy node
        db.query(DBNode).delete()
        db.commit()
        
        if not data or not data["nodes"]:
            # If failed, recreate a dummy failed node
            seed_node = DBNode(
                id="seed", 
                label="Discovery Failed", 
                discovery_status="failed",
                link_count=0,
                color="#e74c3c"
            )
            db.add(seed_node)
            db.commit()
            return

        nodes = data["nodes"]
        edges = data["edges"]
        enc_pw = encrypt_password(seed_data["ssh_password"])
        
        for ip, n in nodes.items():
            # Basic sanity check
            node_id = f"node-{ip.replace('.', '-')}"
            db.add(DBNode(
                id=node_id,
                label=n["hostname"],
                device_type=n["device_type"],
                mgmt_ip=ip,
                ssh_username=seed_data["ssh_username"],
                ssh_password_encrypted=enc_pw,
                running_config_active=n["running_config"],
                running_config_draft=n["running_config"],
                discovery_status="completed",
                link_count=0,
                color="#3498db"
            ))
        db.commit()
        
        for ip, n in nodes.items():
            node_id = f"node-{ip.replace('.', '-')}"
            for v in n.get("vlans", []):
                db.add(DBVlan(node_id=node_id, vlan_id=v["vlan_id"], name=v["name"], is_active=True))
        db.commit()
        
        for i, e in enumerate(edges):
            source_id = f"node-{e['source_ip'].replace('.', '-')}"
            target_id = f"node-{e['target_ip'].replace('.', '-')}"
            
            # Make sure nodes exist
            if not db.query(DBNode).filter(DBNode.id == source_id).first() or \
               not db.query(DBNode).filter(DBNode.id == target_id).first():
                continue
                
            edge = DBEdge(source_id=source_id, target_id=target_id, port_id=f"port-{i+1}")
            db.add(edge)
            db.flush()
            
            db.add(DBPortConfig(
                edge_id=edge.id,
                interface_name=e["source_port"],
                active_interface_name=e["source_port"]
            ))
            
        db.commit()
        
    except Exception as e:
        print(f"Discovery error: {e}")
        seed_node = db.query(DBNode).filter(DBNode.id == "seed").first()
        if seed_node:
            seed_node.discovery_status = "failed"
            db.commit()

from api.assessment import get_full_assessment
from back.apply_config import apply_device_config

def discover_network_task():
    db = SessionLocal()
    try:
        from back.extract_config import fetch_device_config
        nodes = db.query(DBNode).filter(DBNode.discovery_status == "pending").all()
        for node in nodes:
            if "switch" not in node.device_type and "router" not in node.device_type and "cisco" not in node.device_type:
                node.discovery_status = "completed"
                db.commit()
                continue
                
            host = node.mgmt_ip or "192.168.1.2"
            username = node.ssh_username or "admin"
            password = decrypt_password(node.ssh_password_encrypted) or "azeAZE123-"
            
            params = {
                "device_type": getattr(node, "device_type", "cisco_ios"),
                "host": host,
                "username": username,
                "password": password
            }
            
            data = fetch_device_config(params)
            
            if data:
                node.running_config_active = data.get("running_config", "")
                if not node.running_config_draft:
                    node.running_config_draft = node.running_config_active
                
                for v in data.get("vlans", []):
                    existing = db.query(DBVlan).filter(DBVlan.node_id == node.id, DBVlan.vlan_id == v["vlan_id"]).first()
                    if not existing:
                        db.add(DBVlan(node_id=node.id, vlan_id=v["vlan_id"], name=v["name"], is_active=True))
                
                node.discovery_status = "completed"
            else:
                node.discovery_status = "failed"
                
            db.commit()
    finally:
        db.close()

def push_network_task():
    db = SessionLocal()
    try:
        nodes = db.query(DBNode).all()
        for node in nodes:
            if "switch" not in node.id and "router" not in node.id:
                continue
                
            host = node.mgmt_ip or "192.168.1.2"
            username = node.ssh_username or "admin"
            password = decrypt_password(node.ssh_password_encrypted) or "azeAZE123-"
            
            params = {
                "device_type": node.device_type,
                "host": host,
                "username": username,
                "password": password
            }
            
            config_data = {"vlans": [], "interfaces": []}
            
            for vlan in node.vlans:
                config_data["vlans"].append({"vlan_id": vlan.vlan_id, "name": vlan.name})
                
            edges = db.query(DBEdge).filter((DBEdge.source_id == node.id) | (DBEdge.target_id == node.id)).all()
            for edge in edges:
                if edge.config:
                    c = edge.config
                    if not c.interface_name:
                        continue
                    iface = {
                        "interface": c.interface_name,
                        "mode": c.mode,
                        "vlan": c.vlan,
                        "portfast": c.portfast
                    }
                    if c.allowed_vlans:
                        iface["allowed_vlans"] = c.allowed_vlans
                    config_data["interfaces"].append(iface)
                    
            if config_data["vlans"] or config_data["interfaces"]:
                node.discovery_status = "pushing"
                db.commit()
                
                success, output = apply_device_config(params, config_data)
                
                if success:
                    node.discovery_status = "pending"
                else:
                    node.discovery_status = "failed"
                db.commit()
                
    finally:
        db.close()
        
    # Trigger rediscovery to update Active configs
    discover_network_task()


@app.get("/api/network/assess")
def assess_network(db: Session = Depends(get_db)):
    return get_full_assessment(db)

@app.post("/api/network/push")
def push_network(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    assessment = get_full_assessment(db)
    has_errors = any(len(n["errors"]) > 0 for n in assessment)
    if has_errors:
        raise HTTPException(status_code=400, detail={"message": "Configuration errors found.", "assessment": assessment})
        
    background_tasks.add_task(push_network_task)
    return {"message": "Push started"}

@app.post("/api/network/discover")
def trigger_discovery(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    nodes = db.query(DBNode).all()
    for n in nodes:
        n.discovery_status = "pending"
    db.commit()
    background_tasks.add_task(discover_network_task)
    return {"status": "started"}

@app.get("/api/network/status")
def get_network_status(db: Session = Depends(get_db)):
    nodes = db.query(DBNode).all()
    if not nodes:
        return {"status": "pending", "pending": [], "failed": []}
    
    pending = [n.id for n in nodes if n.discovery_status == "pending"]
    failed = [n.id for n in nodes if n.discovery_status == "failed"]
    
    if pending:
        return {"status": "pending", "pending": pending, "failed": failed}
    return {"status": "completed", "failed": failed}

@app.get("/api/network", response_model=NetworkSchema)
def read_network(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # We no longer initialize from static JSON
    
    pending_nodes = db.query(DBNode).filter(DBNode.discovery_status == "pending").count()
    if pending_nodes > 0:
        # If there are pending nodes (e.g., from a push), we might want to do a simple task.
        # But for full discovery, we use /api/network/seed.
        pass
        
    return get_network(db)

class SeedSchema(BaseModel):
    seed_ip: str
    device_type: str = "cisco_ios"
    ssh_username: str
    ssh_password: str

@app.post("/api/network/seed")
def discover_from_seed(seed_data: SeedSchema, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Create or update a global config row (we can just pass it directly if we don't store it)
    db.query(DBPortConfig).delete()
    db.query(DBEdge).delete()
    db.query(DBVlan).delete()
    db.query(DBNode).delete()
    db.commit()
    
    # Python 3.10+ Pydantic
    data_dict = {"seed_ip": seed_data.seed_ip, "device_type": seed_data.device_type, "ssh_username": seed_data.ssh_username, "ssh_password": seed_data.ssh_password}
    background_tasks.add_task(run_dynamic_discovery, data_dict)
    return {"status": "started"}
class NodeUpdateSchema(BaseModel):
    device_type: str = "cisco_ios"
    mgmt_ip: str = ""
    ssh_username: str = ""
    ssh_password: str = ""

@app.post("/api/node/{node_id}")
def update_node(node_id: str, node_data: NodeUpdateSchema, db: Session = Depends(get_db)):
    from api.security import encrypt_password
    node = db.query(DBNode).filter(DBNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node.device_type = node_data.device_type
    node.mgmt_ip = node_data.mgmt_ip
    node.ssh_username = node_data.ssh_username
    if node_data.ssh_password:
        node.ssh_password_encrypted = encrypt_password(node_data.ssh_password)
        
    db.commit()
    return {"status": "success"}

@app.post("/api/config/{port_id}")
def update_config(port_id: str, config: PortConfigSchema, db: Session = Depends(get_db)):
    success = update_edge_config(db, port_id, config)
    if not success:
        raise HTTPException(status_code=404, detail="Edge/Port not found")
    return {"status": "success"}

@app.post("/api/init")
def init_db(db: Session = Depends(get_db)):
    nodes_file = BASE_DIR / "node_edge" / "outputnodes.json"
    edges_file = BASE_DIR / "node_edge" / "outputedges.json"
    
    if not nodes_file.exists() or not edges_file.exists():
        raise HTTPException(status_code=404, detail="JSON data files not found")
        
    with open(nodes_file, "r") as f:
        nodes_data = json.load(f)
        
    with open(edges_file, "r") as f:
        edges_data = json.load(f)
        
    # Clear existing tables
    db.query(DBPortConfig).delete()
    db.query(DBEdge).delete()
    db.query(DBNode).delete()
    
    # Add nodes
    for n in nodes_data:
        db.add(DBNode(id=n["id"], label=n.get("label", n["id"]), link_count=n.get("link_count", 0), color=n.get("color", "#7f7f7f")))
        
    db.commit()
    
    # Add edges
    for i, e in enumerate(edges_data):
        port_id = f"port-{i + 1}"
        edge = DBEdge(source_id=e["source"], target_id=e["target"], port_id=port_id)
        db.add(edge)
        # Mock default config to seed DB as previously done in JS
        db.flush()
        db.add(DBPortConfig(
            edge_id=edge.id,
            ipv4=f"192.168.{i%10}.{i+1}",
            ipv6=f"fe80::{i*100}",
            vlan=str((i%20)+1)
        ))
        
    db.commit()
    return {"status": "Database initialized with base topology"}

app.mount("/js", StaticFiles(directory=str(BASE_DIR / "js")), name="js")
app.mount("/node_edge", StaticFiles(directory=str(BASE_DIR / "node_edge")), name="node_edge")

@app.get("/{filename:path}")
def serve_root_files(filename: str):
    if filename.startswith("api/"):
        raise HTTPException(status_code=404)
    file_path = BASE_DIR / filename
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(BASE_DIR / "index.html")