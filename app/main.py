# app/main.py
from fastapi import FastAPI
from .routers import auth, discovery, topology, deploy

app = FastAPI(
    title="SDN Topology API",
    description="REST API for SDN network topology management (FastAPI + MariaDB)",
    version="1.0.0"
)

# Inclure les routers
app.include_router(auth.router)
app.include_router(discovery.router)
app.include_router(topology.router)
app.include_router(deploy.router)

@app.get("/")
async def root():
    return {"message": "Welcome to SDN Topology API"}
