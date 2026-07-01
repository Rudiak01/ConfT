from typing import Annotated

from fastapi import HTTPException, Depends
from .auth import get_current_user
from .models import ModelUser


async def get_token(token: Annotated[ModelUser, Depends(get_current_user)]):
    if not token:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return token

from backend.db import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
