from sqlalchemy import select
from backend.db import SessionLocal
from backend.db.models import Node, Interface

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

    def get_node_by_ip(self, ip: str):
        with SessionLocal() as session:
            return session.query(Node).filter(Node.ip_address == ip).first()

    def upsert_discovered_nodes(self, nodes_data: dict) -> list[dict]:
        nodes_created = []
        with SessionLocal() as session:
            for ip, data in nodes_data.items():
                node = session.query(Node).filter(Node.ip_address == ip).first()
                if not node:
                    node = Node(
                        ip_address=ip,
                        hostname=data.get("hostname"),
                        device_type=data.get("device_type")
                    )
                    session.add(node)
                    session.commit()
                    session.refresh(node)
                else:
                    node.hostname = data.get("hostname")
                    node.device_type = data.get("device_type")
                    session.commit()

                for vlan in data.get("vlans", []):
                    iface = session.query(Interface).filter(
                        Interface.node_id == node.id, 
                        Interface.vlan_id == int(vlan["vlan_id"])
                    ).first()
                    
                    if not iface:
                        iface = Interface(
                            node_id=node.id,
                            name=f"VLAN{vlan['vlan_id']}",
                            description=f"VLAN {vlan['name']}",
                            mode="access",
                            vlan_id=int(vlan["vlan_id"])
                        )
                        session.add(iface)
                
                session.commit()

                nodes_created.append({
                    "id": node.id,
                    "ip_address": ip,
                    "hostname": data.get("hostname"),
                    "device_type": data.get("device_type")
                })
        return nodes_created