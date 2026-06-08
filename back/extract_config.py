import json
import re
try:
    from .ssh_connect import connect
except ImportError:
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


def parse_cdp_neighbors_detail(output):
    neighbors = []
    current_neighbor = {}
    
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Device ID:"):
            if current_neighbor and "ip" in current_neighbor:
                neighbors.append(current_neighbor)
            current_neighbor = {"device_id": line.split("Device ID:")[1].strip()}
        elif line.startswith("IP address:"):
            current_neighbor["ip"] = line.split("IP address:")[1].strip()
        elif line.startswith("Interface:"):
            parts = line.split(",")
            for p in parts:
                p = p.strip()
                if p.startswith("Interface:"):
                    current_neighbor["local_interface"] = p.split("Interface:")[1].strip()
                elif p.startswith("Port ID (outgoing port):"):
                    current_neighbor["remote_interface"] = p.split("Port ID (outgoing port):")[1].strip()
                elif p.startswith("Port ID"):
                    current_neighbor["remote_interface"] = p.split(":")[1].strip()
                    
    if current_neighbor and "ip" in current_neighbor:
        neighbors.append(current_neighbor)
        
    return neighbors

def get_mock_network_data():
    import os
    import json
    from pathlib import Path
    
    mock_data = {
        "vlans": [{"vlan_id": "1", "name": "default"}],
        "interfaces": [{"name": "Gi0/1", "mode": "trunk"}],
        "running_config": "hostname Mock\ntransport input ssh\n"
    }
    
    state_file = Path(__file__).parent / "current_state.json"
    if state_file.exists():
        with open(state_file, "r") as f:
            mock_data = json.load(f)
            
    return {
        "nodes": {
            "192.168.1.1": {
                "hostname": "CoreRouter",
                "ip": "192.168.1.1",
                "device_type": "cisco_ios",
                "vlans": mock_data.get("vlans", []),
                "interfaces": mock_data.get("interfaces", []),
                "running_config": mock_data.get("running_config", "")
            },
            "192.168.1.2": {
                "hostname": "AccessSwitch1",
                "ip": "192.168.1.2",
                "device_type": "cisco_ios",
                "vlans": mock_data.get("vlans", []),
                "interfaces": mock_data.get("interfaces", []),
                "running_config": mock_data.get("running_config", "")
            }
        },
        "edges": [
            {"source_ip": "192.168.1.1", "target_ip": "192.168.1.2", "source_port": "Gi1/0/1", "target_port": "Gi1/0/24"}
        ]
    }

def fetch_device_config(params):
    import os
    import json
    from pathlib import Path
    
    if os.environ.get("MOCK_NETWORK") == "1":
        state_file = Path(__file__).parent / "current_state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                return json.load(f)
        return {
            "vlans": [{"vlan_id": "1", "name": "default"}],
            "interfaces": [{"name": "Gi0/1", "mode": "trunk"}],
            "running_config": f"hostname Mock\ntransport input ssh\n! mocked data for {params.get('host')}"
        }

    try:
        connection = connect(params)
        vlan_output = connection.send_command("show vlan brief")
        switchport_output = connection.send_command("show interfaces switchport")
        running_config = connection.send_command("show running-config")
        connection.disconnect()
        return {
            "vlans": parse_vlans(vlan_output),
            "interfaces": parse_switchport(switchport_output),
            "running_config": running_config
        }
    except Exception as e:
        print(f"Error fetching data from {params.get('host')}: {e}")
        return None

def crawl_network(seed_ip, credentials):
    import os
    if os.environ.get("MOCK_NETWORK") == "1":
        return get_mock_network_data()

    visited_ips = set()
    queue = [seed_ip]
    
    nodes = {}
    edges = []
    
    while queue:
        current_ip = queue.pop(0)
        if current_ip in visited_ips:
            continue
            
        visited_ips.add(current_ip)
        print(f"Crawling {current_ip}...")
        
        params = credentials.copy()
        params["host"] = current_ip
        
        try:
            connection = connect(params)
            prompt = connection.find_prompt()
            hostname = prompt.replace("#", "").replace(">", "").strip()
            
            vlan_output = connection.send_command("show vlan brief")
            switchport_output = connection.send_command("show interfaces switchport")
            running_config = connection.send_command("show running-config")
            
            nodes[current_ip] = {
                "hostname": hostname,
                "ip": current_ip,
                "device_type": params.get("device_type", "cisco_ios"),
                "vlans": parse_vlans(vlan_output),
                "interfaces": parse_switchport(switchport_output),
                "running_config": running_config
            }
            
            cdp_output = connection.send_command("show cdp neighbors detail")
            neighbors = parse_cdp_neighbors_detail(cdp_output)
            
            for neighbor in neighbors:
                neighbor_ip = neighbor.get("ip")
                if neighbor_ip:
                    edges.append({
                        "source_ip": current_ip,
                        "target_ip": neighbor_ip,
                        "source_port": neighbor.get("local_interface"),
                        "target_port": neighbor.get("remote_interface")
                    })
                    
                    if neighbor_ip not in visited_ips and neighbor_ip not in queue:
                        queue.append(neighbor_ip)
                        
            connection.disconnect()
        except Exception as e:
            print(f"Error crawling {current_ip}: {e}")
            
    # Deduplicate edges (A->B and B->A)
    unique_edges = []
    seen_links = set()
    for e in edges:
        link = tuple(sorted([e["source_ip"], e["target_ip"]]))
        if link not in seen_links:
            seen_links.add(link)
            unique_edges.append(e)
            
    return {"nodes": nodes, "edges": unique_edges}

def main():
    print("Connexion au switch...")
    data = extract_device_data(None)
    if data:
        with open("current_state.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Extraction complète terminée → current_state.json")

if __name__ == "__main__":
    main()