from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import SessionLocal, DBNode, DBEdge, DBPortConfig, NetworkSchema, NodeSchema, EdgeSchema, PortConfigSchema

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_network(db: Session) -> NetworkSchema:
    nodes = db.scalars(select(DBNode)).all()
    edges = db.scalars(select(DBEdge)).all()

    node_schemas = []
    for n in nodes:
        node_schemas.append(NodeSchema(
            id=n.id,
            label=n.label,
            link_count=n.link_count,
            color=n.color
        ))
    
    edge_schemas = []
    for e in edges:
        cfg = e.config if e.config else None
        if cfg:
            config_schema = PortConfigSchema(
                ipv4=cfg.ipv4,
                ipv6=cfg.ipv6,
                mask=cfg.mask,
                gateway=cfg.gateway,
                vlan=cfg.vlan
            )
        else:
            config_schema = PortConfigSchema()

        edge_schemas.append(EdgeSchema(
            source=e.source_id,
            target=e.target_id,
            portId=e.port_id,
            config=config_schema
        ))
    
    return NetworkSchema(nodes=node_schemas, edges=edge_schemas)

def update_edge_config(db: Session, port_id: str, new_config: PortConfigSchema):
    edge = db.scalar(select(DBEdge).where(DBEdge.port_id == port_id))
    if not edge:
        return False
    
    cfg = edge.config if edge.config else None
    if not cfg:
        cfg = DBPortConfig(edge_id=edge.id)
        db.add(cfg)
    
    cfg.ipv4 = new_config.ipv4
    cfg.ipv6 = new_config.ipv6
    cfg.mask = new_config.mask
    cfg.gateway = new_config.gateway
    cfg.vlan = new_config.vlan
    
    db.commit()
    return True