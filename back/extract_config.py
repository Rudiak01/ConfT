# extract_config.py
import json
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from .ssh_connect import connect
from .config import SWITCH
from .vendor_syntax import VENDOR_SYNTAX

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
            
            if feature == "running":
                # La conf brute n'est jamais parsée par TextFSM
                extracted_data["running_config"] = connection.send_command(command)
                continue

            # Pour le reste, on utilise la magie TextFSM
            raw_output = connection.send_command(command, use_textfsm=True)
            
            # Si TextFSM réussit, il renvoie une liste de dictionnaires
            if isinstance(raw_output, list):
                mapping = syntax["normalize_keys"].get(feature, {})
                extracted_data[feature] = normalize_data(raw_output, mapping)
            else:
                # Si ntc-templates n'a pas de template pour cette commande/version
                print(f"  ⚠ Impossible de parser {feature} avec TextFSM (Template manquant).")
                extracted_data[feature] = [] # On laisse une liste vide pour le Front-End

        connection.disconnect()
        return extracted_data

    except NetmikoAuthenticationException:
        print(f"❌ Erreur : Identifiants incorrects pour {params.get('host')}")
        return None
    except NetmikoTimeoutException:
        print(f"❌ Erreur : Le switch {params.get('host')} est injoignable.")
        return None
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        return None

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
    if "vlan" in device_data:
        for v in device_data["vlan"]:
            vlans.append({"vlan_id": v.get("vlan_id", ""), "name": v.get("name", "")})

    nodes = {
        seed_ip: {
            "hostname": hostname,
            "device_type": params["device_type"],
            "running_config": running_cfg,
            "vlans": vlans
        }
    }
    edges = []
    
    return {"nodes": nodes, "edges": edges}

def main():
    print(f"Connexion au switch {SWITCH['host']} ({SWITCH['device_type']})...")
    data = fetch_device_config(SWITCH)
    
    if data:
        with open("current_state.json", "w") as f:
            json.dump(data, f, indent=4)
        print("\n✅ Extraction et normalisation terminées → current_state.json")

if __name__ == "__main__":
    main()