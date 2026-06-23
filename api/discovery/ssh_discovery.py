import paramiko
import re
from datetime import datetime
from config import Config
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_ssh_command(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8')

def discover_device(ip: str) -> dict:
    try:
        ssh = paramiko.SSHClient()
        # TODO SÉCURITÉ: AutoAddPolicy accepte n'importe quelle clé SSH (vulnérable MITM).
        # En production, utiliser paramiko.RejectPolicy() + un fichier known_hosts vérifié.
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ip,
            port=Config.SSH_PORT,
            username=Config.SSH_USER,
            password=Config.SSH_PASS,
            timeout=Config.SSH_TIMEOUT
        )

        # 1. Hostname & basic info (Linux/Unix-like)
        hostname = run_ssh_command(ssh, "hostname").strip()
        os_type = "linux" if "Linux" in run_ssh_command(ssh, "uname -a") else "unknown"

        # Try to detect model/vendor
        model = ""
        try:
            model = run_ssh_command(ssh, "cat /etc/os-release | grep PRETTY_NAME").strip().split('"')[1]
        except Exception:
            pass

        # 2. Interfaces & IPs (Linux)
        ifaces_output = run_ssh_command(ssh, "ip -o addr show | awk '{print $2, $4}'")
        interfaces = []
        for line in ifaces_output.strip().split('\n'):
            parts = line.split()
            if len(parts) == 2:
                name, ip_cidr = parts
                ip_addr = ip_cidr.split('/')[0]
                # Get MAC (simplified)
                mac = run_ssh_command(ssh, f"cat /sys/class/net/{name}/address").strip() or "unknown"
                status = "up" if "UP" in run_ssh_command(ssh, f"cat /sys/class/net/{name}/flags") else "down"
                interfaces.append({
                    "name": name,
                    "ip_address": ip_addr,
                    "mac_address": mac,
                    "status": status
                })

        # 3. Neighbors (LLDP + CDP fallback)
        neighbors = []

        # A. Try LLDP first (Linux, modern switches)
        try:
            lldp_output = run_ssh_command(ssh, "lldpctl -f json")
            if lldp_output.strip():
                import json
                data = json.loads(lldp_output)
                for port in data.get("lldp", {}).get("port", []):
                    local_if = port.get("ifname", "")
                    for neighbor in port.get("neighbor", []):
                        neighbors.append({
                            "neighbor_ip": neighbor.get("mgmt-ip", ""),
                            "neighbor_hostname": neighbor.get("system-name", ""),
                            "local_interface": local_if,
                            "remote_interface": neighbor.get("port-desc", ""),
                            "protocol": "lldp"
                        })
        except Exception as e:
           
            logger.error(f"[CDP] Failed for {ip}: {e}")

        # B. Fallback: CDP (Cisco/NX-OS/Juniper)
        try:
            cdp_output = run_ssh_command(ssh, "show cdp neighbors detail")
            if cdp_output and "Device ID" in cdp_output:
                logger.info(f"[CDP] Parsing CDP output for {ip}...")
                # Parse CDP output (Cisco-style)
                blocks = re.split(r"\n(?=Device ID:)", cdp_output.strip())
                for block in blocks:
                    if not block.strip():
                        continue

                    neighbor_hostname = ""
                    neighbor_ip = ""
                    local_if = ""
                    remote_if = ""

                    lines = block.strip().split('\n')
                    for line in lines:
                        # Device ID: SW-CORE-01 (VLAN99)
                        m = re.match(r"Device ID:\s*(\S+)", line, re.IGNORECASE)
                        if m:
                            neighbor_hostname = m.group(1).split()[0]  # keep only first token

                        # IP address: 192.168.1.2
                        m = re.match(r"IP address:\s*(\d+\.\d+\.\d+\.\d+)", line, re.IGNORECASE)
                        if m:
                            neighbor_ip = m.group(1)

                        # Interface: GigabitEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/2
                        m = re.match(r"Interface:\s*(\S+).*Port ID \(outgoing port\):\s*(\S+)", line, re.IGNORECASE)
                        if m:
                            local_if = m.group(1)
                            remote_if = m.group(2)

                    # Only add if we have minimal info
                    if neighbor_hostname and (neighbor_ip or local_if):
                        neighbors.append({
                            "neighbor_ip": neighbor_ip,
                            "neighbor_hostname": neighbor_hostname,
                            "local_interface": local_if,
                            "remote_interface": remote_if,
                            "protocol": "cdp"
                        })
        except Exception as e:
            logger.error(f"[CDP] Failed for {ip}: {e}")

        # 4. Uptime
        uptime = run_ssh_command(ssh, "uptime -p").strip()

        ssh.close()
        return {
            "ip": ip,
            "hostname": hostname or ip,
            "os_type": os_type,
            "model": model or "unknown",
            "mac_address": interfaces[0]["mac_address"] if interfaces else "unknown",
            "uptime": uptime,
            "interfaces": interfaces,
            "neighbors": neighbors
        }

    except Exception as e:
        return {
            "ip": ip,
            "error": str(e)
        }
