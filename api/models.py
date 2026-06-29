from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from pydantic_extra_types import color as colorType

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
    must_change_password: bool


class TokenData(BaseModel):
    """
    Model for token data converted
    """
    rowid: int | None = None
    role: str | None = None
    action: str | None = None


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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None