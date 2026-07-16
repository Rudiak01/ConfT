# extract_config.py
import json
import re
from netmiko import SSHDetect
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from .ssh_connect import connect
from .config import SWITCH
from .vendor_syntax import VENDOR_SYNTAX

class DeviceUnreachableError(Exception):
    pass

class DeviceAuthenticationError(Exception):
    pass

def autodetect_device_type(params):
    detect_params = params.copy()
    detect_params["device_type"] = "autodetect"
    try:
        guesser = SSHDetect(**detect_params)
        best_match = guesser.autodetect()
        return best_match
    except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
        # Re-raise authentication or timeout issues
        raise e
    except Exception as e:
        print(f"Autodetection failed for {params.get('host')}: {e}")
        try:
            if 'guesser' in locals() and hasattr(guesser, 'connection'):
                guesser.connection.disconnect()
        except Exception:
            pass
        return None

def map_device_type(detected_type):
    if not detected_type:
        return "cisco_ios"
    detected_lower = detected_type.lower()
    if "cisco" in detected_lower:
        return "cisco_ios"
    if "arista" in detected_lower:
        return "arista_eos"
    if "hp" in detected_lower or "procurve" in detected_lower or "aruba" in detected_lower or "hewlett" in detected_lower:
        return "hp_procurve"
    if "huawei" in detected_lower:
        return "huawei"
    if "juniper" in detected_lower:
        return "juniper_junos"
    
    if detected_type in VENDOR_SYNTAX:
        return detected_type
    return "cisco_ios"

def to_str(val):
    if val is None:
        return ""
    if isinstance(val, list):
        if len(val) > 0:
            val = val[0]
        else:
            return ""
    return str(val)

def is_valid_mac(mac_str):
    if not mac_str:
        return False
    mac_str = to_str(mac_str)
    cleaned = mac_str.replace(":", "").replace("-", "").replace(".", "").strip()
    if len(cleaned) == 12 and all(c in "0123456789abcdefABCDEF" for c in cleaned):
        return True
    return False

def format_mac(mac_str):
    if not mac_str:
        return None
    mac_str = to_str(mac_str)
    cleaned = mac_str.replace(":", "").replace("-", "").replace(".", "").strip().lower()
    if len(cleaned) != 12:
        return mac_str
    return ":".join(cleaned[i:i+2] for i in range(0, 12, 2))

def normalize_port_name(port):
    if not port:
        return ""
    p = to_str(port).lower().strip()
    p = p.replace("ethernet", "").replace("fast", "").replace("gigabit", "").replace("tengigabit", "")
    p = p.replace("gi", "").replace("fa", "").replace("te", "").replace("eth", "")
    return p

def deduce_device_type_from_neighbor(neighbor):
    # Combine text fields to scan for vendor keywords
    fields = [
        to_str(neighbor.get("manufacturer")),
        to_str(neighbor.get("platform")),
        to_str(neighbor.get("neighbor_description")),
        to_str(neighbor.get("neighbor_name"))
    ]
    combined = " ".join(fields).lower()
    if not combined.strip():
        return None
        
    if "arista" in combined or "eos" in combined:
        return "arista_eos"
    if any(k in combined for k in ["hp", "procurve", "aruba", "hewlett", "hpe", "provision"]):
        return "hp_procurve"
    if "huawei" in combined or "vrp" in combined:
        return "huawei"
    if "juniper" in combined or "junos" in combined:
        return "juniper_junos"
    if "cisco" in combined or "ios" in combined or "catalyst" in combined or "nexus" in combined:
        return "cisco_ios"
        
    return None

def deduce_device_type_from_capabilities(capabilities_str, platform_str="", desc_str="", name_str=""):
    combined = " ".join([to_str(platform_str), to_str(desc_str), to_str(name_str)]).lower()
    # Check for OS keywords indicating a host
    if any(k in combined for k in ["windows", "linux", "ubuntu", "debian", "redhat", "centos", "fedora", "macos", "os x", "station"]):
        return "host"

    capabilities_str = to_str(capabilities_str)
    if not capabilities_str:
        if "router" in combined:
            return "router"
        if "switch" in combined:
            return "switch"
        return None

    # Standardize capabilities
    caps = [c.strip().lower() for c in capabilities_str.replace(";", ",").split(",")]
    
    is_station = False
    is_router = False
    is_bridge = False
    
    for cap in caps:
        # LLDP caps: Bridge (B), Router (R), Station (S), Telephone (T), WLAN AP (W)
        # CDP caps: Switch (S), Router (R), Host (H), Phone (P), Trans-Bridge (T)
        if any(k in cap for k in ['station', 'host', 'telephone', 'phone', 'wlan', 'ap']) or cap in ['s', 'h', 't', 'p', 'w']:
            is_station = True
        elif 'router' in cap or cap == 'r':
            is_router = True
        elif 'bridge' in cap or 'switch' in cap or cap == 'b' or cap == 's' or 'trans-bridge' in cap or 'source-route-bridge' in cap:
            is_bridge = True
            
    if is_bridge:
        return "switch"
    elif is_router:
        return "router"
    elif is_station:
        return "host"
        
    # fallback to single word check
    words = capabilities_str.lower().split()
    if 'b' in words or 'switch' in capabilities_str.lower() or 'bridge' in capabilities_str.lower():
        return "switch"
    if 'r' in words or 'router' in capabilities_str.lower():
        return "router"
    if 's' in words or 'h' in words or 'station' in capabilities_str.lower() or 'host' in capabilities_str.lower():
        return "host"
        
    return None

def deduce_device_type_from_neighbor_details(neighbor):
    capabilities = neighbor.get("capabilities") or ""
    platform = neighbor.get("platform") or ""
    description = neighbor.get("neighbor_description") or ""
    name = neighbor.get("neighbor_name") or neighbor.get("destination_host") or neighbor.get("neighbor") or ""
    
    # 1. First check capabilities & OS keywords
    dtype = deduce_device_type_from_capabilities(capabilities, platform, description, name)
    if dtype:
        if dtype == "switch":
            # If it's a switch, try to deduce the vendor OS for configuration purposes
            vendor_type = deduce_device_type_from_neighbor(neighbor)
            return vendor_type or "switch"
        return dtype
        
    # 2. Fallback to existing vendor OS detection
    vendor_type = deduce_device_type_from_neighbor(neighbor)
    if vendor_type:
        return vendor_type
        
    return "host" # If it's completely unconnectable and unrecognized, default to host as requested


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
    if device_type == "cisco_ios":
        print(f"Checking device type for {params.get('host')}...")
        try:
            detected_type = autodetect_device_type(params)
            if detected_type:
                device_type = map_device_type(detected_type)
                print(f"Detected device type: {detected_type} (mapped to: {device_type})")
            else:
                print(f"Could not autodetect device type. Falling back to: {device_type}")
        except Exception as e:
            # If autodetect failed due to network error/auth error, let it raise or handle
            print(f"Autodetection error for {params.get('host')}: {e}")
            raise e
            
    device_type = map_device_type(device_type)
    params["device_type"] = device_type
    
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
                raw_output = None
                try:
                    if feature == "lldp" and device_type == "hp_procurve":
                        # Custom detailed LLDP extraction for HP to get management IPs
                        summary_output = connection.send_command(command, use_textfsm=True)
                        if isinstance(summary_output, list):
                            detailed_results = []
                            ports_queried = set()
                            for item in summary_output:
                                port = item.get("local_interface")
                                if port and port not in ports_queried:
                                    ports_queried.add(port)
                                    port_detail = connection.send_command(f"show lldp info remote-device {port}", use_textfsm=True)
                                    if isinstance(port_detail, list):
                                        detailed_results.extend(port_detail)
                            raw_output = detailed_results
                        else:
                            raw_output = summary_output
                    else:
                        raw_output = connection.send_command(command, use_textfsm=True)
                except Exception as textfsm_err:
                    print(f"  [TextFSM Exception] for {feature} on {device_type}: {textfsm_err}")
                
                # If TextFSM failed (threw exception or returned string instead of list), use fallback parser
                if not isinstance(raw_output, list):
                    if feature == "vlans" and device_type == "hp_procurve":
                        print(f"  Running manual fallback parser for {feature}...")
                        raw_output_str = connection.send_command(command, use_textfsm=False)
                        parsed_vlans = []
                        for line in raw_output_str.splitlines():
                            match = re.match(r'^\s*(\d+)\s+(.*?)\s+(\|\s+|)(\S+)', line)
                            if match:
                                v_id, v_name, _, v_status = match.groups()
                                parsed_vlans.append({
                                    "vlan_id": v_id.strip(),
                                    "vlan_name": v_name.strip(),
                                    "name": v_name.strip(),
                                    "status": v_status.strip()
                                })
                        if parsed_vlans:
                            raw_output = parsed_vlans

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
    load_dotenv(override=True)

    # MOCK MODE
    if os.getenv("MOCK_NETWORK", "0") == "1":
        print("[MOCK] Crawling network in mock mode...")
        # Predefined 5-node mock topology (Switches, Router, Host)
        nodes = {
            "192.168.1.13": {
                "hostname": "Core-Switch",
                "device_type": "cisco_ios",
                "running_config": "hostname Core-Switch\ninterface FastEthernet0/1\ninterface FastEthernet0/23\ninterface FastEthernet0/24",
                "vlans": [{"vlan_id": "10", "name": "PRODUCTION"}, {"vlan_id": "20", "name": "MANAGEMENT"}],
                "interfaces": [
                    {"interface": "FastEthernet0/1", "description": "Uplink to Core Router", "mode": "trunk", "vlan": "1", "allowed_vlans": "10,20", "mac_address": "52:54:00:11:22:30"},
                    {"interface": "FastEthernet0/23", "description": "Trunk to Dist-1", "mode": "trunk", "vlan": "1", "allowed_vlans": "10,20", "mac_address": "52:54:00:11:22:33"},
                    {"interface": "FastEthernet0/24", "description": "Trunk to Dist-2", "mode": "trunk", "vlan": "1", "allowed_vlans": "10,20", "mac_address": "52:54:00:11:22:34"},
                ]
            },
            "192.168.1.14": {
                "hostname": "Dist-Switch-1",
                "device_type": "cisco_ios",
                "running_config": "hostname Dist-Switch-1\ninterface FastEthernet0/5\ninterface FastEthernet0/23",
                "vlans": [{"vlan_id": "10", "name": "PRODUCTION"}],
                "interfaces": [
                    {"interface": "FastEthernet0/5", "description": "Access to Web Server", "mode": "access", "vlan": "10", "allowed_vlans": None, "mac_address": "52:54:00:11:22:38"},
                    {"interface": "FastEthernet0/23", "description": "Trunk to Core", "mode": "trunk", "vlan": "1", "allowed_vlans": "10,20", "mac_address": "52:54:00:11:22:35"}
                ]
            },
            "192.168.1.15": {
                "hostname": "Dist-Switch-2",
                "device_type": "cisco_ios",
                "running_config": "hostname Dist-Switch-2\ninterface FastEthernet0/24",
                "vlans": [{"vlan_id": "20", "name": "MANAGEMENT"}],
                "interfaces": [
                    {"interface": "FastEthernet0/24", "description": "Trunk to Core", "mode": "trunk", "vlan": "1", "allowed_vlans": "10,20", "mac_address": "52:54:00:11:22:36"}
                ]
            },
            "192.168.1.1": {
                "hostname": "Core-Router",
                "device_type": "router",
                "running_config": "hostname Core-Router\ninterface GigabitEthernet0/0",
                "vlans": [],
                "interfaces": [
                    {"interface": "GigabitEthernet0/0", "description": "Link to Core Switch", "mode": "routed", "vlan": None, "mac_address": "52:54:00:99:88:77"}
                ]
            },
            "192.168.1.50": {
                "hostname": "Web-Server",
                "device_type": "host",
                "running_config": "# Linux Host running Ubuntu",
                "vlans": [],
                "interfaces": [
                    {"interface": "eth0", "description": "Connected to Dist-1", "mode": "access", "vlan": "10", "mac_address": "52:54:00:aa:bb:cc"}
                ]
            }
        }
        edges = [
            {
                "source_ip": "192.168.1.13",
                "target_ip": "192.168.1.1",
                "source_port": "FastEthernet0/1",
                "target_port": "GigabitEthernet0/0"
            },
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
            },
            {
                "source_ip": "192.168.1.14",
                "target_ip": "192.168.1.50",
                "source_port": "FastEthernet0/5",
                "target_port": "eth0"
            }
        ]
        return {"nodes": nodes, "edges": edges}

    # REAL NETWORK RECURSIVE CRAWL
    queue = [seed_ip]
    visited = set()
    nodes = {}
    edges = []
    known_device_types = {seed_ip: credentials.get("device_type", "cisco_ios")}

    discovered_neighbors = {}

    while queue:
        ip = queue.pop(0)
        if ip in visited:
            continue
        visited.add(ip)

        print(f"Crawling switch: {ip}...")
        device_type = known_device_types.get(ip) or credentials.get("device_type", "cisco_ios")
        params = {
            "host": ip,
            "device_type": device_type,
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
            trimmed = line.strip()
            if trimmed.startswith("hostname "):
                hostname = trimmed.split("hostname ", 1)[1].strip().strip('"').strip("'")
                break

        vlans = []
        if "vlans" in device_data:
            for v in device_data["vlans"]:
                vlans.append({"vlan_id": v.get("vlan_id", ""), "name": v.get("name", "")})

        interfaces = device_data.get("interfaces", [])
        phys_interfaces = device_data.get("phys_interfaces", [])

        # Build mapping from physical interface name to MAC address
        mac_mapping = {}
        for pi in phys_interfaces:
            name = pi.get("interface")
            mac = pi.get("mac_address")
            if name and mac:
                mac_mapping[name] = mac

        # Associate MAC address with normalized interfaces
        for iface in interfaces:
            iface_name = iface.get("interface")
            if iface_name in mac_mapping:
                iface["mac_address"] = mac_mapping[iface_name]

        nodes[ip] = {
            "hostname": hostname,
            "device_type": params["device_type"],
            "running_config": running_cfg,
            "vlans": vlans,
            "interfaces": interfaces
        }

        neighbors = []
        seen_neighbors = set()
        for proto in ["lldp", "cdp"]:
            brief_proto = proto + "_brief"
            for neighbor in device_data.get(proto, []) or []:
                local_port = neighbor.get("local_port") or neighbor.get("local_interface")
                if local_port:
                    local_port = to_str(local_port)
                
                # Check if we need to resolve empty local_port
                if not local_port:
                    for b_neigh in device_data.get(brief_proto, []) or []:
                        b_name = to_str(b_neigh.get("neighbor_name"))
                        b_rem = to_str(b_neigh.get("remote_port"))
                        b_loc = to_str(b_neigh.get("local_port"))
                        
                        det_name = to_str(neighbor.get("neighbor_name") or neighbor.get("chassis_id"))
                        det_rem = to_str(neighbor.get("remote_port") or neighbor.get("port_id"))
                        
                        # Clean mac addresses for comparison
                        b_rem_clean = b_rem.lower().replace(".", "").replace(":", "").replace("-", "")
                        det_rem_clean = det_rem.lower().replace(".", "").replace(":", "").replace("-", "")
                        
                        # Match by remote port or by name and remote port
                        port_match = (b_rem_clean and det_rem_clean and b_rem_clean == det_rem_clean)
                        name_match = (det_name and b_name and (det_name == b_name or b_name in det_name or det_name in b_name))
                        
                        if port_match or (name_match and b_rem_clean == det_rem_clean):
                            local_port = b_loc
                            neighbor["local_port"] = b_loc
                            neighbor["local_interface"] = b_loc
                            break

                remote_host = to_str(neighbor.get("neighbor_name") or neighbor.get("destination_host") or neighbor.get("neighbor"))
                r_port = to_str(neighbor.get("remote_port") or neighbor.get("neighbor_interface") or neighbor.get("port_id"))
                chassis = to_str(neighbor.get("chassis_id"))
                
                # Deduplicate based on a highly unique key signature
                key = (local_port, remote_host, r_port, chassis)
                if key not in seen_neighbors:
                    seen_neighbors.add(key)
                    neighbors.append(neighbor)

        for neighbor in neighbors:
            remote_host = to_str(neighbor.get("neighbor_name") or neighbor.get("destination_host") or neighbor.get("neighbor"))
            # Fallback to chassis_id if neighbor name is not advertised
            if not remote_host or remote_host.lower().strip() in ["", "- not advertised", "not advertised"]:
                remote_host = to_str(neighbor.get("chassis_id"))
            if not remote_host:
                remote_host = "Unknown"

            local_port = to_str(neighbor.get("local_port") or neighbor.get("local_interface"))
            remote_port = to_str(neighbor.get("remote_port") or neighbor.get("neighbor_interface") or neighbor.get("port_id"))

            # Try to resolve remote IP directly from LLDP/CDP details
            remote_ip = neighbor.get("management_ip") or neighbor.get("mgmt_address") or neighbor.get("management_address")
            if remote_ip:
                remote_ip = to_str(remote_ip)
            if remote_ip and remote_ip.lower().strip() in ["- not advertised", "not advertised"]:
                remote_ip = None

            # Fallback: Resolve via MAC table + ARP table of the current switch
            if not remote_ip and local_port:
                macs_on_port = []
                for mac_entry in device_data.get("mac", []):
                    entry_port = mac_entry.get("interface") or mac_entry.get("destination_port") or mac_entry.get("port")
                    norm_entry = normalize_port_name(entry_port)
                    norm_local = normalize_port_name(local_port)
                    if norm_entry and norm_local and (norm_entry == norm_local or norm_entry.endswith(norm_local) or norm_local.endswith(norm_entry)):
                        mac_addr = mac_entry.get("mac") or mac_entry.get("destination_address") or mac_entry.get("mac_address")
                        if mac_addr:
                            mac_addr_str = to_str(mac_addr)
                            macs_on_port.append(mac_addr_str.lower().replace(".", "").replace(":", "").replace("-", ""))

                for arp_entry in device_data.get("arp", []):
                    arp_mac = arp_entry.get("mac") or arp_entry.get("mac_address")
                    if arp_mac:
                        arp_mac_str = to_str(arp_mac)
                        arp_mac_clean = arp_mac_str.lower().replace(".", "").replace(":", "").replace("-", "")
                        if arp_mac_clean in macs_on_port:
                            resolved_ip_val = arp_entry.get("ip") or arp_entry.get("address")
                            if resolved_ip_val:
                                remote_ip = to_str(resolved_ip_val)
                                print(f"Resolved neighbor {remote_host} IP to {remote_ip} via ARP/MAC tables.")
                                break

            # Determine MAC address for this interface
            neighbor_mac = neighbor.get("mac_address") or neighbor.get("chassis_id")
            if neighbor_mac and not is_valid_mac(neighbor_mac):
                neighbor_mac = None

            # Fallback to port_id if it is a MAC address
            if not neighbor_mac:
                port_id_val = neighbor.get("port_id")
                if port_id_val and is_valid_mac(port_id_val):
                    neighbor_mac = port_id_val

            # Fallback to looking up MAC table on the port
            if not neighbor_mac and local_port:
                macs_on_port = []
                for mac_entry in device_data.get("mac", []):
                    entry_port = mac_entry.get("interface") or mac_entry.get("destination_port") or mac_entry.get("port")
                    norm_entry = normalize_port_name(entry_port)
                    norm_local = normalize_port_name(local_port)
                    if norm_entry and norm_local and (norm_entry == norm_local or norm_entry.endswith(norm_local) or norm_local.endswith(norm_entry)):
                        mac_addr = mac_entry.get("mac") or mac_entry.get("destination_address") or mac_entry.get("mac_address")
                        if mac_addr:
                            macs_on_port.append(mac_addr)
                if len(macs_on_port) == 1:
                    neighbor_mac = macs_on_port[0]
                elif len(macs_on_port) > 1:
                    # Find MAC matching remote_ip in ARP table
                    arp_mac = None
                    for arp_entry in device_data.get("arp", []):
                        arp_ip = arp_entry.get("ip") or arp_entry.get("address")
                        if arp_ip == remote_ip:
                            arp_mac = arp_entry.get("mac") or arp_entry.get("mac_address")
                            break
                    if arp_mac:
                        neighbor_mac = arp_mac
                    else:
                        neighbor_mac = macs_on_port[0]

            if neighbor_mac:
                neighbor_mac = format_mac(neighbor_mac)

            # If still no remote_ip, use the neighbor's MAC address directly as its identifier (real data fallback)
            if not remote_ip and neighbor_mac:
                remote_ip = neighbor_mac
                print(f"Using MAC address {remote_ip} as unique identifier for neighbor {remote_host}")

            if remote_host and remote_ip:
                edges.append({
                    "source_ip": ip,
                    "target_ip": remote_ip,
                    "target_hostname": remote_host,
                    "source_port": local_port,
                    "target_port": remote_port
                })

                # Deduce neighbor device type
                neighbor_device_type = deduce_device_type_from_neighbor_details(neighbor)

                if remote_ip not in discovered_neighbors:
                    discovered_neighbors[remote_ip] = {
                        "hostname": remote_host,
                        "device_type": neighbor_device_type,
                        "interfaces": []
                    }
                else:
                    if neighbor_device_type and neighbor_device_type != "host":
                        discovered_neighbors[remote_ip]["device_type"] = neighbor_device_type

                if remote_port:
                    if not any(i["interface"] == remote_port for i in discovered_neighbors[remote_ip]["interfaces"]):
                        mode = "access"
                        if neighbor_device_type == "router":
                            mode = "routed"
                        elif neighbor_device_type == "host":
                            mode = "access"

                        discovered_neighbors[remote_ip]["interfaces"].append({
                            "interface": remote_port,
                            "description": f"Connected to {hostname} ({local_port})",
                            "mode": mode,
                            "mac_address": neighbor_mac
                        })

                # If IP resolved and not visited, add to queue for recursive crawl
                # (only if candidate switch type, to avoid login attempts on hosts/routers)
                if remote_ip not in visited and remote_ip not in queue:
                    is_candidate = neighbor_device_type in ["cisco_ios", "arista_eos", "hp_procurve", "huawei", "juniper_junos", "switch"]
                    if is_candidate:
                        known_device_types[remote_ip] = neighbor_device_type
                        queue.append(remote_ip)
                        print(f"Added switch neighbor {remote_ip} ({remote_host}) to crawl queue")

    # Add unmanaged neighbors to the nodes dictionary
    for remote_ip, data in discovered_neighbors.items():
        if remote_ip not in nodes:
            nodes[remote_ip] = {
                "hostname": data["hostname"],
                "device_type": data["device_type"],
                "running_config": f"# Non-managed device discovered via LLDP/CDP\n# IP: {remote_ip}\n# Hostname: {data['hostname']}",
                "vlans": [],
                "interfaces": data.get("interfaces") or []
            }

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