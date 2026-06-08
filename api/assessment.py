from .models import DBNode

def assess_network(db_session):
    """
    Assess the network configuration for security and best practice issues.
    Returns a dictionary of warnings and errors per node.
    """
    nodes = db_session.query(DBNode).all()
    assessment_results = []
    
    for node in nodes:
        node_issues = {
            "node_id": node.id,
            "label": node.label,
            "errors": [],
            "warnings": []
        }
        
        # Check global running config if available
        config = node.running_config_draft or node.running_config_active or ""
        
        if "transport input telnet" in config or ("line vty" in config and "transport input ssh" not in config):
            node_issues["warnings"].append("Telnet might be enabled or SSH is not explicitly enforced. Use SSH for secure management.")
            
        if "no service password-encryption" in config:
            node_issues["warnings"].append("Service password-encryption is disabled. Passwords may be visible in plain text.")
            
        # Check port configurations (Draft)
        for edge in getattr(node, "edges", []): # wait, edges are linked to nodes via source_id or target_id
            pass # We will query ports directly below
            
        assessment_results.append(node_issues)
        
    return assessment_results

def assess_node_ports(db_session, node_id: str):
    """
    Assess ports for a specific node.
    """
    from .models import DBEdge, DBPortConfig
    edges = db_session.query(DBEdge).filter((DBEdge.source_id == node_id) | (DBEdge.target_id == node_id)).all()
    
    errors = []
    warnings = []
    
    for edge in edges:
        config = edge.config
        if not config:
            continue
            
        port_name = config.interface_name or edge.port_id
            
        if config.mode == "trunk" and config.portfast:
            errors.append(f"Port {port_name}: Portfast should NOT be enabled on trunk ports.")
            
        if config.mode == "trunk" and not config.allowed_vlans:
            warnings.append(f"Port {port_name}: Trunk port allows all VLANs. Best practice is to restrict allowed VLANs.")
            
        if config.mode == "access" and config.allowed_vlans:
            warnings.append(f"Port {port_name}: Allowed VLANs is configured on an access port, which has no effect.")
            
    return {"errors": errors, "warnings": warnings}

def get_full_assessment(db_session):
    nodes_assessment = assess_network(db_session)
    for node_result in nodes_assessment:
        ports_assessment = assess_node_ports(db_session, node_result["node_id"])
        node_result["errors"].extend(ports_assessment["errors"])
        node_result["warnings"].extend(ports_assessment["warnings"])
        
    return nodes_assessment
