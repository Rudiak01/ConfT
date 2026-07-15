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
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # MOCK MODE
    if os.getenv("MOCK_NETWORK", "0") == "1":
        print("[MOCK] Crawling network in mock mode...")
        # Predefined 3-node mock topology
        nodes = {
            "192.168.1.13": {
                "hostname": "Core-Switch",
                "device_type": "cisco_ios",
                "running_config": "hostname Core-Switch\ninterface FastEthernet0/23\ninterface FastEthernet0/24",
                "vlans": [{"vlan_id": "10", "name": "PRODUCTION"}, {"vlan_id": "20", "name": "MANAGEMENT"}],
                "interfaces": [
                    {"interface": "FastEthernet0/23", "description": "Trunk to Dist-1", "mode": "trunk", "vlan": "1"},
                    {"interface": "FastEthernet0/24", "description": "Trunk to Dist-2", "mode": "trunk", "vlan": "1"},
                ]
            },
            "192.168.1.14": {
                "hostname": "Dist-Switch-1",
                "device_type": "cisco_ios",
                "running_config": "hostname Dist-Switch-1\ninterface FastEthernet0/23",
                "vlans": [{"vlan_id": "10", "name": "PRODUCTION"}],
                "interfaces": [
                    {"interface": "FastEthernet0/23", "description": "Trunk to Core", "mode": "trunk", "vlan": "1"}
                ]
            },
            "192.168.1.15": {
                "hostname": "Dist-Switch-2",
                "device_type": "cisco_ios",
                "running_config": "hostname Dist-Switch-2\ninterface FastEthernet0/24",
                "vlans": [{"vlan_id": "20", "name": "MANAGEMENT"}],
                "interfaces": [
                    {"interface": "FastEthernet0/24", "description": "Trunk to Core", "mode": "trunk", "vlan": "1"}
                ]
            }
        }
        edges = [
            {
                "source_ip": "192.168.1.13",
                "target_ip": "192.168.1.14",
                "source_port": "FastEthernet0/23",
                "target_port": "FastEthernet0/23"
            },
            {
                "source_ip": "192.168.1.13",
                "target_ip": "192.168.1.15",
                "source_port": "FastEthernet0/24",
                "target_port": "FastEthernet0/24"
            }
        ]
        return {"nodes": nodes, "edges": edges}

    # REAL NETWORK RECURSIVE CRAWL
    queue = [seed_ip]
    visited = set()
    nodes = {}
    edges = []

    while queue:
        ip = queue.pop(0)
        if ip in visited:
            continue
        visited.add(ip)

        print(f"Crawling switch: {ip}...")
        params = {
            "host": ip,
            "device_type": credentials.get("device_type", "cisco_ios"),
            "username": credentials.get("username", ""),
            "password": credentials.get("password", "")
        }

        try:
            device_data = fetch_device_config(params)
        except Exception as e:
            print(f"Error connecting to {ip}: {e}")
            if ip == seed_ip:
                raise e
            continue

        if not device_data:
            continue

        hostname = "Unknown"
        running_cfg = device_data.get("running_config", "")
        for line in running_cfg.splitlines():
            if line.startswith("hostname "):
                hostname = line.split(" ")[1]
                break

        vlans = []
        if "vlans" in device_data:
            for v in device_data["vlans"]:
                vlans.append({"vlan_id": v.get("vlan_id", ""), "name": v.get("name", "")})

        interfaces = device_data.get("interfaces", [])

        nodes[ip] = {
            "hostname": hostname,
            "device_type": params["device_type"],
            "running_config": running_cfg,
            "vlans": vlans,
            "interfaces": interfaces
        }

        neighbors = device_data.get("lldp", []) or device_data.get("cdp", [])
        for neighbor in neighbors:
            remote_host = neighbor.get("neighbor_name") or neighbor.get("destination_host") or neighbor.get("neighbor")
            local_port = neighbor.get("local_port") or neighbor.get("local_interface")
            remote_port = neighbor.get("remote_port") or neighbor.get("neighbor_interface") or neighbor.get("port_id")

            # Try to resolve remote IP directly from LLDP/CDP details
            remote_ip = neighbor.get("management_ip") or neighbor.get("mgmt_address") or neighbor.get("management_address")

            # Fallback: Resolve via MAC table + ARP table of the current switch
            if not remote_ip and local_port:
                macs_on_port = []
                for mac_entry in device_data.get("mac", []):
                    entry_port = mac_entry.get("interface") or mac_entry.get("destination_port") or mac_entry.get("port")
                    if entry_port == local_port:
                        mac_addr = mac_entry.get("mac") or mac_entry.get("destination_address") or mac_entry.get("mac_address")
                        if mac_addr:
                            macs_on_port.append(mac_addr.lower().replace(".", "").replace(":", "").replace("-", ""))

                for arp_entry in device_data.get("arp", []):
                    arp_mac = arp_entry.get("mac") or arp_entry.get("mac_address")
                    if arp_mac:
                        arp_mac_clean = arp_mac.lower().replace(".", "").replace(":", "").replace("-", "")
                        if arp_mac_clean in macs_on_port:
                            remote_ip = arp_entry.get("ip") or arp_entry.get("address")
                            if remote_ip:
                                print(f"Resolved neighbor {remote_host} IP to {remote_ip} via ARP/MAC tables.")
                                break

            if remote_host:
                edges.append({
                    "source_ip": ip,
                    "target_ip": remote_ip,  # Could be None if unresolved
                    "target_hostname": remote_host,
                    "source_port": local_port,
                    "target_port": remote_port
                })

                # If IP resolved, add to queue
                if remote_ip and remote_ip not in visited:
                    queue.append(remote_ip)
    
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