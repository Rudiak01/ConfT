from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Device, Interface, Neighbor
from discovery.ssh_discovery import discover_device
from config import Config

import ipaddress
import threading
import queue

app = Flask(__name__)
app.config.from_object(Config)

# DB setup
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# Ensure tables exist
Base.metadata.create_all(engine)


def discover_network(start_ip: str, end_ip: str):
    """Scan IP range via SSH (threaded)"""
    start = int(ipaddress.ip_address(start_ip))
    end = int(ipaddress.ip_address(end_ip))

    results_queue = queue.Queue()

    def worker(ip_int):
        ip_str = str(ipaddress.ip_address(ip_int))
        result = discover_device(ip_str)
        results_queue.put((ip_str, result))

    threads = []
    for ip_int in range(start, end + 1):
        t = threading.Thread(target=worker, args=(ip_int,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Store results
    while not results_queue.empty():
        ip_str, data = results_queue.get()
        store_device(ip_str, data)


def store_device(ip: str, data: dict):
    """Store device + interfaces + neighbors in DB"""
    try:
        dev = session.query(Device).filter_by(ip=ip).first()
        if not dev:
            dev = Device(
                ip=data["ip"],
                hostname=data.get("hostname", ""),
                os_type=data.get("os_type", "unknown"),
                model=data.get("model", ""),
                mac_address=data.get("mac_address", ""),
                uptime=data.get("uptime", "")
            )
            session.add(dev)
            session.flush()

        # Update interfaces
        for iface in data.get("interfaces", []):
            existing = session.query(Interface).filter_by(
                device_id=dev.id, name=iface["name"]
            ).first()
            if not existing:
                existing = Interface(device_id=dev.id)
                session.add(existing)
            existing.name = iface["name"]
            existing.ip_address = iface.get("ip_address", "")
            existing.mac_address = iface.get("mac_address", "")
            existing.status = iface.get("status", "unknown")
        # Remove old interfaces not in new list
        current_ifaces = {i["name"] for i in data.get("interfaces", [])}
        for iface in dev.interfaces:
            if iface.name not in current_ifaces:
                session.delete(iface)

        # Store neighbors (LLDP/CDP)
        for nb in data.get("neighbors", []):
            existing_nb = session.query(Neighbor).filter_by(
                device_id=dev.id,
                neighbor_ip=nb["neighbor_ip"],
                local_interface=nb["local_interface"]
            ).first()
            if not existing_nb:
                existing_nb = Neighbor(device_id=dev.id)
                session.add(existing_nb)
            existing_nb.neighbor_hostname = nb.get("neighbor_hostname", "")
            existing_nb.remote_interface = nb.get("remote_interface", "")
            existing_nb.protocol = nb.get("protocol", "lldp")
        # Remove old neighbors
        current_neighbors = {(nb["neighbor_ip"], nb["local_interface"]) for nb in data.get("neighbors", [])}
        for nb in dev.neighbors:
            if (nb.neighbor_ip, nb.local_interface) not in current_neighbors:
                session.delete(nb)

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Failed to store device {ip}: {e}")


@app.route('/api/discover', methods=['POST'])
def discover():
    data = request.get_json() or {}
    start_ip = data.get("start_ip", "192.168.1.1")
    end_ip = data.get("end_ip", "192.168.1.254")

    # Launch discovery in background
    thread = threading.Thread(target=discover_network, args=(start_ip, end_ip))
    thread.start()

    return jsonify({
        "status": "discovery started",
        "range": f"{start_ip} - {end_ip}"
    }), 202


@app.route('/api/devices', methods=['GET'])
def get_devices():
    devices = session.query(Device).all()
    result = []
    for dev in devices:
        device_data = {
            "id": dev.id,
            "ip": dev.ip,
            "hostname": dev.hostname,
            "os_type": dev.os_type,
            "model": dev.model,
            "mac_address": dev.mac_address,
            "uptime": dev.uptime,
            "interfaces": [
                {
                    "name": i.name,
                    "ip_address": i.ip_address,
                    "mac_address": i.mac_address,
                    "status": i.status
                } for i in dev.interfaces
            ],
            "neighbors": [
                {
                    "neighbor_ip": n.neighbor_ip,
                    "neighbor_hostname": n.neighbor_hostname,
                    "local_interface": n.local_interface,
                    "remote_interface": n.remote_interface,
                    "protocol": n.protocol
                } for n in dev.neighbors
            ]
        }
        result.append(device_data)
    return jsonify(result)


@app.route('/api/device/<ip>', methods=['GET'])
def get_device(ip):
    dev = session.query(Device).filter_by(ip=ip).first()
    if not dev:
        return jsonify({"error": "Device not found"}), 404

    device_data = {
        "id": dev.id,
        "ip": dev.ip,
        "hostname": dev.hostname,
        "os_type": dev.os_type,
        "model": dev.model,
        "mac_address": dev.mac_address,
        "uptime": dev.uptime,
        "interfaces": [
            {
                "name": i.name,
                "ip_address": i.ip_address,
                "mac_address": i.mac_address,
                "status": i.status
            } for i in dev.interfaces
        ],
        "neighbors": [
            {
                "neighbor_ip": n.neighbor_ip,
                "neighbor_hostname": n.neighbor_hostname,
                "local_interface": n.local_interface,
                "remote_interface": n.remote_interface,
                "protocol": n.protocol
            } for n in dev.neighbors
        ]
    }
    return jsonify(device_data)


@app.route('/api/topology', methods=['GET'])
def get_topology():
    """
    Renvoie une topologie JSON compatible D3.js / Cytoscape.
    - Nodes : tous les devices + hosts (via interfaces connectées)
    - Links : relations LLDP/CDP + host→switch
    """
    try:
        # 1. Récupérer tous les devices
        devices = session.query(Device).all()
        if not devices:
            return jsonify({"nodes": [], "links": []})

        node_map = {}  # ip → node_id (pour éviter doublons)
        nodes = []
        links = set()  # (source, target) en tuples triés pour éviter doublons
        next_node_id = 1

        # 2. Créer les nœuds principaux (switchs/routeurs)
        for dev in devices:
            node_id = f"n{next_node_id}"
            label = dev.hostname or dev.ip.split('.')[-1]  # last octet fallback
            node_type = "switch"
            if "router" in (dev.model or "").lower() or "router" in (dev.os_type or "").lower():
                node_type = "router"
            elif "host" in (dev.model or "").lower() or dev.os_type == "linux":
                # On distingue les hosts des switchs par leur nombre d'interfaces
                if len(dev.interfaces) <= 2:
                    node_type = "host"

            node_map[dev.ip] = {
                "id": node_id,
                "ip": dev.ip,
                "label": label,
                "type": node_type,
                "interfaces": [i.name for i in dev.interfaces]
            }
            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type,
                "ip": dev.ip
            })
            next_node_id += 1

        # 3. Créer les liens à partir des voisins (LLDP/CDP)
        for dev in devices:
            src_id = node_map[dev.ip]["id"]
            for neighbor in dev.neighbors:
                if neighbor.neighbor_ip not in node_map:
                    continue  # skip si voisin non découvert

                dst_id = node_map[neighbor.neighbor_ip]["id"]

                # Éviter les liens doubles (A→B et B→A)
                link_key = tuple(sorted([src_id, dst_id]))
                links.add(link_key)

        # 4. Ajouter les hosts connectés aux switchs (via IP dans même subnet)
        #    → On suppose qu’un host est un device avec ≤2 interfaces ET pas de voisins CDP/LLDP
        for dev in devices:
            if len(dev.interfaces) <= 2 and not dev.neighbors:
                # C’est probablement un host → le relier au switch le plus proche (même subnet)
                for other_dev in devices:
                    if other_dev == dev or len(other_dev.interfaces) < 3:
                        continue  # skip si pas un switch

                    # Vérifier si même sous-réseau
                    try:
                        dev_ip = ipaddress.ip_address(dev.ip.split('/')[0])
                        other_ip = ipaddress.ip_address(other_dev.ip.split('/')[0])

                        # Trouver une interface de l'autre device dans le même subnet
                        for iface in other_dev.interfaces:
                            if not iface.ip_address or '/' in iface.ip_address:
                                continue  # skip si pas IPv4 simple
                            try:
                                net = ipaddress.ip_network(f"{iface.ip_address}/24", strict=False)
                                if dev_ip in net:
                                    src_id = node_map[dev.ip]["id"]
                                    dst_id = node_map[other_dev.ip]["id"]
                                    link_key = tuple(sorted([src_id, dst_id]))
                                    links.add(link_key)
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue

        # 5. Convertir les liens en format D3.js (source/target)
        d3_links = [
            {"source": src, "target": dst}
            for src, dst in sorted(links)
        ]

        return jsonify({
            "nodes": nodes,
            "links": d3_links
        })

    except Exception as e:
        session.rollback()
        logger.error(f"[Topology] Error: {e}")
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
