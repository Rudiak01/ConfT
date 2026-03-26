import json
import re
from ssh_connect import connect


def parse_vlans(output):
    vlans = []

    for line in output.splitlines():
        match = re.match(r"^(\d+)\s+(\S+)", line)
        if match:
            vlans.append({
                "vlan_id": match.group(1),
                "name": match.group(2)
            })

    return vlans


def parse_switchport(output):
    interfaces = []
    current = {}

    for line in output.splitlines():

        if line.startswith("Name:"):
            if current:
                interfaces.append(current)
            current = {"name": line.split("Name:")[1].strip()}

        elif "Operational Mode:" in line:
            current["mode"] = line.split(":")[1].strip()

        elif "Access Mode VLAN:" in line:
            vlan = re.search(r"(\d+)", line)
            if vlan:
                current["access_vlan"] = vlan.group(1)

        elif "Trunking VLANs Enabled:" in line:
            current["trunk_vlans"] = line.split(":")[1].strip()

    if current:
        interfaces.append(current)

    return interfaces


def main():
    print("Connexion au switch...")
    connection = connect()

    print("Collecte des VLANs...")
    vlan_output = connection.send_command("show vlan brief")

    print("Collecte des switchports...")
    switchport_output = connection.send_command("show interfaces switchport")

    print("Backup running-config...")
    running_config = connection.send_command("show running-config") # Pour tester, pas de parsing dessus

    connection.disconnect()

    data = {
        "vlans": parse_vlans(vlan_output),
        "interfaces": parse_switchport(switchport_output),
        "running_config": running_config  # conf complete
    }

    with open("current_state.json", "w") as f:
        json.dump(data, f, indent=4)

    print("Extraction complète terminée → current_state.json")


if __name__ == "__main__":
    main()