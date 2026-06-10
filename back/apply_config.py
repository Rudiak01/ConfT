import json
from ssh_connect import connect
from config import SWITCH, PROTECTED_INTERFACES, VENDOR_SYNTAX

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
        if "vlan_create" in syntax:
            commands.append(syntax["vlan_create"].format(id=vlan['vlan_id']))
        if "vlan_name" in syntax:
            commands.append(syntax["vlan_name"].format(name=vlan['name']))

    # 3. INTERFACES
    for iface in data.get("interfaces", []):
        iface_name = iface["interface"]

        if iface_name in PROTECTED_INTERFACES:
            print(f"⚠ Interface protégée ignorée : {iface_name}")
            continue

        commands.append(syntax["interface"].format(iface=iface_name))

        if "description" in iface and "desc" in syntax:
            commands.append(syntax["desc"].format(desc=iface['description']))

        mode = iface.get("mode")
        if mode == "access" and "mode_access" in syntax:
            commands.append(syntax["mode_access"])
            if "access_vlan" in syntax:
                commands.append(syntax["access_vlan"].format(vlan=iface['vlan']))
            if iface.get("voice_vlan") and "voice_vlan" in syntax:
                commands.append(syntax["voice_vlan"].format(vlan=iface['voice_vlan']))
            if iface.get("portfast") and "portfast" in syntax:
                commands.append(syntax["portfast"])

        elif mode == "trunk" and "mode_trunk" in syntax:
            commands.append(syntax["mode_trunk"])
            if iface.get("allowed_vlans") and "trunk_allowed" in syntax:
                commands.append(syntax["trunk_allowed"].format(vlans=iface['allowed_vlans']))

    # 4. ROUTAGE STATIQUE
    for route in data.get("routes", []):
        if "route" in syntax:
            commands.append(syntax["route"].format(
                network=route["network"], 
                mask=route.get("mask", ""), # Arista utilise parfois le CIDR, donc mask peut être vide
                nexthop=route["nexthop"]
            ))

    return commands

def main():
    try:
        with open("desired_config.json", "r") as f:
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
            print("\n✅ Configuration appliquée avec succès.")
            print(output)
        else:
            print("Aucune commande à envoyer.")
        connection.disconnect()
    except Exception as e:
        print(f"❌ Erreur lors de l'application: {e}")

if __name__ == "__main__":
    main()