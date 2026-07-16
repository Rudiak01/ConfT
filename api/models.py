from pydantic import BaseModel
from typing import Optional, List


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
    mac_address: Optional[str] = None


class InterfaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[str] = None
    vlan_id: Optional[int] = None
    allowed_vlans: Optional[str] = None
    mac_address: Optional[str] = None


class TopologyNode(BaseModel):
    id: int
    ip_address: str
    hostname: str
    device_type: str
    x: Optional[float] = None
    y: Optional[float] = None
    fx: Optional[float] = None
    fy: Optional[float] = None
    is_locked: Optional[bool] = False


class InterfaceSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    mode: Optional[str]
    vlan_id: Optional[int]
    allowed_vlans: Optional[str]
    mac_address: Optional[str] = None


class TopologyLink(BaseModel):
    source_ip: str
    target_ip: str
    source_interface: Optional[str]
    target_interface: Optional[str]


class TopologyGraph(BaseModel):
    nodes: List[TopologyNode]
    links: List[TopologyLink]


class MockInterface(BaseModel):
    name: str
    description: Optional[str] = None
    mode: Optional[str] = None
    vlan_id: Optional[int] = None
    allowed_vlans: Optional[str] = None
    mac_address: Optional[str] = None



class MockNode(BaseModel):
    ip: str
    label: str
    type: str
    interfaces: List[MockInterface] = []


class MockLink(BaseModel):
    source_ip: str
    target_ip: str


class TopologySyncRequest(BaseModel):
    nodes: List[MockNode]
    links: List[MockLink]


class NodeLayoutUpdate(BaseModel):
    id: int
    x: Optional[float] = None
    y: Optional[float] = None
    fx: Optional[float] = None
    fy: Optional[float] = None
    is_locked: Optional[bool] = False


class TopologyLayoutUpdate(BaseModel):
    nodes: List[NodeLayoutUpdate]


class NodeUpdate(BaseModel):
    hostname: Optional[str] = None
