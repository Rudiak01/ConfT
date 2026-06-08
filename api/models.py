from pydantic import BaseModel
from typing import Optional, List

# --- Pydantic Models ---
class PortConfigSchema(BaseModel):
    ipv4: str = ""
    ipv6: str = ""
    mask: str = "255.255.255.0"
    gateway: str = ""
    vlan: str = "1"

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

class NetworkSchema(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]

# --- SQLAlchemy Models ---
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import create_engine, String, ForeignKey, Integer
from sqlalchemy.orm import sessionmaker

engine = create_engine("mysql+pymysql://root:test@10.0.2.2:3306/test", pool_pre_ping=True)

class Base(DeclarativeBase):
    pass

class DBNode(Base):
    __tablename__ = "nodes"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    label: Mapped[str] = mapped_column(String(50))
    link_count: Mapped[int]
    color: Mapped[str] = mapped_column(String(30))

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
    ipv4: Mapped[str] = mapped_column(String(50), default="")
    ipv6: Mapped[str] = mapped_column(String(50), default="")
    mask: Mapped[str] = mapped_column(String(50), default="255.255.255.0")
    gateway: Mapped[str] = mapped_column(String(50), default="")
    vlan: Mapped[str] = mapped_column(String(50), default="1")
    
    edge: Mapped["DBEdge"] = relationship(back_populates="config")

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(engine, autoflush=False)