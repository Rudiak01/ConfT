from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db import Base, engine
from sqlalchemy import Integer, String, Boolean, ForeignKey, Text


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str] = mapped_column(
        String(45), unique=True, nullable=False
    )  # IPv4/IPv6
    hostname: Mapped[str] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(
        String(50)
    )  # e.g., "cisco_ios", "arista_eos"
    vendor: Mapped[str] = mapped_column(String(50))
    x: Mapped[float] = mapped_column(nullable=True)
    y: Mapped[float] = mapped_column(nullable=True)
    fx: Mapped[float] = mapped_column(nullable=True)
    fy: Mapped[float] = mapped_column(nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    interfaces = relationship(
        "Interface", back_populates="node", cascade="all, delete-orphan"
    )
    links = relationship(
        "Link", foreign_keys="[Link.source_id]", back_populates="source"
    )


class Interface(Base):
    __tablename__ = "interfaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Gi0/1"
    description: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(20))  # "access", "trunk"
    vlan_id: Mapped[int] = mapped_column(Integer, nullable=True)
    allowed_vlans: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON list or comma-separated
    mac_address: Mapped[str] = mapped_column(String(50), nullable=True)
    is_protected: Mapped[bool] = mapped_column(Boolean, default=False)

    node = relationship("Node", back_populates="interfaces")


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nodes.id"), nullable=False
    )
    target_ip: Mapped[str] = mapped_column(
        String(45), nullable=False
    )  # IP du nœud distant
    source_interface: Mapped[str] = mapped_column(String(100))
    target_interface: Mapped[str] = mapped_column(String(100))

    source = relationship("Node", back_populates="links")


Base.metadata.create_all(engine)

# Safely add mac_address column to interfaces if it is missing
from sqlalchemy import text
with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE interfaces ADD COLUMN mac_address VARCHAR(50) NULL;"))
    except Exception:
        pass

