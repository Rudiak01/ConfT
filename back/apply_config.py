import json
from .ssh_connect import connect
from .config import SWITCH, PROTECTED_INTERFACES
from .vendor_syntax import VENDOR_SYNTAX

def normalize_interface_name(name):
    if not name:
        return ""
    name_lower = name.lower()
    replacements = [
        ("fastethernet", "fa"),
        ("gigabitethernet", "gi"),
        ("tenethernet", "te"),
        ("ethernet", "eth"),
        ("vlan", "vl"),
    ]
    res = name_lower
    for long_form, short_form in replacements:
        res = res.replace(long_form, short_form)
    res = res.replace(" ", "")
    return res

def build_commands(data, device_type):
    commands = []
    syntax = VENDOR_SYNTAX.get(device_type, VENDOR_SYNTAX["cisco_ios"])["write"]

    # 1. PARAMÈTRES GLOBAUX (Ex: Spanning-Tree)
    if "stp" in data:
        stp_data = data["stp"]
        if "mode" in stp_data and "stp_mode" in syntax:
            commands.append(syntax["stp_mode"].format(mode=stp_data["mode"]))
        if "root_vlan" in stp_data and "stp_root" in syntax:
            commands.append(syntax["stp_root"].format(vlan=stp_data["root_vlan"]))

    # 2. VLANs
    for vlan in data.get("vlans", []):
        vlan_id = int(vlan.get('vlan_id'))
        if vlan_id in [1, 1002, 1003, 1004, 1005]:
            continue
        if "vlan_create" in syntax:
            commands.append(syntax["vlan_create"].format(id=vlan_id))
        if "vlan_name" in syntax:
            clean_name = vlan.get('name', '').replace(" ", "_")[:32]
            commands.append(syntax["vlan_name"].format(name=clean_name))

    # 3. INTERFACES
    for iface in data.get("interfaces", []):
        iface_name = iface.get("interface")
        if not iface_name:
            continue

        # Normaliser le nom de l'interface pour comparaison
        norm_name = normalize_interface_name(iface_name)
        is_protected = False
        for protected in PROTECTED_INTERFACES:
            if normalize_interface_name(protected) == norm_name:
                is_protected = True
                break

        if is_protected:
            print(f"Attention : Interface protégée ignorée : {iface_name}")
            continue

        # Déterminer le mode (access / trunk / unknown)
        mode_val = iface.get("mode") or ""
        mode_lower = mode_val.lower()

        is_access = False
        is_trunk = False

        if "access" in mode_lower:
            is_access = True
        elif "trunk" in mode_lower:
            is_trunk = True
        elif mode_lower.endswith("fdx") or mode_lower.endswith("hdx"):
            is_access = True

        # Obtenir les valeurs de VLAN
        vlan_val = iface.get("vlan") or iface.get("vlan_id")
        vlan_str = str(vlan_val).strip() if vlan_val is not None else ""
        if vlan_str == "None":
            vlan_str = ""

        allowed_vlans_val = iface.get("allowed_vlans")
        allowed_vlans_str = str(allowed_vlans_val).strip() if allowed_vlans_val is not None else ""
        if allowed_vlans_str == "None":
            allowed_vlans_str = ""

        # Si le mode n'est pas explicite, on le déduit des attributs
        if not (is_access or is_trunk):
            if vlan_str:
                is_access = True
            elif allowed_vlans_str:
                is_trunk = True

        # Générer les commandes pour cette interface s'il y a des modifs à faire
        iface_commands = []

        # Description
        desc_val = iface.get("description")
        if desc_val:  # Ne pas ajouter de description si elle est vide
            iface_commands.append(syntax["desc"].format(desc=desc_val))

        # Mode accès
        if is_access:
            if "mode_access" in syntax:
                if "{vlan}" in syntax["mode_access"]:
                    if vlan_str:
                        iface_commands.append(syntax["mode_access"].format(vlan=vlan_str))
                else:
                    iface_commands.append(syntax["mode_access"])

            if vlan_str and "access_vlan" in syntax:
                iface_commands.append(syntax["access_vlan"].format(vlan=vlan_str))

            if iface.get("voice_vlan") and "voice_vlan" in syntax:
                iface_commands.append(syntax["voice_vlan"].format(vlan=iface["voice_vlan"]))

            if iface.get("portfast") and "portfast" in syntax:
                iface_commands.append(syntax["portfast"])

        # Mode trunk
        elif is_trunk:
            if "mode_trunk" in syntax:
                if "{vlans}" in syntax["mode_trunk"]:
                    if allowed_vlans_str:
                        iface_commands.append(syntax["mode_trunk"].format(vlans=allowed_vlans_str))
                else:
                    iface_commands.append(syntax["mode_trunk"])

            if allowed_vlans_str and "trunk_allowed" in syntax:
                iface_commands.append(syntax["trunk_allowed"].format(vlans=allowed_vlans_str))

        # S'il y a des commandes générées pour cette interface, on ajoute l'interface
        if iface_commands:
            commands.append(syntax["interface"].format(iface=iface_name))
            commands.extend(iface_commands)

    return commands

def apply_device_config(connection_params, config_data): # readded
    import os
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv("MOCK_NETWORK", "0") == "1":
        device_type = connection_params.get("device_type", "cisco_ios")
        commands = build_commands(config_data, device_type)
        return True, f"[MOCK] Configuration applied successfully: {', '.join(commands) if commands else 'none'}"

    try:
        connection = connect(connection_params)
        device_type = connection_params.get("device_type", "cisco_ios")
        commands = build_commands(config_data, device_type)
        if not commands:
            connection.disconnect()
            return True, "No commands to apply"
            
        output = connection.send_config_set(commands)
        connection.save_config()
        connection.disconnect()
        return True, output
    except Exception as e:
        return False, str(e)

def main():
    try:
        with open("back/desired_config.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Erreur : desired_config.json introuvable.")
        return

    device_type = SWITCH.get("device_type", "cisco_ios")
    commands = build_commands(data, device_type)

    print("\n--- Commandes générées ---")
    for cmd in commands:
        print(cmd)

    print("\nApplication de la configuration...")
    try:
        connection = connect(SWITCH)
        if commands:
            output = connection.send_config_set(commands)
            connection.save_config()
            print("\nSuccès : Configuration appliquée avec succès.")
            print(output)
        else:
            print("Aucune commande à envoyer.")
        connection.disconnect()
    except Exception as e:
        print(f"Erreur lors de l'application: {e}")

if __name__ == "__main__":
    main()