# extract_config.py
import json
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from ssh_connect import connect
from config import SWITCH
from vendor_syntax import VENDOR_SYNTAX

def normalize_data(raw_data, template_mapping):
    """
    Transforme les clés brutes de TextFSM en clés universelles pour le Front-End.
    """
    normalized_list = []
    for item in raw_data:
        normalized_item = {}
        for raw_key, universal_key in template_mapping.items():
            # On récupère la valeur si la clé brute existe
            if raw_key in item:
                normalized_item[universal_key] = item[raw_key]
        if normalized_item:
            normalized_list.append(normalized_item)
    return normalized_list


def fetch_device_config(params):
    device_type = params.get("device_type", "cisco_ios")
    syntax = VENDOR_SYNTAX.get(device_type, VENDOR_SYNTAX["cisco_ios"])

    try:
        connection = connect(params)
        
        # 1. Récupération des données brutes
        raw_vlans = connection.send_command(syntax["read"]["vlans"], use_textfsm=True)
        raw_interfaces = connection.send_command(syntax["read"]["interfaces"], use_textfsm=True)
        running_config = connection.send_command(syntax["read"]["running"])
        
        connection.disconnect()

        # 2. Sécurité si TextFSM échoue (renvoie une string au lieu d'une liste)
        if isinstance(raw_vlans, str) or isinstance(raw_interfaces, str):
            print("⚠ Attention : TextFSM n'a pas pu parser la sortie (Template manquant ?)")
            return None

        # 3. Normalisation (La magie du JSON Universel)
        vlans_mapping = syntax["normalize_keys"]["vlans"]
        interfaces_mapping = syntax["normalize_keys"]["interfaces"]

        return {
            "vlans": normalize_data(raw_vlans, vlans_mapping),
            "interfaces": normalize_data(raw_interfaces, interfaces_mapping),
            "running_config": running_config
        }

    except NetmikoAuthenticationException:
        print(f"❌ Erreur : Identifiants incorrects pour {params.get('host')}")
        return None
    except NetmikoTimeoutException:
        print(f"❌ Erreur : Le switch {params.get('host')} est injoignable (Timeout)")
        return None
    except Exception as e:
        print(f"❌ Erreur inattendue avec {params.get('host')}: {e}")
        return None

def main():
    print(f"Connexion au switch {SWITCH['host']}...")
    data = fetch_device_config(SWITCH)
    
    if data:
        with open("current_state.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Extraction et normalisation terminées → current_state.json")

if __name__ == "__main__":
    main()