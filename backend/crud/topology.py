from sqlalchemy import select
from backend.db import SessionLocal
from backend.db.models import Node

class DB:
    """
    DB class
    """

    def __init__(self):
        """
        Constructor of DB class
        """

    def topology_from_db(self):
        with SessionLocal as session:
            res = session.execute(select(Node)).all()
        return res
    
    def get_nodes(self):
        with SessionLocal as session:
            nodes = session.execute(select(Node)).all()
        
        return nodes
    
    def get_node_interfaces(self, id):
        with SessionLocal as session:
            return session.execute(select(Node).where(Node.id == id)).first()