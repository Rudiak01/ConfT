import json
from ssh_connect import connect
from config import SWITCH, PROTECTED_INTERFACES, VENDOR_SYNTAX

def build_commands(data, device_type):
    commands = []
    # On charge la syntaxe d'écriture correspondant au switch
    syntax = VENDOR_SYNTAX.get(device_type, VENDOR_SYNTAX["cisco_ios"])["write"]

    # -------------------
    # VLANs
    # -------------------
    for vlan in data.get("vlans", []):
        commands.append(syntax["vlan_create"].format(id=vlan['vlan_id']))
        commands.append(syntax["vlan_name"].format(name=vlan['name']))

    # -------------------
    # Interfaces
    # -------------------
    for iface in data.get("interfaces", []):
        interface_name = iface["interface"]

        if interface_name in PROTECTED_INTERFACES:
            print(f"⚠ Interface protégée ignorée : {interface_name}")
            continue

        commands.append(syntax["interface"].format(iface=interface_name))

        if "description" in iface and "desc" in syntax:
            commands.append(syntax["desc"].format(desc=iface['description']))

        mode = iface.get("mode")

        # -------- ACCESS --------
        if mode == "access":
            commands.append(syntax["mode_access"])
            # Formatage dynamique via le dictionnaire
            if "access_vlan" in syntax:
                commands.append(syntax["access_vlan"].format(vlan=iface['vlan']))
            
            if iface.get("voice_vlan") and "voice_vlan" in syntax:
                commands.append(syntax["voice_vlan"].format(vlan=iface['voice_vlan']))

            if iface.get("portfast") and "portfast" in syntax:
                commands.append(syntax["portfast"])

        # -------- TRUNK --------
        elif mode == "trunk":
            commands.append(syntax["mode_trunk"])
            if iface.get("allowed_vlans") and "trunk_allowed" in syntax:
                commands.append(syntax["trunk_allowed"].format(vlans=iface['allowed_vlans']))

    return commands

def main():
    with open("desired_config.json", "r") as f:
        data = json.load(f)

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
            print("\nConfiguration appliquée avec succès.")
            print(output)
        else:
            print("Aucune commande à envoyer.")
        connection.disconnect()
    except Exception as e:
        print(f"Erreur lors de l'application: {e}")

if __name__ == "__main__":
    main()