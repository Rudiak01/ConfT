# vendor_syntax.py

VENDOR_SYNTAX = {
    # -----------------------------------------
    # 1. CISCO IOS (Catalyst, ISR...)
    # -----------------------------------------
    "cisco_ios": {
        "read": {
            "vlans": "show vlan brief",
            "interfaces": "show interfaces switchport",
            "running": "show running-config"
        },
        "write": {
            "vlan_create": "vlan {id}",
            "vlan_name": "name {name}",
            "interface": "interface {iface}",
            "mode_access": "switchport mode access",
            "access_vlan": "switchport access vlan {vlan}",
            "mode_trunk": "switchport mode trunk",
            "trunk_allowed": "switchport trunk allowed vlan {vlans}"
        },
        "normalize_keys": {
            "vlans": {"vlan_id": "vlan_id", "name": "name"},
            "interfaces": {"interface": "interface", "access_vlan": "vlan", "admin_mode": "mode"}
        }
    },

    # -----------------------------------------
    # 2. ARISTA EOS (Datacenter)
    # -----------------------------------------
    "arista_eos": {
        "read": {
            "vlans": "show vlan",
            "interfaces": "show interfaces switchport",
            "running": "show running-config"
        },
        "write": {
            # Arista est un clone quasi-parfait d'IOS pour le CLI de base
            "vlan_create": "vlan {id}",
            "vlan_name": "name {name}",
            "interface": "interface {iface}",
            "mode_access": "switchport mode access",
            "access_vlan": "switchport access vlan {vlan}",
            "mode_trunk": "switchport mode trunk",
            "trunk_allowed": "switchport trunk allowed vlan {vlans}"
        },
        "normalize_keys": {
            "vlans": {"vlan_id": "vlan_id", "name": "name"},
            "interfaces": {"interface": "interface", "access_vlan": "vlan", "admin_mode": "mode"}
        }
    },

    # -----------------------------------------
    # 3. HUAWEI VRP (Switches CloudEngine, S-Series)
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
    # 4. HP PROCURVE / ARUBA OS-Switch
    # -----------------------------------------
    "hp_procurve": {
        "read": {
            "vlans": "show vlans",
            "interfaces": "show interfaces brief",
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
            "interfaces": {"port": "interface", "untagged": "vlan", "mode": "mode"}
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