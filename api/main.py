import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import discovery, topology


app = FastAPI()

app.include_router(discovery.router)
app.include_router(topology.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount("/", StaticFiles(directory="front", html=True), name="front")


if __name__ == "__main__":

    log_config = uvicorn.config.LOGGING_CONFIG

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=log_config,
        reload=bool(os.environ.get("IS_DEV", "False"))
    )
