# extract_config.py
import json
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from .ssh_connect import connect
from .config import SWITCH
from .vendor_syntax import VENDOR_SYNTAX

class DeviceUnreachableError(Exception):
    pass

class DeviceAuthenticationError(Exception):
    pass

def normalize_data(raw_data, template_mapping):
    """Transforme les clés TextFSM en clés universelles"""
    normalized_list = []
    for item in raw_data:
        normalized_item = {}
        for raw_key, universal_key in template_mapping.items():
            if raw_key in item:
                normalized_item[universal_key] = item[raw_key]
        if normalized_item:
            normalized_list.append(normalized_item)
    return normalized_list

def fetch_device_config(params):
    device_type = params.get("device_type", "cisco_ios")
    syntax = VENDOR_SYNTAX.get(device_type, VENDOR_SYNTAX["cisco_ios"])
    
    extracted_data = {}

    try:
        connection = connect(params)
        
        # BOUCLE DYNAMIQUE : On parcourt toutes les commandes de lecture prévues
        for feature, command in syntax["read"].items():
            print(f"Extraction de : {feature}...")
            
            # --- NOUVEAU : Bloc sécurisé pour chaque commande ---
            try:
                # 1. Gestion spécifique pour le running-config (pas de TextFSM)
                if feature == "running":
                    extracted_data["running_config"] = connection.send_command(command)
                    continue

                # 2. Tentative d'extraction TextFSM
                raw_output = connection.send_command(command, use_textfsm=True)

                # 3. Vérification si on a eu une erreur de syntaxe (Cisco renvoie souvent le texte d'erreur)
                if isinstance(raw_output, str) and "% Invalid input" in raw_output:
                    print(f"  Attention : Commande '{feature}' non supportée par ce modèle (Ignorée).")
                    continue

                # 4. Normalisation
                if isinstance(raw_output, list):
                    mapping = syntax["normalize_keys"].get(feature, {})
                    extracted_data[feature] = normalize_data(raw_output, mapping)
                else:
                    # Résultat vide (comme poe/port-channel)
                    extracted_data[feature] = []
            
            except Exception as e:
                print(f"Erreur lors de l'extraction de {feature}: {e}")
            
            # --- DEBUG ---
            #if feature == "vlans":
            #    print(f"\n--- DEBUG : Sortie brute de TextFSM pour 'vlans' ---")
            #    print(raw_output)
            #    print("----------------------------------------------------\n")
            # ----------------------------

        connection.disconnect()
        return extracted_data

    except NetmikoAuthenticationException as e:
        print(f"Erreur : Identifiants incorrects pour {params.get('host')}")
        raise DeviceAuthenticationError(f"Identifiants incorrects pour {params.get('host')}") from e
    except NetmikoTimeoutException as e:
        print(f"Erreur : Le switch {params.get('host')} est injoignable.")
        raise DeviceUnreachableError(f"Le switch {params.get('host')} est injoignable.") from e
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        raise e

def crawl_network(seed_ip, credentials):
    """
    Basic discovery that just fetches the seed node (no recursive crawling yet).
    """
    params = {
        "host": seed_ip,
        "device_type": credentials.get("device_type", "cisco_ios"),
        "username": credentials.get("username", ""),
        "password": credentials.get("password", "")
    }
    
    device_data = fetch_device_config(params)
    if not device_data:
        return None
        
    hostname = "Unknown"
    running_cfg = device_data.get("running_config", "")
    # Try to extract hostname from running config
    for line in running_cfg.splitlines():
        if line.startswith("hostname "):
            hostname = line.split(" ")[1]
            break
            
    vlans = []
    if "vlans" in device_data:
        for v in device_data["vlans"]:
            vlans.append({"vlan_id": v.get("vlan_id", ""), "name": v.get("name", "")})

    interfaces = device_data.get("interfaces", [])

    nodes = {
        seed_ip: {
            "hostname": hostname,
            "device_type": params["device_type"],
            "running_config": running_cfg,
            "vlans": vlans,
            "interfaces": interfaces
        }
    }
    
    edges = []
    # In vendor_syntax.py, "lldp" maps to "show cdp neighbors" and "cdp" normalizes the keys
    # But wait, TextFSM returns the raw key if there's no normalizer for "lldp".
    # Wait, the normalize_keys has "cdp", but the read command is "lldp". So it might not be normalized!
    # Let's just safely extract both possibilities
    neighbors = device_data.get("lldp", []) or device_data.get("cdp", [])
    
    for neighbor in neighbors:
        # Depending on if it was normalized or not
        remote_host = neighbor.get("neighbor_name") or neighbor.get("destination_host") or neighbor.get("neighbor")
        local_port = neighbor.get("local_port") or neighbor.get("local_interface")
        remote_port = neighbor.get("remote_port") or neighbor.get("neighbor_interface") or neighbor.get("port_id")
        
        if remote_host:
            edges.append({
                "source_ip": seed_ip,
                "target_hostname": remote_host,
                "source_port": local_port,
                "target_port": remote_port
            })
    
    return {"nodes": nodes, "edges": edges}

def main():
    print(f"Connexion au switch {SWITCH['host']} ({SWITCH['device_type']})...")
    data = fetch_device_config(SWITCH)
    
    if data:
        with open("back/current_state.json", "w") as f:
            json.dump(data, f, indent=4)
        print("\nSuccès : Extraction et normalisation terminées → current_state.json")

if __name__ == "__main__":
    main()