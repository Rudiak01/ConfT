
/**
 * WebSDN Application Logic
 */
class SDNController {
    constructor() {
        this.nodes = [];
        this.links = [];
        this.selectedNode = null;
        this.nextNodeId = 1;

        // Initial Setup
        this.initGraph();
        this.updateUI();
        this.log("Système prêt. Ajoutez des nœuds pour commencer.");
        document.getElementById('refresh-topology-btn')?.addEventListener('click', () => {
            this.fetchRealTopology();
        });
    }
    async fetchRealTopology() {
        try {
            this.log("Récupération de la topologie réelle via l'API...");
            
            const response = await fetch('/api/topology');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            // Valider la structure
            if (!Array.isArray(data.nodes) || !Array.isArray(data.links)) {
                throw new Error("Réponse API invalide");
            }

            this.nodes = data.nodes.map(n => ({
                id: n.id,
                label: n.label,
                type: n.type,
                ip: n.ip,
                // Initialiser x/y pour éviter les bugs de position
                x: (Math.random() * 200) + (this.width / 2 - 100),
                y: (Math.random() * 200) + (this.height / 2 - 100)
            }));
            
            this.links = data.links.map(l => ({
                source: l.source,
                target: l.target
            }));

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

    initGraph() {
        // Configuration D3.js
        this.width = document.getElementById('graph-container').clientWidth;
        this.height = document.getElementById('graph-container').clientHeight;

        this.svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%")
            .call(d3.zoom().on("zoom", (e) => {
                // Correction: Utiliser 'this' pour accéder à g
                this.g.attr("transform", e.transform);
            }))
            .on("dblclick", () => {
                this.selectedNode = null;
                d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");
            });

        // Correction: Stocker 'g' comme propriété de l'objet pour y accéder partout
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

        // Correction: Lier la simulation aux éléments SVG
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
        // Correction: Initialiser x/y pour que la simulation ait un point de départ
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

        // Correction: Redessiner les éléments avec les nouvelles données
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
        this.updateUI();
    }

    createLink(nodeA, nodeB) {
        if (!nodeA || !nodeB || nodeA === nodeB) return;

        // Check if link exists
        const exists = this.links.some(l => {
            const sId = typeof l.source === 'object' ? l.source.id : l.source;
            const tId = typeof l.target === 'object' ? l.target.id : l.target;
            return (sId === nodeA.id && tId === nodeB.id) || (sId === nodeB.id && tId === nodeA.id);
        });

        if (!exists) {
            this.links.push({ source: nodeA.id, target: nodeB.id });
            this.log(`Lien créé entre ${nodeA.label} et ${nodeB.label}`);
            this.restartSimulation();
        } else {
            this.log("Erreur : Une connexion existe déjà entre ces nœuds.");
        }
    }

    restartSimulation() {
        // Mise à jour des données pour les liens
        this.link = this.linkGroup.selectAll("line").data(this.links);
        this.link.exit().remove();

        const linkEnter = this.link.enter().append("line")
            .attr("stroke", "#95a5a6")
            .attr("stroke-width", 2);

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

        this.log("Topologie aléatoire générée.");
        this.restartSimulation();
        this.updateUI();
    }

    resetNetwork() {
        this.nodes = [];
        this.links = [];
        this.nextNodeId = 1;
        this.selectedNode = null;

        this.restartSimulation();
        this.updateUI();
    }

    selectNode(node) {
        if (this.selectedNode === node) {
            this.selectedNode = null;
            d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");
            this.log(`Désélection de ${node.label}`);
        } else {
            // Visual feedback
            d3.selectAll(".node circle").style("stroke-width", 0).style("stroke", "white");

            // Correction: Trouver l'élément SVG correspondant au nœud
            const nodeElement = this.node.nodes().find(n => n.__data__ && n.__data__.id === node.id);
            if (nodeElement) {
                d3.select(nodeElement).select("circle")
                    .style("stroke-width", 4)
                    .style("stroke", "#f1c40f");
            }

            this.selectedNode = node;
            this.log(`Sélection : ${node.label} (IP: ${node.ip})`);
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

    updateUI() {
        // Update dropdown for link creation
        const selectEl = document.getElementById('nodeSelector');
        if (selectEl) {
            selectEl.innerHTML = '<option value="">-- Sélectionnez un nœud --</option>';
            this.nodes.forEach(n => {
                if (n.type === 'switch') {
                    const option = document.createElement('option');
                    option.value = n.id;
                    option.textContent = `${n.label} (${n.type})`;
                    selectEl.appendChild(option);
                }
            });
        }
    }

    connectSelectedNodes(firstId, secondId) {
        if (!firstId || !secondId) {
            this.log("Erreur : Veuillez sélectionner deux nœuds valides.");
            return;
        }

        const node1 = this.nodes.find(n => n.id === firstId);
        const node2 = this.nodes.find(n => n.id === secondId);



        if (!node1 || !node2) {
            this.log("Erreur : Un ou plusieurs nœuds introuvables.");
            return;
        }

        // Empêcher les liens doubles
        const existingLink = this.links.find(
            l =>
                (l.source.id === node1.id && l.target.id === node2.id) ||
                (l.source.id === node2.id && l.target.id === node1.id)
        );

        if (existingLink) {
            this.log(`Un lien existe déjà entre ${node1.label} et ${node2.label}.`);
            return;
        }

        // Créer le lien
        this.createLink(node1, node2);
    }

    createLink(sourceNode, targetNode) {
        const link = { source: sourceNode.id, target: targetNode.id };
        this.links.push(link);

        // Mettre à jour l'affichage du lien
        this.link = this.linkGroup.selectAll(".link").data(this.links, d => `${d.source.id}-${d.target.id}`);

        const linkEnter = this.link.enter().append("line")
            .attr("class", "link")
            .attr("stroke", "#999")
            .attr("stroke-width", 2);

        // Tooltip sur les liens
        linkEnter.on("mouseover", (event, d) => {
            const sourceNode = this.nodes.find(n => n.id === d.source);
            const targetNode = this.nodes.find(n => n.id === d.target);
            this.tooltip.style("opacity", 1);
            this.tooltip.html(`Lien : ${sourceNode.label} ↔ ${targetNode.label}`);
        })
            .on("mousemove", (event) => {
                this.tooltip.style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", () => { this.tooltip.style("opacity", 0); });

        // Supprimer les liens existants
        this.link.exit().remove();
        this.link = linkEnter.merge(this.link);

        // Redémarrer la simulation pour réagencer les nœuds avec le nouveau lien
        this.simulation.nodes(this.nodes).force("link").links(this.links);
        this.simulation.alpha(1).restart();

        this.log(`Lien créé entre ${sourceNode.label} et ${targetNode.label}.`);
    }
    

    installFlowRule() {
        this.log("Installation d'une règle de flot... (simulation)");
    }

    fetchStatistics() {
        this.log("Récupération des statistiques...");
        document.getElementById("stats-output").innerText = "Trafic: Normal | Paquets traités: " + Math.floor(Math.random() * 10000);
    }
}

// Initialize App
const app = new SDNController();

// Helper for UI interaction
function handleSelectionChange() {
    const val = document.getElementById('nodeSelector').value;
    console.log("Selection changed");
}

