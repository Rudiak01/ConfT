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
