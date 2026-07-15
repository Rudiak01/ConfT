# vendor_syntax.py

VENDOR_SYNTAX = {
    # -----------------------------------------
    # 1. CISCO IOS (Le plus complet via TextFSM)
    # -----------------------------------------
    "cisco_ios": {
        "read": {
            "vlans": "show vlan brief",
            "interfaces": "show interfaces switchport",
            "mac": "show mac address-table",
            "arp": "show ip arp",
            "lldp": "show cdp neighbors detail", # use detail to get neighbor IPs
            "routes": "show ip route",
            "poe": "show power inline",
            "port_channels": "show etherchannel summary",
            "stp": "show spanning-tree",
            "running": "show running-config" # Toujours en dernier
        },
        "write": {
            # VLAN & Switchport
            "vlan_create": "vlan {id}",
            "vlan_name": "name {name}",
            "interface": "interface {iface}",
            "desc": "description {desc}",
            "mode_access": "switchport mode access",
            "access_vlan": "switchport access vlan {vlan}",
            "voice_vlan": "switchport voice vlan {vlan}",
            "portfast": "spanning-tree portfast",
            "mode_trunk": "switchport mode trunk",
            "trunk_allowed": "switchport trunk allowed vlan {vlans}",
            # Routage statique
            "route": "ip route {network} {mask} {nexthop}",
            # Spanning-Tree global
            "stp_mode": "spanning-tree mode {mode}", # pvst, rapid-pvst
            "stp_root": "spanning-tree vlan {vlan} root primary"
        },
        "normalize_keys": {
            "vlans": {"vlan_id": "vlan_id", "vlan_name": "name", "status": "status"},
            "interfaces": {"interface": "interface", "access_vlan": "vlan", "admin_mode": "mode", "switchport": "enabled"},
            "mac": {"destination_address": "mac", "vlan": "vlan", "destination_port": "interface"},
            "arp": {"address": "ip", "mac": "mac", "interface": "interface"},
            "lldp": {
                "neighbor_name": "neighbor_name",
                "mgmt_address": "management_ip",
                "local_interface": "local_port",
                "neighbor_interface": "remote_port"
            },
            "cdp": {"destination_host": "neighbor_name", "local_interface": "local_port", "neighbor_interface": "remote_port"},
            "routes": {"network": "network", "mask": "mask", "nexthop_ip": "nexthop", "protocol": "protocol"},
            "poe": {"interface": "interface", "oper": "status", "power": "watts"},
            "port_channels": {"po_name": "channel", "po_protocol": "protocol", "ports": "members"},
            "stp": {"vlan_id": "vlan", "root_mac": "root_bridge", "bridge_mac": "local_bridge"}
        }
    },

    # -----------------------------------------
    # 2. ARISTA EOS
    # -----------------------------------------
    "arista_eos": {
        "read": {
            "vlans": "show vlan",
            "interfaces": "show interfaces switchport",
            "mac": "show mac address-table",
            "arp": "show ip arp",
            "lldp": "show lldp neighbors detail",
            "routes": "show ip route",
            "running": "show running-config"
        },
        "write": {
            "vlan_create": "vlan {id}",
            "vlan_name": "name {name}",
            "interface": "interface {iface}",
            "mode_access": "switchport mode access",
            "access_vlan": "switchport access vlan {vlan}",
            "mode_trunk": "switchport mode trunk",
            "trunk_allowed": "switchport trunk allowed vlan {vlans}",
            "route": "ip route {network}/{mask} {nexthop}" # Syntaxe CIDR courante chez Arista
        },
        "normalize_keys": {
            "vlans": {"vlan_id": "vlan_id", "name": "name"},
            "interfaces": {"interface": "interface", "access_vlan": "vlan", "admin_mode": "mode"},
            "mac": {"mac_address": "mac", "vlan": "vlan", "port": "interface"},
            "arp": {"address": "ip", "mac_address": "mac", "interface": "interface"},
            "lldp": {
                "port": "local_port", 
                "neighbor_device": "neighbor_name", 
                "neighbor_port": "remote_port",
                "neighbor_name": "neighbor_name",
                "mgmt_address": "management_ip",
                "local_interface": "local_port",
                "neighbor_interface": "remote_port"
            },
            "routes": {"network": "network", "nexthop_ip": "nexthop"}
        }
    },

    # -----------------------------------------
    # 3. HP PROCURVE / ARUBA
    # -----------------------------------------
    "hp_procurve": {
        "read": {
            "vlans": "show vlans",
            "interfaces": "show interfaces brief",
            "lldp": "show lldp info remote-device",
            "mac": "show mac-address",
            "running": "show running-config"
        },
        "write": {
            "vlan_create": "vlan {id}",
            "vlan_name": "name {name}",
            "interface": "interface {iface}",
            "mode_access": "untagged vlan {vlan}",
            "mode_trunk": "tagged vlan {vlans}"
        },
        "normalize_keys": {
            "vlans": {"vlan_id": "vlan_id", "name": "name"},
            "interfaces": {"port": "interface", "untagged": "vlan", "mode": "mode"},
            "mac": {"mac_address": "mac", "port": "interface"}
        }
    },

    # -----------------------------------------
    # 4. HUAWEI VRP (Switches CloudEngine, S-Series)
    # -----------------------------------------
    "huawei": {
        "read": {
            "vlans": "display vlan",
            "interfaces": "display interface",
            "running": "display current-configuration"
        },
        "write": {
            "vlan_create": "vlan {id}",
            "vlan_name": "name {name}",
            "interface": "interface {iface}",
            "mode_access": "port link-type access",
            "access_vlan": "port default vlan {vlan}",
            "mode_trunk": "port link-type trunk",
            "trunk_allowed": "port trunk allow-pass vlan {vlans}"
        },
        "normalize_keys": {
            "vlans": {"vlan_id": "vlan_id", "name": "name"},
            "interfaces": {"interface": "interface", "pvid": "vlan", "link_type": "mode"}
        }
    },

    # -----------------------------------------
    # 5. JUNIPER JUNOS (Ex/QFX Series)
    # -----------------------------------------
    "juniper_junos": {
        "read": {
            "vlans": "show vlans",
            "interfaces": "show interfaces ethernet-switching",
            "running": "show configuration"
        },
        "write": {
            # Attention: Junos est hiérarchique.
            "vlan_create": "set vlans VLAN{id} vlan-id {id}",
            "vlan_name": "set vlans VLAN{id} description {name}",
            "interface": "edit interfaces {iface}",
            "mode_access": "set unit 0 family ethernet-switching interface-mode access",
            "access_vlan": "set unit 0 family ethernet-switching vlan members {vlan}",
            "mode_trunk": "set unit 0 family ethernet-switching interface-mode trunk",
            "trunk_allowed": "set unit 0 family ethernet-switching vlan members [{vlans}]"
        },
        "normalize_keys": {
            "vlans": {"vlan_name": "name", "vlan_id": "vlan_id"},
            "interfaces": {"interface": "interface", "vlan_members": "vlan"}
        }
    }
}