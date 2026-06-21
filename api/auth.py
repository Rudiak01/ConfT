from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
import hashlib
import secrets
from typing import Optional, List, Dict

from .models import DBUser, DBToken, DBUserSettings, DBNodeColor
from .db import get_db

router = APIRouter()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_admin(db: Session):
    admin = db.query(DBUser).filter(DBUser.username == "admin").first()
    if not admin:
        admin = DBUser(username="admin", password_hash=hash_password("admin123"), is_admin=True)
        db.add(admin)
        db.commit()
        db.refresh(admin)
        settings = DBUserSettings(user_id=admin.id)
        db.add(settings)
        db.commit()

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    db_token = db.query(DBToken).filter(DBToken.token == token).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(DBUser).filter(DBUser.id == db_token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    ensure_admin(db)
    user = db.query(DBUser).filter(DBUser.username == req.username).first()
    if not user or user.password_hash != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = secrets.token_hex(32)
    db.add(DBToken(token=token, user_id=user.id))
    db.commit()
    return {"token": token, "username": user.username, "is_admin": user.is_admin}

@router.get("/api/auth/me")
def get_me(current_user: DBUser = Depends(get_current_user)):
    return {"username": current_user.username, "is_admin": current_user.is_admin}

@router.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        db.query(DBToken).filter(DBToken.token == token).delete()
        db.commit()
    return {"status": "success"}

class UserSettingsSchema(BaseModel):
    theme: str
    bg_color: str
    default_node_color: str
    router_color: str
    switch_color: str
    host_color: str

@router.get("/api/users/settings")
def get_settings(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = current_user.settings
    if not settings:
        settings = DBUserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        
    node_colors = {nc.node_id: nc.color for nc in current_user.node_colors}
    
    return {
        "theme": settings.theme,
        "bg_color": settings.bg_color,
        "default_node_color": settings.default_node_color,
        "router_color": settings.router_color,
        "switch_color": settings.switch_color,
        "host_color": settings.host_color,
        "node_colors": node_colors
    }

@router.put("/api/users/settings")
def update_settings(req: UserSettingsSchema, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = current_user.settings
    if not settings:
        settings = DBUserSettings(user_id=current_user.id)
        db.add(settings)
    
    settings.theme = req.theme
    settings.bg_color = req.bg_color
    settings.default_node_color = req.default_node_color
    settings.router_color = req.router_color
    settings.switch_color = req.switch_color
    settings.host_color = req.host_color
    db.commit()
    return {"status": "success"}

class NodeColorReq(BaseModel):
    color: str

@router.put("/api/nodes/{node_id}/color")
def update_node_color(node_id: str, req: NodeColorReq, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    nc = db.query(DBNodeColor).filter(DBNodeColor.user_id == current_user.id, DBNodeColor.node_id == node_id).first()
    if not nc:
        nc = DBNodeColor(user_id=current_user.id, node_id=node_id, color=req.color)
        db.add(nc)
    else:
        nc.color = req.color
    db.commit()
    return {"status": "success"}

class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool

@router.post("/api/users")
def create_user(req: UserCreate, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.query(DBUser).filter(DBUser.username == req.username).first():
        raise HTTPException(status_code=400, detail="User already exists")
        
    new_user = DBUser(username=req.username, password_hash=hash_password(req.password), is_admin=req.is_admin)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.add(DBUserSettings(user_id=new_user.id))
    db.commit()
    return {"status": "success"}

@router.get("/api/users")
def list_users(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    users = db.query(DBUser).all()
    return [{"id": u.id, "username": u.username, "is_admin": u.is_admin} for u in users]
