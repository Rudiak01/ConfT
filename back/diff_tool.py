# diff_tool.py
import json


def compare_configs_in_memory(current_data, desired_data, target_ip):
    """
    Compare l'état actuel (current_data) vs la config désirée (desired_data)
    pour un device donné (target_ip).
    
    Retourne un dict avec les différences détaillées.
    
    Args:
        current_data: dict au format {"nodes": {"ip": {"hostname": ..., "vlans": [...], ...}}}
        desired_data: dict au format {"vlans": [...], "interfaces": [...], "routes": [...]}
        target_ip: IP du device à comparer
    """
    current_node = current_data.get("nodes", {}).get(target_ip, {})
    if not current_node:
        return {
            "target_ip": target_ip,
            "error": f"Device {target_ip} not found in current state",
            "vlans": [],
            "interfaces": []
        }

    current_vlans = {v["vlan_id"]: v["name"] for v in current_node.get("vlans", [])}
    
    result = {
        "target_ip": target_ip,
        "hostname": current_node.get("hostname", "Unknown"),
        "vlans": [],
        "interfaces": [],
        "routes": []
    }

    # 1. Analyse des VLANs
    for desired_vlan in desired_data.get("vlans", []):
        v_id = desired_vlan["vlan_id"]
        v_name = desired_vlan["name"]
        
        if v_id not in current_vlans:
            result["vlans"].append({
                "vlan_id": v_id,
                "name": v_name,
                "action": "create",
                "detail": f"VLAN {v_id} ({v_name}) à créer"
            })
        elif current_vlans[v_id] != v_name:
            result["vlans"].append({
                "vlan_id": v_id,
                "name": v_name,
                "current_name": current_vlans[v_id],
                "action": "rename",
                "detail": f"VLAN {v_id} : '{current_vlans[v_id]}' → '{v_name}'"
            })
        else:
            result["vlans"].append({
                "vlan_id": v_id,
                "name": v_name,
                "action": "ok",
                "detail": f"VLAN {v_id} ({v_name}) déjà conforme"
            })

    # 2. Analyse des interfaces (basique — comparaison par nom)
    # current_state ne stocke pas toujours les interfaces au même format,
    # donc on fait une comparaison basée sur la running_config si disponible
    running_config = current_node.get("running_config", "")
    for desired_iface in desired_data.get("interfaces", []):
        iface_name = desired_iface.get("interface", "")
        if iface_name in running_config:
            result["interfaces"].append({
                "interface": iface_name,
                "action": "update",
                "detail": f"Interface {iface_name} existe — vérifier la config détaillée"
            })
        else:
            result["interfaces"].append({
                "interface": iface_name,
                "action": "configure",
                "detail": f"Interface {iface_name} à configurer"
            })

    # 3. Analyse des routes
    for desired_route in desired_data.get("routes", []):
        network = desired_route.get("network", "")
        nexthop = desired_route.get("nexthop", "")
        if network in running_config and nexthop in running_config:
            result["routes"].append({
                "network": network,
                "nexthop": nexthop,
                "action": "ok",
                "detail": f"Route {network} → {nexthop} probablement présente"
            })
        else:
            result["routes"].append({
                "network": network,
                "nexthop": nexthop,
                "action": "create",
                "detail": f"Route {network} → {nexthop} à ajouter"
            })

    # Résumé
    result["summary"] = {
        "vlans_to_create": sum(1 for v in result["vlans"] if v["action"] == "create"),
        "vlans_to_rename": sum(1 for v in result["vlans"] if v["action"] == "rename"),
        "vlans_ok": sum(1 for v in result["vlans"] if v["action"] == "ok"),
        "interfaces_to_configure": sum(1 for i in result["interfaces"] if i["action"] == "configure"),
        "interfaces_to_update": sum(1 for i in result["interfaces"] if i["action"] == "update"),
        "routes_to_create": sum(1 for r in result["routes"] if r["action"] == "create"),
        "routes_ok": sum(1 for r in result["routes"] if r["action"] == "ok"),
    }

    return result


def compare_configs(current_state_file, desired_config_file, target_ip):
    """Version fichier (legacy) — charge les JSONs depuis le disque."""
    with open(current_state_file, "r") as f:
        current_full = json.load(f)
    with open(desired_config_file, "r") as f:
        desired = json.load(f)

    # Récupère l'état actuel du switch ciblé
    current_node = current_full["nodes"].get(target_ip, {})
    current_vlans = {v["vlan_id"]: v["name"] for v in current_node.get("vlans", [])}
    
    print(f"--- ANALYSE DES DIFFÉRENCES POUR {target_ip} ---")
    
    # 1. Analyse des VLANs
    print("\n[VLANs]")
    for dev_vlan in desired.get("vlans", []):
        v_id = dev_vlan["vlan_id"]
        v_name = dev_vlan["name"]
        
        if v_id not in current_vlans:
            print(f"➕ À CRÉER : VLAN {v_id} ({v_name})")
        elif current_vlans[v_id] != v_name:
            print(f"🔄 À RENOMMER : VLAN {v_id} s'appelle '{current_vlans[v_id]}', devrait être '{v_name}'")
        else:
            print(f"✅ OK : VLAN {v_id} ({v_name}) existe déjà.")

    # 2. Tu peux faire pareil pour les interfaces ici...
    # (Je garde l'exemple court pour la lisibilité)

if __name__ == "__main__":
    # Test avec ton IP de CoreRouter
    compare_configs("current_state.json", "desired_config.json", "10.0.0.1")