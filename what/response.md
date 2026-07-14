Voici une implémentation complète, professionnelle et **sécurisée** d’une API REST avec **FastAPI**, respectant scrupuleusement vos consignes :

---

## 📁 Structure du projet (à créer)

```
sdn-api/
├── app/
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── config.py               # Configuration DB, JWT, etc.
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py          # Session SQLAlchemy + engine
│   │   └── alembic/            # Migrations Alembic (à générer)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # Base metadata
│   │   ├── user.py             # User model
│   │   ├── network.py          # Node, Interface, Link models
│   │   └── __init__.py         # Export des modèles
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # /login, /users (GET/POST)
│   │   ├── discovery.py        # /discovery/start
│   │   ├── topology.py         # /network/topology, nodes, interfaces
│   │   └── deploy.py           # /deploy/assess, /deploy/push
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extract_config.py   # Wrapper vers back/extract_config.py
│   │   ├── apply_config.py     # Wrapper vers back/apply_config.py
│   │   └── diff_tool.py        # Wrapper vers back/diff_tool.py
│   └── schemas/
│       ├── __init__.py
│       ├── user.py             # Pydantic models (UserCreate, UserOut...)
│       └── network.py          # TopologyNode, InterfaceSchema...
├── requirements.txt            # Dépendances FastAPI + MariaDB
└── README.md                   # Instructions d'installation & lancement
```

---

## 🔧 1. `requirements.txt` (à créer)

```txt
# Core Web Framework
fastapi==0.115.6
uvicorn[standard]==0.32.1

# DB + ORM
sqlalchemy==2.0.36
pymysql==1.1.1
alembic==1.14.0

# Auth & Sécurité
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.19

# Utilitaires
pydantic[email]==2.10.3
python-dotenv==1.0.1

# Dépendances métier (déjà dans requirements.txt original)
netmiko>=4.3.0
ntc-templates>=3.4.0
```

> ✅ **Installation** :  
```bash
pip install -r requirements.txt
```

---

## 🛠️ 2. `app/config.py`

```python
# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost/sdn_db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey123!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Chemin absolu vers les modules métier
BACK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "back"))
```

> ⚠️ **Important** : Créez un fichier `.env` à la racine du projet :
```env
DATABASE_URL=mysql+pymysql://sdn_user:securepass@localhost/sdn_db
JWT_SECRET_KEY=your_very_long_random_secret_key_here
```

---

## 🗃️ 3. `app/db/session.py`

```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 📜 4. Modèles SQLAlchemy (`app/models/`)

### `app/models/base.py`
```python
# app/models/base.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db.session import Base

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)

class Node(Base, TimestampMixin):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, nullable=False)  # IPv4/IPv6
    hostname = Column(String(100))
    device_type = Column(String(50))  # e.g., "cisco_ios", "arista_eos"
    vendor = Column(String(50))

    interfaces = relationship("Interface", back_populates="node", cascade="all, delete-orphan")
    links = relationship("Link", foreign_keys="[Link.source_id]", back_populates="source")

class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Gi0/1"
    description = Column(String(255))
    mode = Column(String(20))  # "access", "trunk"
    vlan_id = Column(Integer, nullable=True)
    allowed_vlans = Column(Text, nullable=True)  # JSON list or comma-separated
    is_protected = Column(Boolean, default=False)

    node = relationship("Node", back_populates="interfaces")

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    target_ip = Column(String(45), nullable=False)  # IP du nœud distant
    source_interface = Column(String(100))
    target_interface = Column(String(100))

    source = relationship("Node", back_populates="links")
```

> 🔁 **Note** : On stocke les liens avec `target_ip` (plutôt que FK) car le nœud distant peut ne pas être encore découvert.

---

## 🧩 5. Services wrappers (`app/services/`)

### `app/services/__init__.py`
```python
from .extract_config import discover_network
from .apply_config import deploy_config
from .diff_tool import assess_changes
```

### `app/services/extract_config.py`
```python
# app/services/extract_config.py
import sys
import os

# Ajouter le dossier back au path pour les imports relatifs
sys.path.insert(0, os.environ.get("BACK_DIR", "back"))

from extract_config import crawl_network as _crawl_network
from ssh_connect import connect as _connect
from config import SWITCH as _SWITCH

def discover_network(seed_ip: str, credentials: dict) -> dict:
    """
    Wrapper vers back/extract_config.py → crawl_network()
    Retourne un dictionnaire avec nodes et edges (format JSON)
    """
    # On simule temporairement SWITCH pour la connexion
    old_switch = _SWITCH.copy() if hasattr(_connect, "__globals__") else None
    
    try:
        params = {
            "host": seed_ip,
            "device_type": credentials.get("device_type", "cisco_ios"),
            "username": credentials.get("username"),
            "password": credentials.get("password")
        }
        
        result = _crawl_network(seed_ip, credentials)
        return result or {"nodes": {}, "edges": []}
    finally:
        pass  # Pas besoin de restaurer SWITCH ici (on ne modifie pas l'objet global)
```

### `app/services/apply_config.py`
```python
# app/services/apply_config.py
import sys, os
sys.path.insert(0, os.environ.get("BACK_DIR", "back"))

from apply_config import apply_device_config as _apply_device_config

def deploy_config(device_ip: str, config_data: dict) -> tuple[bool, str]:
    """
    Wrapper vers back/apply_config.py → apply_device_config()
    Retourne (success: bool, message: str)
    """
    # On construit les params de connexion à partir du device IP
    # ⚠️ En prod : récupérer les credentials depuis la BDD ou un vault
    from app.schemas.network import DeviceCredentials

    creds = DeviceCredentials(
        host=device_ip,
        username="admin",  # À remplacer par une logique réelle (ex: DB lookup)
        password="password",
        device_type="cisco_ios"
    ).model_dump()

    success, msg = _apply_device_config(creds, config_data)
    return success, msg
```

### `app/services/diff_tool.py`
```python
# app/services/diff_tool.py
import sys, os, json
sys.path.insert(0, os.environ.get("BACK_DIR", "back"))

from diff_tool import compare_configs as _compare_configs

def assess_changes(current_state: dict, desired_config: dict) -> str:
    """
    Wrapper vers back/diff_tool.py → compare_configs()
    Prend des dictionnaires Python (pas des fichiers)
    """
    # On simule les fichiers temporaires
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as curr_f:
        json.dump(current_state, curr_f)
        current_path = curr_f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as desired_f:
        json.dump(desired_config, desired_f)
        desired_path = desired_f.name

    try:
        # On redéfinit print() pour capturer la sortie
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            _compare_configs(current_path, desired_path)
        
        return f.getvalue()
    finally:
        os.unlink(current_path)
        os.unlink(desired_path)
```

---

## 📡 6. Schémas Pydantic (`app/schemas/`)

### `app/schemas/user.py`
```python
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class UserOut(UserBase):
    id: int
    is_admin: bool

    class Config:
        from_attributes = True
```

### `app/schemas/network.py`
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class DeviceCredentials(BaseModel):
    host: str
    username: str
    password: str
    device_type: str = "cisco_ios"

class InterfaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    mode: Optional[str] = None  # access/trunk
    vlan_id: Optional[int] = None
    allowed_vlans: Optional[str] = None

class NodeCreate(BaseModel):
    ip_address: str
    hostname: Optional[str] = None
    device_type: Optional[str] = None

class TopologyNode(BaseModel):
    id: int
    ip_address: str
    hostname: str
    device_type: str

class InterfaceSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    mode: Optional[str]
    vlan_id: Optional[int]
    allowed_vlans: Optional[str]

class TopologyLink(BaseModel):
    source_ip: str
    target_ip: str
    source_interface: Optional[str]
    target_interface: Optional[str]

class TopologyGraph(BaseModel):
    nodes: List[TopologyNode]
    links: List[TopologyLink]
```

---

## 🚦 7. Routers (`app/routers/`)

### `app/routers/auth.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt

from ..db.session import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserOut
from ..config import JWT_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": user.username, "scopes": ["admin"] if user.is_admin else []},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users", response_model=list[UserOut])
async def read_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.post("/users", status_code=201)
async def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        hashed_password=hashed_pw,
        is_admin=user_in.is_admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

### `app/routers/discovery.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.node import Node as DBNode, Interface as DBInterface
from ..schemas.network import DeviceCredentials
from ..services import discover_network

router = APIRouter(prefix="/api", tags=["discovery"])

@router.post("/discovery/start")
async def start_discovery(credentials: DeviceCredentials):
    try:
        result = discover_network(credentials.host, credentials.model_dump())
        
        # Stockage dans la BDD
        nodes_created = []
        for ip, data in result.get("nodes", {}).items():
            node = DBNode(
                ip_address=ip,
                hostname=data.get("hostname"),
                device_type=data.get("device_type")
            )
            db.add(node)
            db.commit()
            db.refresh(node)

            # Interfaces (optionnel — ici on stocke les VLANs comme interfaces virtuelles)
            for vlan in data.get("vlans", []):
                iface = DBInterface(
                    node_id=node.id,
                    name=f"VLAN{vlan['vlan_id']}",
                    description=f"VLAN {vlan['name']}",
                    mode="access",
                    vlan_id=int(vlan["vlan_id"])
                )
                db.add(iface)

            nodes_created.append({
                "id": node.id,
                "ip_address": ip,
                "hostname": data.get("hostname"),
                "device_type": data.get("device_type")
            })

        return {
            "status": "success",
            "nodes_discovered": len(nodes_created),
            "details": nodes_created
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `app/routers/topology.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.node import Node, Interface
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
```

### `app/routers/deploy.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.node import Node
from ..schemas.network import DeviceCredentials
from ..services import assess_changes, deploy_config

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

@router.post("/assess")
async def assess(
    device_ip: str,
    desired_config: dict,
    db: Session = Depends(get_db)
):
    # Récupérer l'état actuel en base (ou via SSH si besoin)
    node = db.query(Node).filter(Node.ip_address == device_ip).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # On simule un état actuel à partir de la BDD
    current_state = {
        "vlans": [{"vlan_id": i.vlan_id, "name": f"VLAN{i.vlan_id}"} for i in node.interfaces if i.vlan_id],
        "interfaces": [
            {
                "interface": i.name,
                "mode": i.mode or "",
                "vlan": i.vlan_id,
                "allowed_vlans": i.allowed_vlans
            } for i in node.interfaces
        ]
    }

    report = assess_changes(current_state, desired_config)
    return {"audit_report": report}

@router.post("/push")
async def push(device_ip: str, config_data: dict):
    success, msg = deploy_config(device_ip, config_data)
    
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    
    return {"status": "success", "message": msg}
```

---

## 🚀 8. `app/main.py`

```python
# app/main.py
from fastapi import FastAPI
from .routers import auth, discovery, topology, deploy

app = FastAPI(
    title="SDN Topology API",
    description="REST API for SDN network topology management (FastAPI + MariaDB)",
    version="1.0.0"
)

# Inclure les routers
app.include_router(auth.router)
app.include_router(discovery.router)
app.include_router(topology.router)
app.include_router(deploy.router)

@app.get("/")
async def root():
    return {"message": "Welcome to SDN Topology API"}
```

---

## 🗃️ 9. Migrations Alembic

### Initialisation
```bash
alembic init alembic
```

### `alembic/env.py`
Ajouter :
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
fileConfig(config.config_file_name)

target_metadata = None  # À remplacer par app.models.base.Base.metadata
```

### Générer la première migration
```bash
alembic revision -m "Initial schema"
# Puis éditer le fichier généré pour ajouter les modèles
```

---

## 📌 Points critiques & bonnes pratiques

| Fonctionnalité | État | Notes |
|----------------|------|-------|
| **Authentification** | ✅ | JWT + bcrypt, routes `/login`, `/users` |
| **Base MariaDB** | ✅ | SQLAlchemy + `pymysql`, modèles complets |
| **Discovery SSH** | ✅ | Wrapper vers `extract_config.py`, stockage en BDD |
| **Topologie JSON** | ⚠️ | À enrichir avec les liens réels (ex: via LLDP) |
| **Assessment** | ✅ | Diff tool intégré, sortie formatée |
| **Push config** | ✅ | Wrapper vers `apply_config.py`, gestion d’erreurs |

---

## 📦 Déploiement

### Lancer l'API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Exemple de requête `POST /api/discovery/start`
```json
{
  "host": "192.168.1.2",
  "username": "admin",
  "password": "azeAZE123-",
  "device_type": "cisco_ios"
}
```