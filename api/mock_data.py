# api/mock_data.py

MOCK_DISCOVERY_DEVICES = [
    {
        "ip": "192.168.1.1",
        "hostname": "SW-CORE-01",
        "os_type": "cisco_ios",
        "model": "Catalyst 9300",
        "mac_address": "00:11:22:33:44:55",
        "uptime": "10 days, 2 hours",
        "interfaces": [
            {"name": "GigabitEthernet0/1", "ip_address": "192.168.1.1", "mac_address": "00:11:22:33:44:55", "status": "up"},
            {"name": "GigabitEthernet0/2", "ip_address": "", "mac_address": "00:11:22:33:44:56", "status": "up"}
        ],
        "neighbors": [
            {"neighbor_ip": "192.168.1.2", "neighbor_hostname": "SW-ACCESS-01", "local_interface": "GigabitEthernet0/2", "remote_interface": "GigabitEthernet1/0/1", "protocol": "cdp"}
        ]
    },
    {
        "ip": "192.168.1.2",
        "hostname": "SW-ACCESS-01",
        "os_type": "cisco_ios",
        "model": "Catalyst 2960",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "uptime": "5 days, 1 hour",
        "interfaces": [
            {"name": "GigabitEthernet1/0/1", "ip_address": "", "mac_address": "AA:BB:CC:DD:EE:FF", "status": "up"},
            {"name": "Vlan1", "ip_address": "192.168.1.2", "mac_address": "AA:BB:CC:DD:EE:FE", "status": "up"},
            {"name": "FastEthernet0/1", "ip_address": "", "mac_address": "AA:BB:CC:DD:EE:FD", "status": "up"}
        ],
        "neighbors": [
            {"neighbor_ip": "192.168.1.1", "neighbor_hostname": "SW-CORE-01", "local_interface": "GigabitEthernet1/0/1", "remote_interface": "GigabitEthernet0/2", "protocol": "cdp"}
        ]
    },
    {
        "ip": "192.168.1.50",
        "hostname": "HOST-A",
        "os_type": "linux",
        "model": "Ubuntu Server",
        "mac_address": "11:22:33:44:55:66",
        "uptime": "1 day, 0 hours",
        "interfaces": [
            {"name": "eth0", "ip_address": "192.168.1.50/24", "mac_address": "11:22:33:44:55:66", "status": "up"}
        ],
        "neighbors": []
    }
]

MOCK_CRAWL_RESULT = {
    "nodes": {
        "192.168.1.1": MOCK_DISCOVERY_DEVICES[0],
        "192.168.1.2": MOCK_DISCOVERY_DEVICES[1]
    },
    "edges": [
        {"source": "192.168.1.1", "target": "192.168.1.2"}
    ]
}

MOCK_EXTRACT_RESULT = {
    "running_config": """!
hostname SW-ACCESS-01
!
vlan 10
 name Users
!
vlan 20
 name Servers
!
interface GigabitEthernet1/0/1
 switchport mode trunk
!
interface FastEthernet0/1
 switchport mode access
 switchport access vlan 10
!
interface Vlan1
 ip address 192.168.1.2 255.255.255.0
!
end""",
    "interfaces": ["GigabitEthernet1/0/1", "FastEthernet0/1", "Vlan1"],
    "vlans": [{"id": 10, "name": "Users"}, {"id": 20, "name": "Servers"}]
}
