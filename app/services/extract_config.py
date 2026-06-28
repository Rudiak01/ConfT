# app/services/extract_config.py
from back.extract_config import crawl_network as _crawl_network
from back.ssh_connect import connect as _connect
from back.config import SWITCH as _SWITCH

def discover_network(seed_ip: str, credentials: dict) -> dict:
    """
    Wrapper vers back/extract_config.py → crawl_network()
    Retourne un dictionnaire avec nodes et edges (format JSON)
    """
    # On simule temporairement SWITCH pour la connexion
    old_switch = _SWITCH.copy() if hasattr(_connect, "__globals__") else None
    
    try:
        params = {
            "host": seed_ip,
            "device_type": credentials.get("device_type", "cisco_ios"),
            "username": credentials.get("username"),
            "password": credentials.get("password")
        }
        
        result = _crawl_network(seed_ip, credentials)
        return result or {"nodes": {}, "edges": []}
    finally:
        pass  # Pas besoin de restaurer SWITCH ici (on ne modifie pas l'objet global)
