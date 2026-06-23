from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Device(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    ip = Column(String(45), unique=True, nullable=False)  # IPv4/IPv6
    hostname = Column(String(255))
    os_type = Column(String(100))  # e.g., "cisco_ios", "linux"
    model = Column(String(255))
    mac_address = Column(String(17))
    uptime = Column(String(100))
    interfaces = relationship("Interface", back_populates="device", cascade="all, delete-orphan")
    neighbors = relationship("Neighbor", back_populates="device", cascade="all, delete-orphan")

class Interface(Base):
    __tablename__ = 'interfaces'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'))
    name = Column(String(100))
    ip_address = Column(String(45))
    mac_address = Column(String(17))
    status = Column(String(20))  # up/down
    speed = Column(String(50))
    description = Column(Text)
    device = relationship("Device", back_populates="interfaces")

class Neighbor(Base):
    __tablename__ = 'neighbors'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'))
    neighbor_ip = Column(String(45))
    neighbor_hostname = Column(String(255))
    local_interface = Column(String(100))
    remote_interface = Column(String(100))
    protocol = Column(String(50))  # e.g., "lldp", "cdp"
    device = relationship("Device", back_populates="neighbors")
