from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Boolean,
)
from backend.db import Base, engine
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime


class TimestampMixin:
    created_at = Mapped[str] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = Mapped[str] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base, TimestampMixin):
    __tablename__ = "User"

    id = Mapped[int] = mapped_column(primary_key=True, index=True)
    username =  Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password =  Mapped[int] = mapped_column(String(128), nullable=False)
    is_admin = Mapped[bool] = mapped_column(Boolean, default=False)

class Node(Base, TimestampMixin):
    __tablename__ = "nodes"

    id = Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address = Mapped[str] = mapped_column(String(45), unique=True, nullable=False)  # IPv4/IPv6
    hostname = Mapped[str] = mapped_column(String(100))
    device_type = Mapped[str] = mapped_column(String(50))  # e.g., "cisco_ios", "arista_eos"
    vendor = Mapped[str] = mapped_column(String(50))

    interfaces = relationship("Interface", back_populates="node", cascade="all, delete-orphan")
    links = relationship("Link", foreign_keys="[Link.source_id]", back_populates="source")

class Interface(Base):
    __tablename__ = "interfaces"

    id = Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    node_id = Mapped[int] = mapped_column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    name = Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Gi0/1"
    description = Mapped[str] = mapped_column(String(255))
    mode = Mapped[str] = mapped_column(String(20))  # "access", "trunk"
    vlan_id = Mapped[int] = mapped_column(Integer, nullable=True)
    allowed_vlans = Mapped[str] = mapped_column(Text, nullable=True)  # JSON list or comma-separated
    is_protected = Mapped[bool] = mapped_column(Boolean, default=False)

    node = relationship("Node", back_populates="interfaces")

class Link(Base):
    __tablename__ = "links"

    id = Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id = Mapped[int] = mapped_column(Integer, ForeignKey("nodes.id"), nullable=False)
    target_ip = Mapped[str] = mapped_column(String(45), nullable=False)  # IP du nœud distant
    source_interface = Mapped[str] = mapped_column(String(100))
    target_interface = Mapped[str] = mapped_column(String(100))

    source = relationship("Node", back_populates="links")

Base.metadata.create_all(engine)