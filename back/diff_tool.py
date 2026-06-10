# diff_tool.py
import json

def compare_configs(current_state_file, desired_config_file, target_ip):
    # Charge les JSONs
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