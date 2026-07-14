# diff_tool.py
import json
import os

def compare_configs(current_state_file, desired_config_file):
    # 1. Obtenir le chemin absolu
    base_dir = os.path.dirname(os.path.abspath(__file__))
    current_path = os.path.join(base_dir, current_state_file)
    desired_path = os.path.join(base_dir, desired_config_file)

    # 2. Charger les fichiers
    try:
        with open(current_path, "r", encoding="utf-8") as f:
            current_data = json.load(f)
        with open(desired_path, "r", encoding="utf-8") as f:
            desired_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Erreur : Impossible de trouver le fichier {e.filename}")
        return
    except json.JSONDecodeError:
        print("Erreur : Le format JSON est invalide.")
        return

    print("\nDIFFÉRENCES DE CONFIGURATION")
    
    # 1. ANALYSE DES VLANs
    print("\n[VLANs]")
    # Utilisation de .get() pour éviter le KeyError
    current_vlans = {
        str(v.get("vlan_id", "unknown")): v.get("name", "Unnamed_VLAN") 
        for v in current_data.get("vlans", []) 
        if v.get("vlan_id") # S'assure qu'il y a au moins un ID
    }
    
    for des_vlan in desired_data.get("vlans", []):
        # Sécurité sur le desired_config
        v_id = str(des_vlan.get("vlan_id", "unknown"))
        v_name = des_vlan.get("name", "Unnamed_VLAN")
        
        if v_id not in current_vlans:
            print(f"+ A CREER : VLAN {v_id} ({v_name})")
        elif current_vlans[v_id] != v_name:
            print(f"[RENOMMER] : VLAN {v_id} s'appelle '{current_vlans[v_id]}', devrait être '{v_name}'")
        else:
            print(f"OK : VLAN {v_id} ({v_name}) est déjà conforme.")

    # 2. ANALYSE DES INTERFACES
    print("\n[Interfaces]")
    # Sécurité sur le nom de l'interface
    current_interfaces = {
        i.get("interface", "unknown"): i 
        for i in current_data.get("interfaces", []) 
        if i.get("interface")
    }

    for des_iface in desired_data.get("interfaces", []):
        iface_name = des_iface.get("interface")
        
        if not iface_name:
            continue # Si l'interface n'a pas de nom dans le desired, on ignore

        if iface_name not in current_interfaces:
            print(f"INCONNUE : L'interface {iface_name} n'existe pas sur ce switch.")
            continue
            
        curr_iface = current_interfaces[iface_name]
        
        curr_mode = str(curr_iface.get("mode", "")).lower()
        des_mode = str(des_iface.get("mode", "")).lower()
        
        if "access" in curr_mode: curr_mode = "access"
        if "trunk" in curr_mode: curr_mode = "trunk"

        if curr_mode != des_mode:
            print(f"[MODIFIER] : {iface_name} est en mode '{curr_mode}', doit passer en '{des_mode}'")
            continue 
            
        if des_mode == "access":
            curr_vlan = str(curr_iface.get("vlan", "1"))
            des_vlan = str(des_iface.get("vlan", "1"))
            if curr_vlan != des_vlan:
                print(f"[MODIFIER] : {iface_name} (VLAN {curr_vlan} -> VLAN {des_vlan})")
            else:
                print(f"OK : {iface_name} (Access VLAN {des_vlan})")
                
        elif des_mode == "trunk" and "allowed_vlans" in des_iface:
            curr_allowed = str(curr_iface.get("allowed_vlans", curr_iface.get("trunk_vlans", "All")))
            des_allowed = str(des_iface.get("allowed_vlans", ""))
            if curr_allowed != des_allowed:
                print(f"[MODIFIER] : {iface_name} (Allowed '{curr_allowed}' -> '{des_allowed}')")
            else:
                print(f"OK : {iface_name} (Trunk Allowed {des_allowed})")

if __name__ == "__main__":
    compare_configs("current_state.json", "desired_config.json")