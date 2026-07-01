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
            "email": os.environ.get("SERIEMATRIX_SOCIETY_ADMIN_EMAIL"),
            "login": "admin",
            "password": os.environ.get("admin123"),
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

class StatusCodeFilter(logging.Filter):
    def filter(self, record):
        try:
            message = record.getMessage()

            # Extract HTTP status code
            match = re.search(r'" (\d{3})', message)
            if not match:
                return True

            status = int(match.group(1))

            if 100 <= status < 200:
                level = logging.DEBUG
                name = "DEBUG"
            elif 200 <= status < 400:
                level = logging.INFO
                name = "INFO"
            elif 400 <= status < 500:
                level = logging.WARNING
                name = "WARNING"
            else:  # 500+
                level = logging.ERROR
                name = "ERROR"

            record.levelno = level
            record.levelname = name

        except Exception:
            pass

        return True


class EndpointFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()

        if "/metrics" in message or "/health" in message:
            return False

        return True


if __name__ == "__main__":

    log_config = uvicorn.config.LOGGING_CONFIG

    log_config["formatters"]["access"]["fmt"] = (
        "%(asctime)s | %(levelname)s | "
        "trace_id=%(otelTraceID)s span_id=%(otelSpanID)s service=%(otelServiceName)s | "
        "%(message)s"
    )

    log_config["filters"] = {
        "endpoint_filter": {
            "()": EndpointFilter,
        },
        "status_code_filter": {
            "()": StatusCodeFilter,
        },
    }
    log_config["loggers"]["uvicorn.access"]["filters"] = ["endpoint_filter"]

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=log_config,
        reload=bool(os.environ.get("IS_DEV", "False"))
    )
