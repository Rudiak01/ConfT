from models import TableNode,engine, Session
from sqlalchemy import select, insert, values
import json

def add(data):
    """
    add a node to db
    """
    with Session() as session:
        id = session.execute(insert(TableNode).values(label=data.label,link_count=data.link_count,color=data.color))
        session.commit()
    return id

def get_all():
    with Session() as session:
        return session.scalar(select(TableNode))