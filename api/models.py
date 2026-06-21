from pydantic import BaseModel
from typing import Optional, List

# --- Pydantic Models ---
class PortConfigSchema(BaseModel):
    ipv4: str = ""
    ipv6: str = ""
    mask: str = "255.255.255.0"
    gateway: str = ""
    vlan: str = "1"
    interface_name: str = ""
    mode: str = "access"
    portfast: bool = False
    allowed_vlans: str = ""
    description: str = ""
    voice_vlan: str = ""

class EdgeSchema(BaseModel):
    source: str
    target: str
    portId: str
    config: PortConfigSchema

class NodeSchema(BaseModel):
    id: str
    label: str
    link_count: int
    color: str
    device_type: str = "cisco_ios"
    mgmt_ip: str = ""
    ssh_username: str = ""
    stp_mode: str = ""
    stp_root_vlan: str = ""
    routes_json: str = "[]"

class NetworkSchema(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]

# --- SQLAlchemy Models ---
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import create_engine, String, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import sessionmaker

# Force MySQL connection
engine = create_engine("mysql+pymysql://root:test@localhost:3306/test", pool_pre_ping=True)
print("Successfully connected to MySQL database.")

class Base(DeclarativeBase):
    pass

class DBNode(Base):
    __tablename__ = "nodes"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    label: Mapped[str] = mapped_column(String(50))
    link_count: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str] = mapped_column(String(30), default="#3498db")
    
    # SSH Discovery Fields
    device_type: Mapped[str] = mapped_column(String(50), default="cisco_ios")
    mgmt_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ssh_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ssh_password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Configurations
    running_config_active: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    running_config_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # New Backend Capabilities
    stp_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    stp_root_vlan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    routes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status: pending, completed, failed
    discovery_status: Mapped[str] = mapped_column(String(20), default="pending")
    
    vlans: Mapped[List["DBVlan"]] = relationship(back_populates="node", cascade="all, delete-orphan")

class DBEdge(Base):
    __tablename__ = "edges"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"))
    port_id: Mapped[str] = mapped_column(String(50))
    
    config: Mapped["DBPortConfig"] = relationship(back_populates="edge", cascade="all, delete-orphan")

class DBPortConfig(Base):
    __tablename__ = "port_configs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[int] = mapped_column(ForeignKey("edges.id"))
    
    # App / Draft Config
    ipv4: Mapped[str] = mapped_column(String(50), default="")
    ipv6: Mapped[str] = mapped_column(String(50), default="")
    mask: Mapped[str] = mapped_column(String(50), default="255.255.255.0")
    gateway: Mapped[str] = mapped_column(String(50), default="")
    vlan: Mapped[str] = mapped_column(String(50), default="1")
    interface_name: Mapped[str] = mapped_column(String(50), default="")
    mode: Mapped[str] = mapped_column(String(20), default="access")
    portfast: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_vlans: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(String(200), default="")
    voice_vlan: Mapped[str] = mapped_column(String(50), default="")
    
    # Active / Physical Config
    active_ipv4: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_ipv6: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_mask: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_gateway: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_vlan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_interface_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    active_portfast: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    active_trunk_vlans: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    edge: Mapped["DBEdge"] = relationship(back_populates="config")

class DBVlan(Base):
    __tablename__ = "vlans"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"))
    vlan_id: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    node: Mapped["DBNode"] = relationship(back_populates="vlans")

class DBUser(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    settings: Mapped["DBUserSettings"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    node_colors: Mapped[List["DBNodeColor"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class DBToken(Base):
    __tablename__ = "tokens"
    token: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

class DBUserSettings(Base):
    __tablename__ = "user_settings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    bg_color: Mapped[str] = mapped_column(String(30), default="#1e1e1e")
    default_node_color: Mapped[str] = mapped_column(String(30), default="#ccc")
    router_color: Mapped[str] = mapped_column(String(30), default="#3498db")
    switch_color: Mapped[str] = mapped_column(String(30), default="#2ecc71")
    host_color: Mapped[str] = mapped_column(String(30), default="#9b59b6")
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    
    user: Mapped["DBUser"] = relationship(back_populates="settings")

class DBNodeColor(Base):
    __tablename__ = "node_colors"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"))
    color: Mapped[str] = mapped_column(String(30))
    
    user: Mapped["DBUser"] = relationship(back_populates="node_colors")

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(engine, autoflush=False)