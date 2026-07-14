from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

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

class InterfaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[str] = None
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

class TopologyLink(BaseModel):
    source_ip: str
    target_ip: str
    source_interface: Optional[str]
    target_interface: Optional[str]

class TopologyGraph(BaseModel):
    nodes: List[TopologyNode]
    links: List[TopologyLink]


class ModelUser(BaseModel):
    """
    Model for user
    """
    first_name: str = Field(max_length=100)
    last_name: str = Field(None, max_length=100)
    email: str = Field(max_length=100)
    login: str = Field(max_length=50, min_length=1)
    password: str = Field(max_length=200, min_length=2)
    role: str | None = "user"


class UserUpdate(BaseModel):
    """
    Model for user update
    """
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=100)
    login: str | None = Field(None, max_length=50, min_length=1)
    password: str | None = Field(None, max_length=200, min_length=1)
    current_password: str | None = Field(None, max_length=200)


class UserRole(BaseModel):
    """
    Model for role update
    """
    role: str | None = "user"


class Token(BaseModel):
    """
    Model for token
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Model for token data converted
    """
    rowid: int | None = None
    role: str | None = None


class ModelResponseGetConnectedUser(BaseModel):
    """
    Model for connected user result
    """
    id: int
    first_name: str
    last_name: str | None
    email: str
    login: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str

class MockInterface(BaseModel):
    name: str
    description: Optional[str] = None
    mode: Optional[str] = None
    vlan_id: Optional[int] = None
    allowed_vlans: Optional[str] = None

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