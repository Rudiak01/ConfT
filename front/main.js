
const API_BASE = window.location.port === '5500' ? 'http://localhost:8000' : '';

/**
 * WebSDN Application Logic
 */
class SDNController {
    constructor() {
        this.nodes = [];
        this.links = [];
        this.selectedNode = null;
        this.nextNodeId = 1;
        this.connectionMode = false;

        // Initial Setup
        this.initGraph();

        this.log("Système prêt. Ajoutez des nœuds pour commencer.");
        document.getElementById('refresh-topology-btn')?.addEventListener('click', () => {
            this.fetchRealTopology();
        });
    }
    async fetchRealTopology() {
        try {
            this.log("Récupération de la topologie réelle via l'API...");
            
            const response = await fetch(`${API_BASE}/db/topology`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            // Valider la structure
            if (!Array.isArray(data.nodes) || !Array.isArray(data.links)) {
                throw new Error("Réponse API invalide");
            }

            this.nodes = data.nodes.map(n => ({
                id: n.id,
                label: n.hostname || n.label,
                type: n.device_type || n.type,
                ip: n.ip_address || n.ip,
                // Initialiser x/y pour éviter les bugs de position
                x: (Math.random() * 200) + (this.width / 2 - 100),
                y: (Math.random() * 200) + (this.height / 2 - 100)
            }));
            
            this.links = data.links.map(l => {
                // Find node ID by IP since backend link uses IP
                const sourceNode = this.nodes.find(n => n.ip === l.source_ip) || {id: l.source || l.source_ip};
                const targetNode = this.nodes.find(n => n.ip === l.target_ip) || {id: l.target || l.target_ip};
                return {
                    source: sourceNode.id,
                    target: targetNode.id,
                    source_interface: l.source_interface,
                    target_interface: l.target_interface
                };
            });

            // Mettre à jour la simulation avec les nouvelles données
            this.restartSimulation();
            this.log(`Topologie réelle chargée : ${this.nodes.length} nœuds, ${this.links.length} liens.`);
            
        } catch (error) {
            console.warn("[SDN] API topologie non disponible. Utilisation de la topologie aléatoire.", error);
            this.log("⚠️ Backend SDN indisponible → génération d'une topologie aléatoire.");
            this.generateRandomTopology();
        }
    }


    log(message) {
        const consoleEl = document.getElementById('console-log');
        const entry = document.createElement('div');
        const time = new Date().toLocaleTimeString();
        entry.textContent = `> [${time}] ${message}`;
        consoleEl.appendChild(entry);
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    toggleConnectionMode() {
        this.connectionMode = !this.connectionMode;
        const btn = document.getElementById('btn-connection-mode');
        if (this.connectionMode) {
            if(btn) {
                btn.classList.add('active');
                btn.textContent = "Mode Connexion: Actif";
            }
            this.log("Mode connexion activé. Cliquez sur deux nœuds pour les relier.");
        } else {
            if(btn) {
                btn.classList.remove('active');
                btn.textContent = "Activer Mode Connexion";
            }
            this.selectedNode = null;
            d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");
            this.log("Mode connexion désactivé.");
        }
    }

    initGraph() {
        // Configuration D3.js
        this.width = document.getElementById('graph-container').clientWidth;
        this.height = document.getElementById('graph-container').clientHeight;

        this.svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%")
            .call(d3.zoom().on("zoom", (e) => {
                this.g.attr("transform", e.transform);
            }))
            .on("dblclick", () => {
                this.selectedNode = null;
                d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");
                this.closePanel();
            });

        this.g = this.svg.append("g");

        // Simulation Force-Directed
        this.simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2))
            .force("collide", d3.forceCollide().radius(60));

        // Draw Links
        this.linkGroup = this.g.append("g").attr("class", "links");
        this.link = this.linkGroup.selectAll("line");

        // Draw Nodes
        this.nodeGroup = this.g.append("g").attr("class", "nodes");
        this.node = this.nodeGroup.selectAll(".node");

        // Tooltip setup
        this.tooltip = d3.select("#tooltip");

        // Lier la simulation aux éléments SVG
        this.simulation
            .nodes(this.nodes)
            .on("tick", () => {
                this.link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                this.node
                    .attr("transform", d => `translate(${d.x},${d.y})`);
            });

        // Lier les liens après avoir initialisé la simulation
        this.simulation.force("link").links(this.links);
    }

    createInitialTopology() {
        const controller = { id: "c1", label: "SDN-Ctrl", type: "switch", ip: "10.0.0.254" };

        const s1 = { id: `s${this.nextNodeId++}`, label: "S-01", type: "switch", ip: "192.168.1.1" };
        const s2 = { id: `s${this.nextNodeId++}`, label: "S-02", type: "switch", ip: "192.168.1.2" };

        const h1 = { id: `h${this.nextNodeId++}`, label: "Host A", type: "host", ip: "192.168.1.10" };
        const h2 = { id: `h${this.nextNodeId++}`, label: "Host B", type: "host", ip: "192.168.1.11" };
        const h3 = { id: `h${this.nextNodeId++}`, label: "Serveur Web", type: "host", ip: "192.168.1.20" };

        this.nodes.push(controller, s1, s2, h1, h2, h3);

        this.links.push(
            { source: controller, target: s1 },
            { source: s1, target: s2 },
            { source: s1, target: h1 },
            { source: s1, target: h2 },
            { source: s2, target: h3 }
        );

        this.restartSimulation();

        // Positionner manuellement au centre pour le démarrage
        this.nodes.forEach(n => {
            if (!n.x) n.x = this.width / 2 + (Math.random() * 100 - 50);
            if (!n.y) n.y = this.height / 2 + (Math.random() * 100 - 50);
        });

        // Forcer un tick initial pour afficher les éléments
        this.simulation.alpha(1).restart();
    }

    addNode(type) {
        this.width = document.getElementById('graph-container').clientWidth || 800;
        this.height = document.getElementById('graph-container').clientHeight || 600;
        this.simulation.force("center", d3.forceCenter(this.width / 2, this.height / 2));

        const id = type === 'switch' ? `s${this.nextNodeId++}` : `h${this.nextNodeId++}`;
        const label = type === 'switch' ? `S-${id.replace('s', '')}` : `Host ${id.replace('h', '')}`;
        const ip = type === 'switch' ? `192.168.1.${Math.floor(Math.random() * 254)}` : `10.0.0.${this.nextNodeId}`;

        // Position random near center
        const x = (Math.random() * 300) + (this.width / 2 - 150);
        const y = (Math.random() * 300) + (this.height / 2 - 150);

        const newNode = { id, label, type, ip, x, y };

        this.nodes.push(newNode);
        this.log(`Nouveau nœud créé : ${label} (${type})`);
        this.restartSimulation();
    }


    restartSimulation() {
        // Mise à jour des données pour les liens
        this.link = this.linkGroup.selectAll("line").data(this.links);
        this.link.exit().remove();

        const linkEnter = this.link.enter().append("line")
            .attr("stroke", "#95a5a6")
            .attr("stroke-width", 2);

        // Tooltip sur les liens
        linkEnter.on("mouseover", (event, d) => {
            const sourceNode = typeof d.source === 'object' ? d.source : this.nodes.find(n => n.id === d.source);
            const targetNode = typeof d.target === 'object' ? d.target : this.nodes.find(n => n.id === d.target);
            if (sourceNode && targetNode) {
                this.tooltip.style("opacity", 1);
                this.tooltip.html(`Lien : ${sourceNode.label} ↔ ${targetNode.label}`);
            }
        })
            .on("mousemove", (event) => {
                this.tooltip.style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", () => { this.tooltip.style("opacity", 0); });

        this.link = linkEnter.merge(this.link);

        // Mise à jour des données pour les nœuds
        this.node = this.nodeGroup.selectAll(".node").data(this.nodes, d => d.id);
        this.node.exit().remove();

        const nodeEnter = this.node.enter().append("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", (event, d) => this.dragstarted(event, d))
                .on("drag", (event, d) => this.dragged(event, d))
                .on("end", (event, d) => this.dragended(event, d)))
            .on("click", (event, d) => this.selectNode(d));

        nodeEnter.append("circle")
            .attr("r", d => d.type === 'switch' ? 25 : 15)
            .attr("fill", d => d.type === 'switch' ? "#e74c3c" : "#2ecc71")
            .attr("stroke", "white")
            .attr("stroke-width", 0);

        nodeEnter.append("text")
            .attr("dx", d => d.type === 'switch' ? 35 : 20)
            .attr("dy", ".35em")
            .text(d => d.label)
            .style("font-size", "14px")
            .style("font-weight", "bold")
            .style("pointer-events", "none");

        // Tooltip sur les nouveaux nœuds
        nodeEnter.on("mouseover", (event, d) => {
            this.tooltip.style("opacity", 1);
            this.tooltip.html(`ID: ${d.id}<br>Type: ${d.type.toUpperCase()}<br>IP: ${d.ip}`);
        })
            .on("mousemove", (event) => {
                this.tooltip.style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", () => { this.tooltip.style("opacity", 0); });

        this.node = nodeEnter.merge(this.node);

        // Mise à jour de la simulation
        this.simulation.nodes(this.nodes)
            .force("link").links(this.links);

        this.simulation.alpha(1).restart();
    }

    generateRandomTopology() {
        this.nodes = [];
        this.links = [];
        this.nextNodeId = 1;
        this.selectedNode = null;

        this.width = document.getElementById('graph-container').clientWidth || 800;
        this.height = document.getElementById('graph-container').clientHeight || 600;
        this.simulation.force("center", d3.forceCenter(this.width / 2, this.height / 2));

        const switches = Math.floor(Math.random() * 16) + 5; // 5 to 20 switches

        let prevSwitch = null;
        for (let i = 0; i < switches; i++) {
            const sId = `s${this.nextNodeId++}`;
            const sNode = {
                id: sId, label: `S-${i + 1}`, type: "switch", ip: `192.168.${i}.1`,
                x: Math.random() * this.width, y: Math.random() * this.height
            };
            this.nodes.push(sNode);

            if (prevSwitch) {
                this.links.push({ source: prevSwitch.id, target: sNode.id });
            }

            const hostsPerSwitch = Math.floor(Math.random() * 9) + 2; // 2 to 10 hosts
            for (let j = 0; j < hostsPerSwitch; j++) {
                const hId = `h${this.nextNodeId++}`;
                const hNode = {
                    id: hId, label: `Host ${j + 1}`, type: "host", ip: `192.168.${i}.${j + 10}`,
                    x: sNode.x + (Math.random() * 100 - 50), y: sNode.y + 100
                };
                this.nodes.push(hNode);
                this.links.push({ source: sNode.id, target: hNode.id });
            }

            prevSwitch = sNode;
        }

        if (switches > 2) {
            this.links.push({ source: this.nodes[0].id, target: prevSwitch.id });
        }

        this.log("Topologie aléatoire générée localement. Synchronisation avec la DB...");
        this.restartSimulation();

        // Sync with backend
        const payloadNodes = this.nodes.map(n => {
            let interfaces = [];
            
            // Compter le nombre exact de liens connectés à ce nœud
            const connectedLinksCount = this.links.filter(l => 
                (typeof l.source === 'object' ? l.source.id : l.source) === n.id || 
                (typeof l.target === 'object' ? l.target.id : l.target) === n.id
            ).length;

            if (n.type === 'switch') {
                for (let k = 1; k <= connectedLinksCount; k++) {
                    interfaces.push({
                        name: `FastEthernet0/${k}`,
                        description: "Auto-generated",
                        mode: Math.random() > 0.5 ? "access" : "trunk",
                        vlan_id: Math.floor(Math.random() * 100) + 1
                    });
                }
            } else {
                for (let k = 1; k <= (connectedLinksCount || 1); k++) {
                    interfaces.push({
                        name: k === 1 ? "eth0" : `eth${k-1}`,
                        description: "Auto-generated host interface",
                        mode: "access",
                        vlan_id: 1
                    });
                }
            }
            return {
                ip: n.ip,
                label: n.label,
                type: n.type,
                interfaces: interfaces
            };
        });

        const ifaceCounter = {};
        const payloadLinks = this.links.map(l => {
            const sNode = this.nodes.find(n => n.id === (typeof l.source === 'object' ? l.source.id : l.source));
            const tNode = this.nodes.find(n => n.id === (typeof l.target === 'object' ? l.target.id : l.target));
            
            let sIface = "", tIface = "";
            if (sNode) {
                ifaceCounter[sNode.id] = (ifaceCounter[sNode.id] || 0) + 1;
                sIface = sNode.type === 'switch' ? `FastEthernet0/${ifaceCounter[sNode.id]}` : (ifaceCounter[sNode.id] === 1 ? "eth0" : `eth${ifaceCounter[sNode.id]-1}`);
            }
            if (tNode) {
                ifaceCounter[tNode.id] = (ifaceCounter[tNode.id] || 0) + 1;
                tIface = tNode.type === 'switch' ? `FastEthernet0/${ifaceCounter[tNode.id]}` : (ifaceCounter[tNode.id] === 1 ? "eth0" : `eth${ifaceCounter[tNode.id]-1}`);
            }

            return {
                source_ip: sNode ? sNode.ip : "",
                target_ip: tNode ? tNode.ip : "",
                source_interface: sIface,
                target_interface: tIface
            };
        });

        fetch(`${API_BASE}/db/topology/random`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nodes: payloadNodes, links: payloadLinks })
        }).then(res => {
            if (res.ok) {
                this.log("Topologie aléatoire synchronisée avec la base de données.");
                // Re-fetch to get the real integer IDs from the database
                this.fetchRealTopology();
            } else {
                this.log("Erreur de synchronisation avec la DB.");
            }
        }).catch(err => {
            this.log("Erreur réseau (Sync DB): " + err.message);
        });
    }

    resetNetwork() {
        this.nodes = [];
        this.links = [];
        this.nextNodeId = 1;
        this.selectedNode = null;

        this.restartSimulation();
    }

    selectNode(node) {
        if (this.selectedNode === node) {
            this.selectedNode = null;
            d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");
            this.log(`Désélection de ${node.label}`);
            this.closePanel();
        } else {
            if (this.selectedNode) {
                // Connection mode removed
            }

            d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");

            const nodeElement = this.node.nodes().find(n => n.__data__ && n.__data__.id === node.id);
            if (nodeElement) {
                d3.select(nodeElement).select("circle")
                    .style("stroke-width", 4)
                    .style("stroke", "#f1c40f");
            }

            this.selectedNode = node;
            this.log(`Sélection : ${node.label} (IP: ${node.ip})`);
            this.fetchSelectedNode();
        }
    }

    // Drag Functions
    dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }


    installFlowRule() {
        this.log("Installation d'une règle de flot... (simulation)");
    }

    async fetchSelectedNode() {
        if (!this.selectedNode) return;
        
        if (this.currentEditingInterfaceId) {
            this.autoSaveInterface(this.currentEditingInterfaceId);
        }

        try {
            const nodeId = this.selectedNode.id;
            this.log(`Récupération des interfaces pour le nœud ID: ${nodeId}...`);
            const response = await fetch(`${API_BASE}/db/node/${nodeId}/interfaces`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            this.currentInterfaces = await response.json();
            this.openPanel();
            this.renderInterfacesPanel();
        } catch (error) {
            this.log(`Erreur lors de la récupération des interfaces: ${error.message}`);
        }
    }

    openPanel() {
        const panel = document.getElementById('bottom-panel');
        if (panel) {
            document.getElementById('panel-title').textContent = `Interfaces - ${this.selectedNode?.label || ''}`;
            panel.classList.add('open');
        }
    }

    closePanel() {
        if (this.currentEditingInterfaceId) {
            this.autoSaveInterface(this.currentEditingInterfaceId);
        }
        const panel = document.getElementById('bottom-panel');
        if (panel) panel.classList.remove('open');
        if (this.linkGroup) {
            this.linkGroup.selectAll("line")
                .style("stroke", "#95a5a6")
                .style("stroke-width", 2);
        }
        this.currentInterfaces = [];
        this.currentEditingInterfaceId = null;
    }

    renderInterfacesPanel() {
        const list = document.getElementById('interfaces-list');
        if (!list) return;
        list.innerHTML = '';
        if (!this.currentInterfaces || this.currentInterfaces.length === 0) {
            list.innerHTML = '<p style="color: #666; text-align:center;">Aucune interface trouvée.</p>';
            return;
        }

        this.currentInterfaces.forEach(iface => {
            const isEditing = this.currentEditingInterfaceId === iface.id;
            const card = document.createElement('div');
            card.className = `interface-card ${isEditing ? 'editing' : ''}`;
            
            if (isEditing) {
                card.innerHTML = `
                    <div class="iface-field">
                        <span class="iface-label">Nom</span>
                        <input type="text" class="iface-input" id="edit-name-${iface.id}" value="${iface.name || ''}" />
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Description</span>
                        <input type="text" class="iface-input" id="edit-desc-${iface.id}" value="${iface.description || ''}" />
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Mode</span>
                        <select class="iface-input" id="edit-mode-${iface.id}">
                            <option value="access" ${iface.mode === 'access' ? 'selected' : ''}>Access</option>
                            <option value="trunk" ${iface.mode === 'trunk' ? 'selected' : ''}>Trunk</option>
                            <option value="dynamic auto" ${iface.mode === 'dynamic auto' ? 'selected' : ''}>Dynamic Auto</option>
                            <option value="static access" ${iface.mode === 'static access' ? 'selected' : ''}>Static Access</option>
                        </select>
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">VLAN</span>
                        <input type="number" class="iface-input" id="edit-vlan-${iface.id}" value="${iface.vlan_id || ''}" />
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Allowed VLANs</span>
                        <input type="text" class="iface-input" id="edit-allowed-${iface.id}" value="${iface.allowed_vlans || ''}" placeholder="ex: 10,20,30" />
                    </div>
                `;
            } else {
                card.innerHTML = `
                    <div class="iface-status ${iface.mode ? 'active' : ''}"></div>
                    <div class="iface-field">
                        <span class="iface-label">Nom</span>
                        <span class="iface-value">${iface.name || '-'}</span>
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Mode</span>
                        <span class="iface-value">${iface.mode || '-'}</span>
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">VLAN</span>
                        <span class="iface-value">${iface.vlan_id || '-'}</span>
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Description</span>
                        <span class="iface-value">${iface.description || '-'}</span>
                    </div>
                `;
                card.onclick = () => this.editInterface(iface.id);
            }
            list.appendChild(card);
        });
    }

    editInterface(id) {
        if (this.currentEditingInterfaceId && this.currentEditingInterfaceId !== id) {
            this.autoSaveInterface(this.currentEditingInterfaceId);
        }
        this.currentEditingInterfaceId = id;
        this.renderInterfacesPanel();

        // Highlight link on the graph
        const selectedInterface = this.currentInterfaces.find(i => i.id === id);
        if (selectedInterface && this.selectedNode) {
            const ifaceName = selectedInterface.name;
            const nodeId = this.selectedNode.id;

            let matchFound = false;
            this.linkGroup.selectAll("line")
                .style("stroke", d => {
                    const srcMatch = String(d.source.id) === String(nodeId) && d.source_interface === ifaceName;
                    const tgtMatch = String(d.target.id) === String(nodeId) && d.target_interface === ifaceName;
                    if (srcMatch || tgtMatch) matchFound = true;
                    return (srcMatch || tgtMatch) ? "#e74c3c" : "#95a5a6";
                })
                .style("stroke-width", d => {
                    const srcMatch = String(d.source.id) === String(nodeId) && d.source_interface === ifaceName;
                    const tgtMatch = String(d.target.id) === String(nodeId) && d.target_interface === ifaceName;
                    return (srcMatch || tgtMatch) ? 4 : 2;
                });
                
            this.log(`Recherche de liens pour l'interface ${ifaceName}... ${matchFound ? 'Trouvé!' : 'Aucun lien actif'}`);
        }
    }

    async autoSaveInterface(id) {
        const nameEl = document.getElementById(`edit-name-${id}`);
        const descEl = document.getElementById(`edit-desc-${id}`);
        const modeEl = document.getElementById(`edit-mode-${id}`);
        const vlanEl = document.getElementById(`edit-vlan-${id}`);
        const allowedEl = document.getElementById(`edit-allowed-${id}`);

        if (!nameEl) return;

        const data = {
            name: nameEl.value,
            description: descEl.value,
            mode: modeEl.value,
            vlan_id: parseInt(vlanEl.value) || null,
            allowed_vlans: allowedEl.value
        };

        const idx = this.currentInterfaces.findIndex(i => i.id === id);
        if (idx !== -1) {
            this.currentInterfaces[idx] = { ...this.currentInterfaces[idx], ...data };
        }
        
        // Remove currently editing id before rendering so it shows as a normal card
        this.currentEditingInterfaceId = null;
        this.renderInterfacesPanel();
        
        this.log(`Sauvegarde de l'interface ${data.name}...`);

        try {
            const response = await fetch(`${API_BASE}/db/interface/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!response.ok) throw new Error("Erreur serveur lors de la sauvegarde");
            this.log(`Interface ${data.name} sauvegardée avec succès.`);
        } catch (error) {
            this.log(`Erreur de sauvegarde: ${error.message}`);
        }
    }

    fetchStatistics() {
        this.log("Récupération des statistiques...");
        document.getElementById("stats-output").innerText = "Trafic: Normal | Paquets traités: " + Math.floor(Math.random() * 10000);
    }
}

// Initialize App
const app = new SDNController();

// Helper for UI interaction — sélection de nœud depuis le dropdown
function handleSelectionChange() {
    const val = document.getElementById('nodeSelector').value;
    if (!val) return;

    // Trouver le nœud et le sélectionner visuellement
    const node = app.nodes.find(n => n.id === val);
    if (node) {
        app.selectNode(node);
    }
}
