import json
from ssh_connect import connect

# Interfaces à protéger
PROTECTED_INTERFACES = [
    "GigabitEthernet0/1",
    "GigabitEthernet0/2",
    "FastEthernet0/24"
]


def build_commands(data):
    commands = []

    # -------------------
    # VLANs
    # -------------------
    for vlan in data.get("vlans", []):
        commands.append(f"vlan {vlan['vlan_id']}")
        commands.append(f"name {vlan['name']}")

    # -------------------
    # Interfaces
    # -------------------
    for iface in data.get("interfaces", []):

        interface_name = iface["interface"]

        # Protection des interfaces critiques
        if interface_name in PROTECTED_INTERFACES:
            print(f"⚠ Interface protégée ignorée : {interface_name}")
            continue

        commands.append(f"interface {interface_name}")

        # Description
        if "description" in iface:
            commands.append(f"description {iface['description']}")

        mode = iface.get("mode")

        # -------- ACCESS --------
        if mode == "access":
            commands.append("switchport mode access")
            commands.append(f"switchport access vlan {iface['vlan']}")

            if iface.get("voice_vlan"):
                commands.append(f"switchport voice vlan {iface['voice_vlan']}")

            if iface.get("portfast"):
                commands.append("spanning-tree portfast")

        # -------- TRUNK --------
        elif mode == "trunk":
            commands.append("switchport mode trunk")

            if iface.get("allowed_vlans"):
                commands.append(
                    f"switchport trunk allowed vlan {iface['allowed_vlans']}"
                )

    return commands


def main():
    with open("desired_config.json", "r") as f:
        data = json.load(f)

    connection = connect()

    commands = build_commands(data)

    print("\n--- Commandes envoyées ---")
    for cmd in commands:
        print(cmd)

    print("\nApplication de la configuration...")
    output = connection.send_config_set(commands)

    connection.save_config()
    connection.disconnect()

    print("\nConfiguration appliquée avec succès.")


if __name__ == "__main__":
    main()