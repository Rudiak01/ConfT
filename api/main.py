import logging
import os
import re
import uvicorn
from typing import Annotated, List
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .models import Token, ModelUser
from .routers import users, deploy, discovery, topology
from .auth import get_current_user
from .tools import (
    get_admin_account,
    add_admin_account,
    token,
)

APP_NAME = os.environ.get("APP_NAME", "ConfT")
EXPOSE_PORT = os.environ.get("EXPOSE_PORT", 8000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if get_admin_account() is False:
        dataModel = {
            "first_name": "administrateur",
            "email": os.environ.get("SOCIETY_ADMIN_EMAIL"),
            "login": "admin",
            "password": "admin123",
            "role": "admin",
        }
        add_admin_account(ModelUser(**dataModel))
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(deploy.router)
app.include_router(discovery.router)
app.include_router(topology.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GetToken = Annotated[ModelUser, Depends(get_current_user)]


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/token")
async def _login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """
    return the token of the user
    """
    return token(form_data)


if __name__ == "__main__":

    log_config = uvicorn.config.LOGGING_CONFIG

    log_config["formatters"]["access"]["fmt"] = (
        "%(asctime)s | %(levelname)s | "
        "trace_id=%(otelTraceID)s span_id=%(otelSpanID)s service=%(otelServiceName)s | "
        "%(message)s"
    )

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=log_config,
        reload=bool(os.environ.get("IS_DEV", "False"))
    )
