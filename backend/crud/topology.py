from sqlalchemy import select
from sqlalchemy.orm import joinedload
from backend.db import SessionLocal
from backend.db.models import Node, Interface, Link

class DB:
    """
    DB class
    """

    def __init__(self):
        """
        Constructor of DB class
        """

    def topology_from_db(self):
        with SessionLocal() as session:
            nodes = session.scalars(select(Node)).all()
            links = session.scalars(select(Link)).all()
        return {"nodes": nodes, "links": links}
    
    def get_nodes(self):
        with SessionLocal() as session:
            nodes = session.execute(select(Node)).all()
        
        return nodes
    
    def get_node_interfaces(self, id):
        with SessionLocal() as session:
            return session.scalars(select(Node).options(joinedload(Node.interfaces)).where(Node.id == id)).first()

    def get_node_by_ip(self, ip: str):
        with SessionLocal() as session:
            return session.query(Node).filter(Node.ip_address == ip).first()

    def update_interface(self, id: int, update_data: dict):
        with SessionLocal() as session:
            iface = session.get(Interface, id)
            if not iface:
                return None
            
            for key, value in update_data.items():
                if hasattr(iface, key):
                    setattr(iface, key, value)
                    
            session.commit()
            session.refresh(iface)
            return {
                "id": iface.id,
                "name": iface.name,
                "description": iface.description,
                "mode": iface.mode,
                "vlan_id": iface.vlan_id,
                "allowed_vlans": iface.allowed_vlans
            }

    def upsert_discovered_nodes(self, nodes_data: dict, edges_data: list = None) -> list[dict]:
        nodes_created = []
        if edges_data is None:
            edges_data = []
            
        with SessionLocal() as session:
            node_map = {}
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
                
                node_map[ip] = node.id

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
                        
                for phys_iface in data.get("interfaces", []):
                    iface = session.query(Interface).filter(
                        Interface.node_id == node.id,
                        Interface.name == phys_iface.get("interface")
                    ).first()
                    
                    if not iface:
                        iface = Interface(
                            node_id=node.id,
                            name=phys_iface.get("interface", "unknown"),
                            description=phys_iface.get("description", ""),
                            mode=phys_iface.get("mode", "access"),
                            vlan_id=int(phys_iface.get("vlan", 1)) if phys_iface.get("vlan") and phys_iface.get("vlan").isdigit() else None
                        )
                        session.add(iface)
                
                session.commit()

                nodes_created.append({
                    "id": node.id,
                    "ip_address": ip,
                    "hostname": data.get("hostname"),
                    "device_type": data.get("device_type")
                })
                
            for edge in edges_data:
                source_id = node_map.get(edge.get("source_ip"))
                target_id = None
                
                if edge.get("target_ip"):
                    target_id = node_map.get(edge.get("target_ip"))
                elif edge.get("target_hostname"):
                    # Fallback to hostname if IP is unknown
                    target_node = session.query(Node).filter(Node.hostname == edge.get("target_hostname")).first()
                    if target_node:
                        target_id = target_node.id
                        
                if source_id and target_id:
                    link = session.query(Link).filter(
                        ((Link.source_id == source_id) & (Link.target_id == target_id)) |
                        ((Link.source_id == target_id) & (Link.target_id == source_id))
                    ).first()
                    
                    if not link:
                        link = Link(
                            source_id=source_id,
                            target_id=target_id,
                            source_interface=edge.get("source_port"),
                            target_interface=edge.get("target_port")
                        )
                        session.add(link)
            session.commit()
            
        return nodes_created

    def reset_and_save_topology(self, data) -> None:
        with SessionLocal() as session:
            # Clear all data
            session.query(Link).delete()
            session.query(Interface).delete()
            session.query(Node).delete()
            session.commit()

            # Insert Nodes and Interfaces
            node_map = {}
            node_interfaces = {}
            for n in data.nodes:
                node = Node(
                    ip_address=n.ip,
                    hostname=n.label,
                    device_type=n.type,
                    vendor="simulated"
                )
                session.add(node)
                session.commit()
                session.refresh(node)
                node_map[n.ip] = node.id
                node_interfaces[n.ip] = []

                for i, iface in enumerate(n.interfaces):
                    interface = Interface(
                        node_id=node.id,
                        name=iface.name,
                        description=iface.description or "",
                        mode=iface.mode or "access",
                        vlan_id=iface.vlan_id,
                        is_protected=False
                    )
                    session.add(interface)
                    node_interfaces[n.ip].append(iface.name)
            session.commit()

            # Insert Links
            for l in data.links:
                source_id = node_map.get(l.source_ip)
                if source_id:
                    s_ifaces = node_interfaces.get(l.source_ip, [])
                    t_ifaces = node_interfaces.get(l.target_ip, [])
                    s_iface_name = s_ifaces.pop(0) if s_ifaces else "auto"
                    t_iface_name = t_ifaces.pop(0) if t_ifaces else "auto"

                    link = Link(
                        source_id=source_id,
                        target_ip=l.target_ip,
                        source_interface=s_iface_name,
                        target_interface=t_iface_name
                    )
                    session.add(link)
            session.commit()