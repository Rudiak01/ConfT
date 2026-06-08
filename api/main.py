from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import json
import os

from .models import NetworkSchema, PortConfigSchema, DBNode, DBEdge, DBPortConfig, SessionLocal
from .db import get_db, get_network, update_edge_config

app = FastAPI()

# Get the base directory (ConfT)
BASE_DIR = Path(__file__).resolve().parent.parent

@app.get("/api/network", response_model=NetworkSchema)
def read_network(db: Session = Depends(get_db)):
    return get_network(db)

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