
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db.session import Base, engine

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

Base.metadata.create_all(engine)