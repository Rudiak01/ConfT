from fastapi import FastAPI

from models import node
from db import add, get_all
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/add")
def _add(node: node):
    return add(node)

@app.get("/get")
def read():
    return get_all()