
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
        this.hoveredIfaceName = null;

        this.isGraphLocked = false;
        try {
            const savedStateJson = localStorage.getItem('conft_topology_state');
            if (savedStateJson) {
                const savedState = JSON.parse(savedStateJson);
                if (savedState.isLocked !== undefined) {
                    this.isGraphLocked = savedState.isLocked;
                }
            }
        } catch (e) { }

        // Initial Setup
        this.initGraph();

        this.log("Système prêt.");

        // Bind new action buttons
        document.getElementById('refresh-db-btn')?.addEventListener('click', () => {
            this.fetchRealTopology();
        });

        document.getElementById('discover-network-btn')?.addEventListener('click', () => {
            this.rediscoverNetwork();
        });

        document.getElementById('deploy-network-btn')?.addEventListener('click', () => {
            this.deployTopology();
        });

        document.getElementById('save-settings-btn')?.addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('reset-app-btn')?.addEventListener('click', () => {
            this.showConfirmModal();
        });

        document.getElementById('confirm-cancel-btn')?.addEventListener('click', () => {
            this.hideConfirmModal();
        });

        document.getElementById('confirm-reset-btn')?.addEventListener('click', () => {
            this.resetApp();
        });

        document.getElementById('add-sub-cancel-btn')?.addEventListener('click', () => {
            this.hideAddSubInterfaceModal();
        });

        document.getElementById('add-sub-submit-btn')?.addEventListener('click', () => {
            this.submitAddSubInterface();
        });

        const lockBtn = document.getElementById('lock-topology-btn');
        if (lockBtn) {
            lockBtn.addEventListener('click', () => {
                this.toggleGraphLock();
            });
            // Update button state to match initial state
            this.updateLockButtonUI();
        }

        // Key listener for Escape to deselect selected equipment
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' || e.key === 'Esc') {
                const confirmModal = document.getElementById('confirm-modal');
                if (confirmModal && confirmModal.style.display === 'flex') {
                    this.hideConfirmModal();
                    return;
                }
                this.deselectCurrentNode();
            }
        });

        // Collapsible sidebar sections (Paramètres, Démo & Simulation, Configuration Réseau)
        document.querySelectorAll('.sidebar-section').forEach(section => {
            const h3 = section.querySelector('h3');
            if (h3 && (h3.textContent.includes('Paramètres') || h3.textContent.includes('Démo') || h3.textContent.includes('Configuration'))) {
                h3.classList.add('collapsible');
                h3.addEventListener('click', () => {
                    section.classList.toggle('collapsed');
                });
            }
        });

        // Fetch existing topology and load configuration on load
        this.loadSettings();
        this.fetchRealTopology();
    }

    async loadSettings() {
        try {
            const response = await fetch(`${API_BASE}/db/settings`);
            if (response.ok) {
                const settings = await response.json();
                document.getElementById('settings-ip').value = settings.host || '';
                document.getElementById('settings-username').value = settings.username || '';
                document.getElementById('settings-password').value = settings.password || '';
                document.getElementById('settings-device-type').value = settings.device_type || 'cisco_ios';
                this.log("Paramètres de connexion chargés.");
            }
        } catch (error) {
            this.log("Impossible de charger les paramètres.");
        }
    }

    async saveSettings() {
        const host = document.getElementById('settings-ip').value.trim();
        const username = document.getElementById('settings-username').value.trim();
        const password = document.getElementById('settings-password').value.trim();
        const deviceType = document.getElementById('settings-device-type').value;

        if (!host || !username || !password) {
            this.log("Champs de paramètres de connexion incomplets.");
            alert("Veuillez remplir l'adresse IP, l'utilisateur et le mot de passe.");
            return;
        }

        const btn = document.getElementById('save-settings-btn');
        btn.disabled = true;
        btn.textContent = "Enregistrement...";

        try {
            const response = await fetch(`${API_BASE}/db/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host, username, password, device_type: deviceType })
            });

            if (response.ok) {
                this.log("Paramètres de connexion sauvegardés.");
                alert("Paramètres enregistrés avec succès.");
            } else {
                throw new Error();
            }
        } catch (error) {
            this.log("Erreur lors de la sauvegarde des paramètres.");
            alert("Erreur lors de la sauvegarde.");
        } finally {
            btn.disabled = false;
            btn.textContent = "Enregistrer";
        }
    }

    async rediscoverNetwork() {
        const btn = document.getElementById('discover-network-btn');
        btn.disabled = true;
        btn.textContent = "Découverte...";
        this.log("Début de la découverte réseau...");

        // Purge example graph immediately on crawl start
        this.nodes = [];
        this.links = [];
        this.restartSimulation();

        try {
            const response = await fetch(`${API_BASE}/db/rediscover`, {
                method: 'POST'
            });

            const result = await response.json();
            if (response.ok) {
                this.log(`Découverte terminée : ${result.nodes_discovered} nœud(s) découvert(s).`);
                this.fetchRealTopology();
            } else {
                throw new Error(result.detail || "Échec de la découverte");
            }
        } catch (error) {
            this.log(`Erreur de découverte : ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = "Découvrir le réseau";
        }
    }

    async deployTopology() {
        const btn = document.getElementById('deploy-network-btn');
        btn.disabled = true;
        btn.textContent = "Envoi en cours...";
        this.log("Déploiement de la configuration au réseau...");

        try {
            const response = await fetch(`${API_BASE}/db/deploy`, {
                method: 'POST'
            });

            const result = await response.json();
            if (response.ok) {
                let successCount = 0;
                let failCount = 0;
                result.results.forEach(res => {
                    if (res.success) {
                        this.log(`[Succès] ${res.hostname || res.ip_address} : ${res.message}`);
                        successCount++;
                    } else {
                        this.log(`[Erreur] ${res.hostname || res.ip_address} : ${res.message}`);
                        failCount++;
                    }
                });
                this.log(`Déploiement terminé.\nSuccès : ${successCount}, Échecs : ${failCount}`);
            } else {
                throw new Error(result.detail || "Échec du déploiement");
            }
        } catch (error) {
            this.log(`Erreur de déploiement : ${error.message}`);
            alert(`Erreur : ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = "Envoyer au réseau";
        }
    }

    showConfirmModal() {
        const modal = document.getElementById('confirm-modal');
        if (modal) modal.style.display = 'flex';
    }

    hideConfirmModal() {
        const modal = document.getElementById('confirm-modal');
        if (modal) modal.style.display = 'none';
    }

    async resetApp() {
        this.hideConfirmModal();
        this.log("Réinitialisation de l'application...");

        try {
            const response = await fetch(`${API_BASE}/db/reset`, {
                method: 'POST'
            });

            if (response.ok) {
                const consoleEl = document.getElementById('console-log');
                if (consoleEl) {
                    consoleEl.innerHTML = '';
                }
                this.log("Application réinitialisée. Base de données vidée.");
                this.selectedNode = null;
                this.updateNodeInfoUI(null);
                this.closePanel();

                // Vider les inputs
                document.getElementById('settings-ip').value = '';
                document.getElementById('settings-username').value = '';
                document.getElementById('settings-password').value = '';
                document.getElementById('settings-device-type').value = 'cisco_ios';

                this.nodes = [];
                this.links = [];
                this.restartSimulation();

                await this.fetchRealTopology();
            } else {
                throw new Error("Erreur lors de la réinitialisation");
            }
        } catch (error) {
            this.log(`Erreur de réinitialisation : ${error.message}`);
            alert(`Erreur : ${error.message}`);
        }
    }

    updateNodeInfoUI(node) {
        const container = document.getElementById('node-info-section');
        const infoCard = document.getElementById('selected-node-info');
        if (!container || !infoCard) return;

        if (node) {
            container.style.display = 'block';
            infoCard.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:6px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <strong>Nom :</strong> 
                        <input type="text" id="edit-node-label" value="${node.label || ''}" 
                            style="flex: 1; padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.9rem; font-family: inherit; font-weight: bold; color: #334155; width: 100%; box-sizing: border-box;" />
                    </div>
                    <div><strong>Adresse IP :</strong> ${node.ip}</div>
                    <div><strong>Type :</strong> ${node.type.toUpperCase()}</div>
                </div>
            `;

            const input = document.getElementById('edit-node-label');
            if (input) {
                input.addEventListener('change', (e) => {
                    this.saveNodeLabel(node, e.target.value.trim());
                });
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        input.blur();
                    }
                });
            }
        } else {
            container.style.display = 'none';
            infoCard.innerHTML = '';
        }
    }

    async saveNodeLabel(node, newLabel) {
        if (!newLabel || newLabel === node.label) return;

        this.log(`Sauvegarde du nom de ${node.label} -> ${newLabel}...`);
        const oldLabel = node.label;
        node.label = newLabel;

        // Mettre à jour l'étiquette texte du SVG immédiatement
        this.node.select("text").text(d => d.label);

        try {
            const response = await fetch(`${API_BASE}/db/node/${node.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hostname: newLabel })
            });

            if (response.ok) {
                this.log(`Nom sauvegardé avec succès.`);
                const panelTitle = document.getElementById('panel-title');
                if (panelTitle && this.selectedNode && this.selectedNode.id === node.id) {
                    panelTitle.textContent = `Interfaces - ${newLabel}`;
                }
            } else {
                throw new Error();
            }
        } catch (error) {
            this.log(`Erreur lors de la sauvegarde du nom.`);
            node.label = oldLabel;
            this.node.select("text").text(d => d.label);
            this.updateNodeInfoUI(node);
        }
    }
    async fetchRealTopology() {
        try {
            this.log("Récupération de la topologie via l'API.");

            const response = await fetch(`${API_BASE}/db/topology`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();

            // Valider la structure
            if (!Array.isArray(data.nodes) || !Array.isArray(data.links)) {
                throw new Error("Réponse API invalide");
            }

            // Check if topology is empty (first initialization)
            if (data.nodes.length === 0) {
                this.showSetupOverlay();
                this.loadExampleTopology();
                return;
            } else {
                this.hideSetupOverlay();
            }

            // Check if any node is locked in DB
            const isAnyLocked = data.nodes.some(n => n.is_locked);
            if (isAnyLocked) {
                this.isGraphLocked = true;
            }
            this.updateLockButtonUI();

            // Mapping des nœuds pour conserver les positions s'ils existent déjà (par id et par ip)
            const oldNodesMap = new Map();
            this.nodes.forEach(n => {
                if (n.id !== undefined && n.id !== null) {
                    oldNodesMap.set(String(n.id), n);
                }
                if (n.ip) {
                    oldNodesMap.set(n.ip, n);
                }
            });

            let savedState = null;
            try {
                const savedStateJson = localStorage.getItem('conft_topology_state');
                if (savedStateJson) savedState = JSON.parse(savedStateJson);
            } catch (e) { }

            this.nodes = data.nodes.map(n => {
                const oldNode = oldNodesMap.get(String(n.id)) || oldNodesMap.get(n.ip_address || n.ip);
                const savedNode = savedState && savedState.nodes ? (savedState.nodes[n.id] || (oldNode && savedState.nodes[oldNode.id])) : null;

                let startX = (Math.random() * 200) + (this.width / 2 - 100);
                let startY = (Math.random() * 200) + (this.height / 2 - 100);

                if (oldNode && oldNode.x !== undefined) {
                    startX = oldNode.x;
                    startY = oldNode.y;
                } else if (n.x !== null && n.x !== undefined) {
                    startX = n.x;
                    startY = n.y;
                } else if (savedNode && savedNode.x !== undefined) {
                    startX = savedNode.x;
                    startY = savedNode.y;
                }

                let fx = null;
                let fy = null;
                if (this.isGraphLocked) {
                    if (oldNode && oldNode.fx !== null && oldNode.fx !== undefined) {
                        fx = oldNode.fx;
                        fy = oldNode.fy;
                    } else if (n.fx !== null && n.fx !== undefined) {
                        fx = n.fx;
                        fy = n.fy;
                    } else if (savedNode && savedNode.x !== undefined) {
                        fx = savedNode.x;
                        fy = savedNode.y;
                    } else {
                        fx = startX;
                        fy = startY;
                    }
                }

                return {
                    id: n.id,
                    label: n.hostname || n.label,
                    type: n.device_type || n.type,
                    ip: n.ip_address || n.ip,
                    x: startX,
                    y: startY,
                    fx: fx,
                    fy: fy,
                    vx: oldNode ? oldNode.vx : 0,
                    vy: oldNode ? oldNode.vy : 0
                };
            });

            this.links = data.links.map(l => {
                // Find node ID by IP since backend link uses IP
                const sourceNode = this.nodes.find(n => n.ip === l.source_ip) || { id: l.source || l.source_ip };
                const targetNode = this.nodes.find(n => n.ip === l.target_ip) || { id: l.target || l.target_ip };
                return {
                    source: sourceNode.id,
                    target: targetNode.id,
                    source_interface: l.source_interface,
                    target_interface: l.target_interface
                };
            });

            // Mettre à jour la simulation avec les nouvelles données
            this.restartSimulation();
            this.log(`Topologie chargée : ${this.nodes.length} nœuds, ${this.links.length} liens.`);

            this.fetchAllInterfaces();

        } catch (error) {
            this.log("API indisponible.");
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

    updateLockButtonUI() {
        const lockBtn = document.getElementById('lock-topology-btn');
        if (!lockBtn) return;
        if (this.isGraphLocked) {
            lockBtn.textContent = "Déverrouiller le graphe";
            lockBtn.classList.add('locked');
        } else {
            lockBtn.textContent = "Verrouiller le graphe";
            lockBtn.classList.remove('locked');
        }
    }

    showSetupOverlay() {
        const overlay = document.getElementById('setup-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            this.initSetupForm();
        }
    }

    hideSetupOverlay() {
        const overlay = document.getElementById('setup-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    initSetupForm() {
        const form = document.getElementById('setup-form');
        const demoBtn = document.getElementById('btn-setup-demo');
        const submitBtn = document.getElementById('btn-setup-submit');
        const spinner = submitBtn ? submitBtn.querySelector('.spinner') : null;
        const btnText = submitBtn ? submitBtn.querySelector('.btn-text') : null;
        const errorDiv = document.getElementById('setup-error');

        if (form && !form.dataset.initialized) {
            form.dataset.initialized = 'true';
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                // Purge example graph immediately on crawl start
                this.nodes = [];
                this.links = [];
                this.restartSimulation();
                const ip = document.getElementById('setup-ip').value;
                const username = document.getElementById('setup-username').value;
                const password = document.getElementById('setup-password').value;
                const deviceType = document.getElementById('setup-device-type').value;

                if (submitBtn) submitBtn.disabled = true;
                if (spinner) spinner.style.display = 'block';
                if (btnText) btnText.textContent = "Découverte en cours...";
                if (errorDiv) errorDiv.style.display = 'none';

                try {
                    const response = await fetch(`${API_BASE}/api/network/crawl`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            host: ip,
                            username: username,
                            password: password,
                            device_type: deviceType
                        })
                    });

                    const result = await response.json();
                    if (!response.ok) {
                        throw new Error(result.detail || "Échec de la découverte");
                    }

                    this.log(`Découverte réussie : ${result.nodes_discovered} nœuds trouvés.`);
                    this.hideSetupOverlay();
                    this.fetchRealTopology();
                } catch (err) {
                    this.log(`Erreur de découverte : ${err.message}`);
                    if (errorDiv) {
                        errorDiv.textContent = `Erreur : ${err.message}`;
                        errorDiv.style.display = 'block';
                    }
                } finally {
                    if (submitBtn) submitBtn.disabled = false;
                    if (spinner) spinner.style.display = 'none';
                    if (btnText) btnText.textContent = "Démarrer la découverte";
                }
            });
        }

        if (demoBtn && !demoBtn.dataset.initialized) {
            demoBtn.dataset.initialized = 'true';
            demoBtn.addEventListener('click', () => {
                this.log("Génération de la topologie de démonstration...");
                this.generateRandomTopology();
                this.hideSetupOverlay();
            });
        }
    }

    toggleGraphLock() {
        this.isGraphLocked = !this.isGraphLocked;
        this.updateLockButtonUI();

        if (this.isGraphLocked) {
            this.log("Graphe verrouillé.");
            this.nodes.forEach(d => {
                d.fx = d.x;
                d.fy = d.y;
            });
            this.simulation.alphaTarget(0); // Stop movement
        } else {
            this.log("Graphe déverrouillé.");
            this.nodes.forEach(d => {
                d.fx = null;
                d.fy = null;
            });
            this.simulation.alpha(0.3).restart();
        }
        this.saveTopologyState();
    }

    async saveTopologyState() {
        const state = {
            isLocked: this.isGraphLocked,
            nodes: {}
        };
        const updates = [];
        this.nodes.forEach(n => {
            state.nodes[n.id] = { x: n.x, y: n.y };
            updates.push({
                id: n.id,
                x: n.x,
                y: n.y,
                fx: n.fx,
                fy: n.fy,
                is_locked: this.isGraphLocked
            });
        });
        localStorage.setItem('conft_topology_state', JSON.stringify(state));

        try {
            await fetch(`${API_BASE}/db/topology/layout`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nodes: updates })
            });
        } catch (e) {
            console.warn("Could not save layout to DB", e);
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
                this.deselectCurrentNode();
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
                    .attr("y2", d => d.target.y)
                    .style("stroke-dasharray", d => {
                        const srcNode = typeof d.source === 'object' ? d.source : this.nodes.find(n => n.id === d.source);
                        const tgtNode = typeof d.target === 'object' ? d.target : this.nodes.find(n => n.id === d.target);
                        if (!srcNode || !tgtNode) return "none";
                        const srcType = srcNode.type;
                        const tgtType = tgtNode.type;
                        const isSrcExt = srcType === 'external';
                        const isTgtExt = tgtType === 'external';
                        if (isSrcExt || isTgtExt) {
                            const sx = srcNode.x || 0;
                            const sy = srcNode.y || 0;
                            const tx = tgtNode.x || 0;
                            const ty = tgtNode.y || 0;
                            const dx = tx - sx;
                            const dy = ty - sy;
                            const len = Math.sqrt(dx * dx + dy * dy) || 1;
                            const solidLen = 35;
                            const dotPeriod = 10;
                            const remaining = Math.max(0, len - solidLen);
                            const numDots = Math.floor(remaining / dotPeriod);

                            if (isTgtExt) {
                                // Router is source, External is target -> solid at start
                                let pattern = `${solidLen}, 6`;
                                for (let i = 0; i < numDots; i++) {
                                    pattern += ", 4, 6";
                                }
                                pattern += ", 0, 1000";
                                return pattern;
                            } else {
                                // External is source, Router is target -> solid at end
                                let pattern = "";
                                for (let i = 0; i < numDots; i++) {
                                    pattern += "4, 6, ";
                                }
                                pattern += `${solidLen}, 1000`;
                                return pattern;
                            }
                        }
                        return "none";
                    });

                this.node
                    .attr("transform", d => `translate(${d.x},${d.y})`);

                this.g.selectAll(".vlan-dot")
                    .attr("cx", d => {
                        const targetNode = d.isSource ? d.link.target : d.link.source;
                        const sourceNode = d.isSource ? d.link.source : d.link.target;
                        const dx = targetNode.x - sourceNode.x;
                        const dy = targetNode.y - sourceNode.y;
                        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                        const offset = sourceNode.type === 'switch' ? 35 : (sourceNode.type === 'router' ? 40 : 25);
                        return sourceNode.x + (dx / dist) * offset;
                    })
                    .attr("cy", d => {
                        const targetNode = d.isSource ? d.link.target : d.link.source;
                        const sourceNode = d.isSource ? d.link.source : d.link.target;
                        const dx = targetNode.x - sourceNode.x;
                        const dy = targetNode.y - sourceNode.y;
                        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                        const offset = sourceNode.type === 'switch' ? 35 : (sourceNode.type === 'router' ? 40 : 25);
                        return sourceNode.y + (dy / dist) * offset;
                    });
            })
            .on("end", () => {
                this.saveTopologyState();
            });

        // Lier les liens après avoir initialisé la simulation
        this.simulation.force("link").links(this.links);
    }



    restartSimulation() {
        // Mise à jour des données pour les liens
        this.link = this.linkGroup.selectAll("line").data(this.links);
        this.link.exit().remove();

        const linkEnter = this.link.enter().append("line")
            .attr("stroke", d => {
                const srcType = typeof d.source === 'object' ? d.source.type : (this.nodes.find(n => n.id === d.source)?.type);
                const tgtType = typeof d.target === 'object' ? d.target.type : (this.nodes.find(n => n.id === d.target)?.type);
                if (srcType === 'external' || tgtType === 'external') return "#7f8c8d";
                return "#95a5a6";
            })
            .attr("stroke-width", d => {
                const srcType = typeof d.source === 'object' ? d.source.type : (this.nodes.find(n => n.id === d.source)?.type);
                const tgtType = typeof d.target === 'object' ? d.target.type : (this.nodes.find(n => n.id === d.target)?.type);
                if (srcType === 'external' || tgtType === 'external') return 1.5;
                return 2;
            })
            .style("stroke-dasharray", d => {
                const srcType = typeof d.source === 'object' ? d.source.type : (this.nodes.find(n => n.id === d.source)?.type);
                const tgtType = typeof d.target === 'object' ? d.target.type : (this.nodes.find(n => n.id === d.target)?.type);
                if (srcType === 'external' || tgtType === 'external') return "35, 6, 4, 6, 4, 6, 4, 6, 4, 6";
                return "none";
            })
            .style("opacity", d => {
                const srcType = typeof d.source === 'object' ? d.source.type : (this.nodes.find(n => n.id === d.source)?.type);
                const tgtType = typeof d.target === 'object' ? d.target.type : (this.nodes.find(n => n.id === d.target)?.type);
                if (srcType === 'external' || tgtType === 'external') return 0.9;
                return 1;
            });

        // Tooltip sur les liens
        linkEnter.on("mouseover", (event, d) => {
            const sourceNode = typeof d.source === 'object' ? d.source : this.nodes.find(n => n.id === d.source);
            const targetNode = typeof d.target === 'object' ? d.target : this.nodes.find(n => n.id === d.target);
            if (sourceNode && targetNode) {
                if (sourceNode.type === 'external' || targetNode.type === 'external') return;
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
            .style("display", d => d.type === 'external' ? "none" : null)
            .call(d3.drag()
                .on("start", (event, d) => this.dragstarted(event, d))
                .on("drag", (event, d) => this.dragged(event, d))
                .on("end", (event, d) => this.dragended(event, d)))
            .on("click", (event, d) => {
                if (d.type === 'external') return;
                this.selectNode(d);
            });

        nodeEnter.append("circle")
            .attr("r", d => d.type === 'switch' ? 25 : (d.type === 'router' ? 30 : 15))
            .attr("fill", d => d.type === 'switch' ? "#e74c3c" : (d.type === 'router' ? "#3498db" : "#2ecc71"))
            .attr("stroke", "white")
            .attr("stroke-width", 0);

        nodeEnter.append("text")
            .attr("dx", d => d.type === 'switch' ? 35 : (d.type === 'router' ? 40 : 20))
            .attr("dy", ".35em")
            .text(d => d.label)
            .style("font-size", "14px")
            .style("font-weight", "bold")
            .style("pointer-events", "none");

        // Tooltip sur les nouveaux nœuds
        nodeEnter.on("mouseover", (event, d) => {
            if (d.type === 'external') return;
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

        const getNewIface = (node, type, targetNode) => {
            if (!node._ifaces) node._ifaces = [];
            let ifaceName = "";
            let mode = "access";
            let vlan_id = 1;
            let allowed_vlans = "";
            let description = `Connected to ${targetNode.label}`;

            const count = node._ifaces.length + 1;

            if (node.type === 'router') {
                // Realistic Cisco-style router interface numbering
                // GigabitEthernet0/0 = WAN uplink, GigabitEthernet0/1+ = LAN
                const ethIdx = node._ifaces.filter(i => !i.name.includes('.')).length;
                ifaceName = `GigabitEthernet0/${ethIdx}`;
                mode = "routed";
                vlan_id = null;
                allowed_vlans = null;

                // If connecting to a switch (not external), also generate dot1q sub-interfaces
                // The sub-interfaces will be added separately after VLAN pruning
                if (targetNode.type === 'switch') {
                    description = `LAN trunk to ${targetNode.label}`;
                } else if (targetNode.type === 'external') {
                    description = `WAN uplink to ${targetNode.label}`;
                }

            } else if (node.type === 'external') {
                ifaceName = `WAN0`;
                mode = "routed";
                vlan_id = null;
                allowed_vlans = null;
            } else if (node.type === 'switch') {
                ifaceName = `FastEthernet0/${count}`;
                if (targetNode.type === 'router' || targetNode.type === 'switch') {
                    mode = "trunk";
                    vlan_id = 1;
                    description = `Trunk to ${targetNode.label}`;
                } else if (targetNode.type === 'external') {
                    mode = "routed";
                    vlan_id = null;
                    allowed_vlans = null;
                } else if (targetNode.type === 'host') {
                    mode = "access";
                    vlan_id = targetNode._vlan || 10;
                    description = `Access port for ${targetNode.label} (VLAN ${vlan_id})`;
                }
            } else if (node.type === 'host') {
                ifaceName = count === 1 ? "eth0" : `eth${count - 1}`;
                mode = "routed";
                vlan_id = null;
                allowed_vlans = null;
                description = `Uplink to ${targetNode.label}`;
            }

            const ifaceObj = {
                name: ifaceName,
                description: description,
                mode: mode,
                vlan_id: vlan_id
            };
            if (allowed_vlans !== null && allowed_vlans !== undefined && allowed_vlans !== "") {
                ifaceObj.allowed_vlans = allowed_vlans;
            }
            node._ifaces.push(ifaceObj);
            return ifaceName;
        };

        const addLink = (sourceNode, targetNode) => {
            const sIface = getNewIface(sourceNode, sourceNode.type, targetNode);
            const tIface = getNewIface(targetNode, targetNode.type, sourceNode);
            this.links.push({
                source: sourceNode.id,
                target: targetNode.id,
                _sourceNode: sourceNode,
                _targetNode: targetNode,
                source_interface: sIface,
                target_interface: tIface
            });
        };

        const complexity = parseInt(document.getElementById('topo-complexity')?.value || '2');

        let numCores, numDists, getNumAccess, getNumHosts;
        if (complexity === 1) {
            numCores = 1;
            numDists = 0;
            getNumAccess = () => 1;
            getNumHosts = () => Math.floor(Math.random() * 2) + 1; // 1 to 2
        } else if (complexity === 2) {
            numCores = Math.floor(Math.random() * 2) + 1; // 1 to 2 core routers (max 2)
            numDists = numCores; // 1 to 2 dist switches
            getNumAccess = () => Math.floor(Math.random() * 2) + 1; // 1 to 2 access switches per dist
            getNumHosts = () => Math.floor(Math.random() * 2) + 1; // 1 to 2 hosts per access
        } else { // 3 (Grand)
            numCores = 2; // max 2 core routers
            numDists = Math.floor(Math.random() * 2) + 2; // 2 to 3 dist switches (potentially more than 2)
            getNumAccess = () => Math.floor(Math.random() * 2) + 2; // 2 to 3 access switches per dist
            getNumHosts = () => Math.floor(Math.random() * 2) + 2; // 2 to 3 hosts per access
        }

        const cores = [];
        const externals = [];

        for (let i = 0; i < numCores; i++) {
            // Core router
            const rId = `r${this.nextNodeId++}`;
            const rNode = {
                id: rId, label: `Core-R${i + 1}`, type: "router", ip: `10.0.0.${i + 1}`,
                x: (this.width / (numCores + 1)) * (i + 1), y: this.height * 0.2
            };
            this.nodes.push(rNode);
            cores.push(rNode);

            // Dummy external node
            const extId = `ext${this.nextNodeId++}`;
            const extNode = {
                id: extId, label: `Ext-R${i + 1}`, type: "external", ip: `198.51.100.${i + 1}`,
                x: rNode.x, y: rNode.y - 80
            };
            this.nodes.push(extNode);
            externals.push(extNode);
        }

        // Link core routers to their external connections (creates GigabitEthernet0/0 interface on router)
        for (let i = 0; i < cores.length; i++) {
            addLink(cores[i], externals[i]);
        }

        // Link core routers to their distribution/access switches
        const dists = [];
        const accesses = [];

        if (complexity === 1) {
            // Très Petit: No distribution switches. Core connects directly to access switch.
            const sId = `s${this.nextNodeId++}`;
            const sNode = {
                id: sId, label: `Acc-S1`, type: "switch", ip: `192.168.0.1`,
                x: cores[0].x, y: this.height * 0.6
            };
            this.nodes.push(sNode);
            accesses.push(sNode);

            // Link Core directly to Access switch
            addLink(cores[0], sNode);
        } else {
            // Distribution switches
            for (let j = 0; j < numDists; j++) {
                const sId = `s${this.nextNodeId++}`;
                const sNode = {
                    id: sId, label: `Dist-S${dists.length + 1}`, type: "switch", ip: `172.16.${dists.length}.1`,
                    x: (this.width / (numDists + 1)) * (j + 1), y: this.height * 0.5
                };
                this.nodes.push(sNode);
                dists.push(sNode);
                if (j < cores.length) {
                    addLink(cores[j], sNode);
                }
            }

            // Interconnect distribution switches to form a fully connected path (guarantees they are never disconnected)
            if (dists.length > 1) {
                for (let i = 0; i < dists.length - 1; i++) {
                    addLink(dists[i], dists[i + 1]);
                }
            }

            // Access switches
            for (let i = 0; i < dists.length; i++) {
                const numAccess = getNumAccess();
                for (let j = 0; j < numAccess; j++) {
                    const sId = `s${this.nextNodeId++}`;
                    const sNode = {
                        id: sId, label: `Acc-S${accesses.length + 1}`, type: "switch", ip: `192.168.${accesses.length}.1`,
                        x: (this.width / (dists.length * numAccess + 1)) * (accesses.length + 1), y: this.height * 0.8
                    };
                    this.nodes.push(sNode);
                    accesses.push(sNode);
                    addLink(dists[i], sNode);
                }
            }
        }

        // Host generation for all access switches
        for (let i = 0; i < accesses.length; i++) {
            const sNode = accesses[i];
            const vlanForThisSwitch = [10, 20, 30, 40, 50][Math.floor(Math.random() * 5)];

            const numHosts = getNumHosts();
            for (let k = 0; k < numHosts; k++) {
                const hId = `h${this.nextNodeId++}`;
                const hNode = {
                    id: hId, label: `Host-${i + 1}-${k + 1}`, type: "host", ip: `192.168.${i}.${k + 10}`,
                    x: sNode.x + (Math.random() * 80 - 40), y: this.height * 0.95 + (Math.random() * 20 - 10),
                    _vlan: vlanForThisSwitch
                };
                this.nodes.push(hNode);
                addLink(sNode, hNode);
            }
        }

        // --- VLAN Pruning Logic ---
        this.nodes.forEach(n => n._requiredVlans = new Set());

        // 1. Acc => Hosts
        this.links.forEach(l => {
            const src = l._sourceNode;
            const tgt = l._targetNode;
            if (src.type === 'host' && tgt.type === 'switch') tgt._requiredVlans.add(src._vlan);
            if (tgt.type === 'host' && src.type === 'switch') src._requiredVlans.add(tgt._vlan);
        });

        // 2. Dist => Acc
        this.links.forEach(l => {
            const src = l._sourceNode;
            const tgt = l._targetNode;
            if (src.label.startsWith('Dist') && tgt.label.startsWith('Acc')) {
                tgt._requiredVlans.forEach(v => src._requiredVlans.add(v));
            }
            if (tgt.label.startsWith('Dist') && src.label.startsWith('Acc')) {
                src._requiredVlans.forEach(v => tgt._requiredVlans.add(v));
            }
        });

        // 3. Core => Dist or Core => Acc
        this.links.forEach(l => {
            const src = l._sourceNode;
            const tgt = l._targetNode;
            if (src.label.startsWith('Core') && (tgt.label.startsWith('Dist') || tgt.label.startsWith('Acc'))) {
                tgt._requiredVlans.forEach(v => src._requiredVlans.add(v));
            }
            if (tgt.label.startsWith('Core') && (src.label.startsWith('Dist') || src.label.startsWith('Acc'))) {
                src._requiredVlans.forEach(v => tgt._requiredVlans.add(v));
            }
        });

        // 4. Update allowed_vlans on trunk interfaces
        this.nodes.forEach(n => {
            if (n._ifaces) {
                n._ifaces.forEach(iface => {
                    if (iface.mode === 'trunk') {
                        const link = this.links.find(l =>
                            (l.source === n.id && l.source_interface === iface.name) ||
                            (l.target === n.id && l.target_interface === iface.name)
                        );
                        if (link) {
                            const targetNode = link.source === n.id ? link._targetNode : link._sourceNode;
                            let allowed = [...n._requiredVlans].filter(x => targetNode._requiredVlans.has(x));
                            if (allowed.length > 0) {
                                iface.allowed_vlans = allowed.sort((a, b) => a - b).join(',');
                            } else {
                                iface.allowed_vlans = "1"; // native fallback
                            }
                        }
                    }
                });
            }
        });

        // 5. Generate dot1q sub-interfaces for routers (router-on-a-stick)
        this.nodes.forEach(n => {
            if (n.type !== 'router') return;
            // Find the LAN-facing physical interface (connected to a switch)
            const lanLinks = this.links.filter(l => {
                const other = l.source === n.id ? l._targetNode : (l.target === n.id ? l._sourceNode : null);
                return other && other.type === 'switch';
            });
            lanLinks.forEach(link => {
                const physIface = link.source === n.id ? link.source_interface : link.target_interface;
                const switchNode = link.source === n.id ? link._targetNode : link._sourceNode;
                const vlansToRoute = [...(switchNode._requiredVlans || new Set())];
                if (vlansToRoute.length === 0) return;
                // Add sub-interface for each VLAN (dot1q encapsulation)
                vlansToRoute.sort((a, b) => a - b).forEach(vlan => {
                    const subIfaceName = `${physIface}.${vlan}`;
                    const alreadyExists = n._ifaces && n._ifaces.find(i => i.name === subIfaceName);
                    if (!alreadyExists) {
                        const subnetBase = 100 + Math.floor(vlan / 10);
                        n._ifaces.push({
                            name: subIfaceName,
                            description: `dot1q encapsulation ${vlan} — gateway 192.168.${vlan}.1/24`,
                            mode: "dot1q",
                            vlan_id: vlan,
                            allowed_vlans: null
                        });
                    }
                });
            });
        });
        // --- End VLAN Pruning / dot1q Logic ---

        // --- Anomaly Injection (demo mode) ---
        const anomalyEnabled = document.getElementById('topo-anomaly')?.checked;
        if (anomalyEnabled) {
            this._injectVlanAnomalies();
            this.log("[NON-CONFORME] Anomalies VLAN injectées.");
        }
        // --- End Anomaly Injection ---

        this.log("Topologie générée localement. Synchronisation avec la DB...");

        const payloadNodes = this.nodes.map(n => {
            return {
                ip: n.ip,
                label: n.label,
                type: n.type,
                interfaces: n._ifaces || []
            };
        });

        const payloadLinks = this.links.map(l => {
            return {
                source_ip: l._sourceNode.ip,
                target_ip: l._targetNode.ip,
                source_interface: l.source_interface,
                target_interface: l.target_interface
            };
        });

        this.nodes.forEach(n => {
            delete n._ifaces;
            delete n._vlan;
        });

        const linksForD3 = this.links.map(l => ({
            source: l.source,
            target: l.target,
            source_interface: l.source_interface,
            target_interface: l.target_interface
        }));
        this.links = linksForD3;

        fetch(`${API_BASE}/db/topology/random`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nodes: payloadNodes, links: payloadLinks })
        }).then(res => {
            if (res.ok) {
                this.log("Topologie synchronisée avec la base de données.");
                this.fetchRealTopology();
            } else {
                this.log("Erreur de synchronisation avec la DB.");
            }
        }).catch(err => {
            this.log("Erreur réseau (Sync DB): " + err.message);
        });
    }

    updateComplexityLabel(val) {
        const label = document.getElementById('topo-complexity-value');
        if (!label) return;

        let text = "Moyen";
        const v = parseInt(val);
        if (v === 1) {
            text = "Petit";
        } else if (v === 2) {
            text = "Moyen";
        } else if (v === 3) {
            text = "Grand";
        }
        label.textContent = text;
    }


    deselectCurrentNode() {
        if (this.selectedNode) {
            this.log(`Désélection de ${this.selectedNode.label}`);
        }
        this.selectedNode = null;
        d3.selectAll(".node circle")
            .style("stroke-width", 0)
            .style("stroke", "white");
        this.updateNodeInfoUI(null);
        this.closePanel();
    }

    selectNode(node) {
        if (this.selectedNode && this.selectedNode.id === node.id) {
            this.deselectCurrentNode();
        } else {
            if (this.selectedNode) {
                this.closePanel(); // Save interface state and reset links
            }

            d3.selectAll(".node circle")
                .style("stroke-width", 0)
                .style("stroke", "white");

            this.selectedNode = node;
            const nodeElement = this.node.nodes().find(n => n.__data__ && n.__data__.id === node.id);
            if (nodeElement) {
                d3.select(nodeElement).select("circle")
                    .style("stroke-width", 4)
                    .style("stroke", "#f1c40f");
            }

            this.log(`Sélection : ${node.label} (IP: ${node.ip})`);
            this.updateNodeInfoUI(node);
            this.fetchSelectedNode();
        }
    }

    // Drag Functions
    dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        if (!this.isGraphLocked) {
            d.fx = d.x;
            d.fy = d.y;
        }
    }

    dragged(event, d) {
        if (!this.isGraphLocked) {
            d.fx = event.x;
            d.fy = event.y;
        } else {
            // Même si verrouillé, on autorise peut-être le drag manuel pour ajuster ?
            // Le prompt demande "verrouiller le déplacement du graph" 
            // Si on veut permettre le drag manuel tout en gardant "verrouillé", on fait pareil :
            d.fx = event.x;
            d.fy = event.y;
        }
    }

    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        if (!this.isGraphLocked) {
            d.fx = null;
            d.fy = null;
        } else {
            d.fx = d.x;
            d.fy = d.y;
        }
        this.saveTopologyState();
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
        this.currentInterfaces = [];
        this.currentEditingInterfaceId = null;
        this.hoveredIfaceName = null;
        this.updateLinkStyles();
    }

    renderInterfacesPanel() {
        const list = document.getElementById('interfaces-list');
        if (!list) return;
        list.innerHTML = '';
        if (!this.currentInterfaces || this.currentInterfaces.length === 0) {
            list.innerHTML = '<p style="color: #666; text-align:center;">Aucune interface trouvée.</p>';
            return;
        }

        // Grouping logic
        const subIfaceMap = {};
        const physicalIfaces = [];

        this.currentInterfaces.forEach(iface => {
            const name = iface.name || "";
            const dotIndex = name.indexOf('.');
            if (dotIndex !== -1) {
                const parentName = name.substring(0, dotIndex);
                if (!subIfaceMap[parentName]) {
                    subIfaceMap[parentName] = [];
                }
                subIfaceMap[parentName].push(iface);
            } else {
                physicalIfaces.push(iface);
            }
        });

        // Add virtual parent if sub-interfaces exist but parent physical interface is missing
        const physicalNames = new Set(physicalIfaces.map(i => i.name));
        Object.keys(subIfaceMap).forEach(parentName => {
            if (!physicalNames.has(parentName)) {
                physicalIfaces.push({
                    id: `virtual-${parentName}`,
                    name: parentName,
                    description: "Interface physique parente (Virtuelle)",
                    mode: "routed",
                    vlan_id: null,
                    isVirtual: true
                });
            }
        });

        // Sort parent interfaces
        physicalIfaces.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));

        // Helper to render a card
        const createCardElement = (iface, isSubCard = false) => {
            const isEditing = this.currentEditingInterfaceId === iface.id;
            const card = document.createElement('div');
            card.className = `interface-card ${isEditing ? 'editing' : ''}`;
            if (iface.isVirtual) {
                card.style.opacity = '0.75';
                card.style.cursor = 'default';
            }

            // Mouse hover event listeners for highlighting
            card.addEventListener('mouseenter', () => {
                if (this.selectedNode) {
                    this.hoveredIfaceName = iface.name;
                    this.updateLinkStyles();
                }
            });
            card.addEventListener('mouseleave', () => {
                if (this.selectedNode) {
                    this.hoveredIfaceName = null;
                    this.updateLinkStyles();
                }
            });

            if (isEditing) {
                card.innerHTML = `
                    <div class="iface-field">
                        <span class="iface-label">Nom</span>
                        <input type="text" class="iface-input" id="edit-name-${iface.id}" value="${iface.name || ''}" ${iface.isVirtual ? 'disabled' : ''} />
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Description</span>
                        <input type="text" class="iface-input" id="edit-desc-${iface.id}" value="${iface.description || ''}" />
                    </div>
                    ${this.selectedNode && this.selectedNode.type !== 'host' && !iface.isVirtual ? `
                     <div class="iface-field">
                        <span class="iface-label" title="Access = port pour machine finale, Trunk = port entre switchs/routeurs">Mode</span>
                        <select class="iface-input" id="edit-mode-${iface.id}" onchange="
                            const val = this.value;
                            document.getElementById('edit-vlan-container-${iface.id}').style.display = (val === 'access' || val === 'static access' || val === 'dot1q') ? 'flex' : 'none';
                            document.getElementById('edit-allowed-container-${iface.id}').style.display = val === 'trunk' ? 'flex' : 'none';
                            document.getElementById('edit-vlan-label-${iface.id}').textContent = val === 'dot1q' ? 'Encap. VLAN' : 'VLAN';
                        ">
                            ${(() => {
                            const modes = ["access", "trunk", "dynamic auto", "static access", "dot1q"];
                            if (iface.mode && !modes.includes(iface.mode)) {
                                modes.push(iface.mode);
                            }
                            return modes.map(m => `<option value="${m}" ${iface.mode === m ? 'selected' : ''}>${m === 'dot1q' ? '802.1Q (dot1q)' : m.charAt(0).toUpperCase() + m.slice(1)}</option>`).join('');
                        })()}
                        </select>
                    </div>
                    <div class="iface-field" id="edit-vlan-container-${iface.id}" style="display: ${(!iface.mode || iface.mode.includes('access') || iface.mode === 'dot1q') ? 'flex' : 'none'}">
                        <span class="iface-label" id="edit-vlan-label-${iface.id}" title="VLAN d'accès ou d'encapsulation de ce port">${iface.mode === 'dot1q' ? 'Encap. VLAN' : 'VLAN'}</span>
                        <input type="number" class="iface-input" id="edit-vlan-${iface.id}" value="${iface.vlan_id || ''}" />
                    </div>
                    <div class="iface-field" id="edit-allowed-container-${iface.id}" style="display: ${iface.mode === 'trunk' ? 'flex' : 'none'}">
                        <span class="iface-label" title="VLANs taggés autorisés sur ce trunk">Allowed VLANs</span>
                        <input type="text" class="iface-input" id="edit-allowed-${iface.id}" value="${iface.allowed_vlans || ''}" placeholder="ex: 10,20,30" />
                    </div>
                    ` : ''}
                `;
            } else {
                let actionBtns = '';
                if (!isSubCard && this.selectedNode && this.selectedNode.type === 'router') {
                    actionBtns += `
                        <button class="btn-add-sub" onclick="event.stopPropagation(); app.showAddSubInterfaceModal('${iface.name}')">
                            + Sous-interface
                        </button>
                    `;
                }
                if (isSubCard) {
                    actionBtns += `
                        <button class="btn-delete-sub" onclick="event.stopPropagation(); app.deleteInterface(${iface.id}, '${iface.name}')">
                            Supprimer
                        </button>
                    `;
                }

                card.innerHTML = `
                    <div class="iface-status ${iface.mode ? 'active' : ''}"></div>
                    <div class="iface-field">
                        <span class="iface-label">Nom</span>
                        <span class="iface-value">${iface.name || '-'}</span>
                    </div>
                    <div class="iface-field">
                        <span class="iface-label">Description</span>
                        <span class="iface-value">${iface.description || '-'}</span>
                    </div>
                    ${this.selectedNode && this.selectedNode.type !== 'host' && !iface.isVirtual ? `
                    <div class="iface-field">
                        <span class="iface-label">Mode</span>
                        <span class="iface-value" style="${iface.mode === 'dot1q' ? 'color:#7c3aed;font-weight:600;' : iface.mode === 'trunk' ? 'color:#0369a1;font-weight:600;' : ''}">${iface.mode || '-'}${iface.mode === 'dot1q' ? ' (802.1Q)' : ''}</span>
                    </div>
                    ${(iface.mode === 'dot1q' || !iface.mode || iface.mode.includes('access')) ? `
                    <div class="iface-field">
                        <span class="iface-label">${iface.mode === 'dot1q' ? 'Encap. VLAN' : 'VLAN'}</span>
                        <span class="iface-value" style="${iface.mode === 'dot1q' ? 'color:#7c3aed;font-weight:600;' : ''}">${iface.vlan_id || '-'}</span>
                    </div>` : ''}
                    ${iface.mode === 'trunk' ? `
                    <div class="iface-field">
                        <span class="iface-label">Allowed VLANs</span>
                        <span class="iface-value">${iface.allowed_vlans || '-'}</span>
                    </div>` : ''}
                    ` : ''}
                    ${actionBtns ? `<div class="interface-card-header-actions">${actionBtns}</div>` : ''}
                `;

                if (!iface.isVirtual) {
                    card.onclick = () => this.editInterface(iface.id);
                }
            }
            return card;
        };

        // Render each parent and its nested sub-interfaces
        physicalIfaces.forEach(parent => {
            const parentCard = createCardElement(parent, false);
            const subs = subIfaceMap[parent.name] || [];

            if (subs.length > 0) {
                const group = document.createElement('div');
                group.className = 'interface-group';
                group.appendChild(parentCard);

                subs.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));

                const subListContainer = document.createElement('div');
                subListContainer.className = 'sub-interfaces-list';

                subs.forEach(sub => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'sub-interface-card-wrapper';
                    const subCard = createCardElement(sub, true);
                    wrapper.appendChild(subCard);
                    subListContainer.appendChild(wrapper);
                });

                group.appendChild(subListContainer);
                list.appendChild(group);
            } else {
                // Direct append to avoid double borders on devices without sub-interfaces (like switch ports)
                list.appendChild(parentCard);
            }
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
            let matchFound = false;
            this.linkGroup.selectAll("line").each(d => {
                const srcMatch = String(d.source.id) === String(this.selectedNode.id) && d.source_interface === ifaceName;
                const tgtMatch = String(d.target.id) === String(this.selectedNode.id) && d.target_interface === ifaceName;
                if (srcMatch || tgtMatch) matchFound = true;
            });
            this.log(`Recherche de liens pour l'interface ${ifaceName}... ${matchFound ? 'Trouvé!' : 'Aucun lien actif'}`);
        }

        this.updateLinkStyles();
    }

    async autoSaveInterface(id) {
        const nameEl = document.getElementById(`edit-name-${id}`);
        const descEl = document.getElementById(`edit-desc-${id}`);
        const modeEl = document.getElementById(`edit-mode-${id}`);
        const vlanEl = document.getElementById(`edit-vlan-${id}`);
        const allowedEl = document.getElementById(`edit-allowed-${id}`);

        if (!nameEl) return;

        const idx = this.currentInterfaces.findIndex(i => i.id === id);
        if (idx === -1) return;
        const existingIface = this.currentInterfaces[idx];

        const data = {
            name: nameEl.value,
            description: descEl ? descEl.value : existingIface.description,
            mode: modeEl ? modeEl.value : existingIface.mode,
            vlan_id: vlanEl ? (parseInt(vlanEl.value) || null) : existingIface.vlan_id,
            allowed_vlans: allowedEl ? allowedEl.value : existingIface.allowed_vlans
        };

        this.currentInterfaces[idx] = { ...this.currentInterfaces[idx], ...data };

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
            this.fetchAllInterfaces();
        } catch (error) {
            this.log(`Erreur de sauvegarde: ${error.message}`);
        }
    }
    async fetchAllInterfaces() {
        this.log("Interfaces chargées.");
        this.allInterfaces = {};
        const vlanSet = new Set();

        const promises = this.nodes.map(async (n) => {
            try {
                const response = await fetch(`${API_BASE}/db/node/${n.id}/interfaces`);
                if (response.ok) {
                    const ifaces = await response.json();
                    this.allInterfaces[n.id] = ifaces;
                    ifaces.forEach(iface => {
                        if (iface.vlan_id) vlanSet.add(iface.vlan_id);
                        if (iface.allowed_vlans) {
                            iface.allowed_vlans.split(',').forEach(v => {
                                const vlan = parseInt(v.trim());
                                if (!isNaN(vlan)) vlanSet.add(vlan);
                            });
                        }
                    });
                }
            } catch (e) {
                console.warn("Erreur fetch iface:", e);
            }
        });
        await Promise.all(promises);
        this.populateVlanFilter(Array.from(vlanSet).sort((a, b) => a - b));
    }

    populateVlanFilter(vlans) {
        const filterSelect = document.getElementById('vlan-filter');
        if (!filterSelect) return;

        const previousValue = filterSelect.value;

        filterSelect.innerHTML = '<option value="">Pas de filtre</option>';
        vlans.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v;
            opt.textContent = `VLAN ${v}`;
            filterSelect.appendChild(opt);
        });

        // Supprimer l'ancien écouteur s'il existe pour éviter les doublons
        const newSelect = filterSelect.cloneNode(true);
        newSelect.value = previousValue;
        filterSelect.parentNode.replaceChild(newSelect, filterSelect);

        newSelect.addEventListener('change', (e) => {
            this.highlightVlan(e.target.value);
        });

        if (previousValue) {
            this.highlightVlan(previousValue);
        }
    }

    highlightVlan(vlanId) {
        this.updateLinkStyles();
    }

    updateLinkStyles() {
        if (!this.linkGroup) return;

        const vlanFilter = document.getElementById('vlan-filter');
        const vlan = vlanFilter && vlanFilter.value ? parseInt(vlanFilter.value) : null;

        let editingNodeId = null;
        let editingIfaceName = null;
        if (this.currentEditingInterfaceId && this.selectedNode) {
            const selectedInterface = this.currentInterfaces.find(i => i.id === this.currentEditingInterfaceId);
            if (selectedInterface) {
                editingNodeId = String(this.selectedNode.id);
                editingIfaceName = selectedInterface.name;
            }
        }

        let hoveredNodeId = null;
        let hoveredIfaceName = null;
        if (this.hoveredIfaceName && this.selectedNode) {
            hoveredNodeId = String(this.selectedNode.id);
            hoveredIfaceName = this.hoveredIfaceName;
        }

        this.g.selectAll(".vlan-dot").remove();
        let matchCount = 0;
        const dotsData = [];

        this.linkGroup.selectAll("line")
            .style("stroke", d => {
                // Check hover match (supports physical and sub-interfaces)
                if (hoveredNodeId && hoveredIfaceName) {
                    const parentHoverName = hoveredIfaceName.split('.')[0];
                    const srcMatch = String(d.source.id) === hoveredNodeId && d.source_interface === parentHoverName;
                    const tgtMatch = String(d.target.id) === hoveredNodeId && d.target_interface === parentHoverName;
                    if (srcMatch || tgtMatch) return "#3b82f6"; // premium blue highlight
                }

                // Check editing match (supports physical and sub-interfaces)
                if (editingNodeId && editingIfaceName) {
                    const parentEditName = editingIfaceName.split('.')[0];
                    const srcMatch = String(d.source.id) === editingNodeId && d.source_interface === parentEditName;
                    const tgtMatch = String(d.target.id) === editingNodeId && d.target_interface === parentEditName;
                    if (srcMatch || tgtMatch) return "#e74c3c";
                }

                // Check VLAN match
                if (vlan) {
                    const srcIsHost = d.source.type === 'host';
                    const tgtIsHost = d.target.type === 'host';

                    const srcHasVlan = !srcIsHost && this.nodeHasVlanOnLink(d, true, vlan);
                    const tgtHasVlan = !tgtIsHost && this.nodeHasVlanOnLink(d, false, vlan);

                    if (srcHasVlan || tgtHasVlan) {
                        matchCount++;
                        if (srcHasVlan) dotsData.push({ link: d, isSource: true });
                        if (tgtHasVlan) dotsData.push({ link: d, isSource: false });
                    }

                    if (srcIsHost || tgtIsHost) {
                        if (srcHasVlan || tgtHasVlan) return "#f1c40f";
                    } else {
                        if (srcHasVlan && tgtHasVlan) return "#f1c40f";
                        if (srcHasVlan || tgtHasVlan) return "#e67e22";
                    }
                    return "#bdc3c7";
                }

                // Default
                return "#95a5a6";
            })
            .style("stroke-width", d => {
                // Check hover match
                if (hoveredNodeId && hoveredIfaceName) {
                    const parentHoverName = hoveredIfaceName.split('.')[0];
                    const srcMatch = String(d.source.id) === hoveredNodeId && d.source_interface === parentHoverName;
                    const tgtMatch = String(d.target.id) === hoveredNodeId && d.target_interface === parentHoverName;
                    if (srcMatch || tgtMatch) return 5; // thicker for hover to stand out
                }

                // Check editing match
                if (editingNodeId && editingIfaceName) {
                    const parentEditName = editingIfaceName.split('.')[0];
                    const srcMatch = String(d.source.id) === editingNodeId && d.source_interface === parentEditName;
                    const tgtMatch = String(d.target.id) === editingNodeId && d.target_interface === parentEditName;
                    if (srcMatch || tgtMatch) return 4;
                }

                // Check VLAN match
                if (vlan) {
                    const srcIsHost = d.source.type === 'host';
                    const tgtIsHost = d.target.type === 'host';
                    const srcHasVlan = !srcIsHost && this.nodeHasVlanOnLink(d, true, vlan);
                    const tgtHasVlan = !tgtIsHost && this.nodeHasVlanOnLink(d, false, vlan);
                    return (srcHasVlan || tgtHasVlan) ? 4 : 1.5;
                }

                // Default
                return 2;
            })
            .style("opacity", d => {
                // Dim other links if hovering
                if (hoveredNodeId && hoveredIfaceName) {
                    const parentHoverName = hoveredIfaceName.split('.')[0];
                    const srcMatch = String(d.source.id) === hoveredNodeId && d.source_interface === parentHoverName;
                    const tgtMatch = String(d.target.id) === hoveredNodeId && d.target_interface === parentHoverName;
                    return (srcMatch || tgtMatch) ? 1.0 : 0.15;
                }

                // Dim other links if editing
                if (editingNodeId && editingIfaceName) {
                    const parentEditName = editingIfaceName.split('.')[0];
                    const srcMatch = String(d.source.id) === editingNodeId && d.source_interface === parentEditName;
                    const tgtMatch = String(d.target.id) === editingNodeId && d.target_interface === parentEditName;
                    return (srcMatch || tgtMatch) ? 1.0 : 0.25;
                }

                if (vlan) {
                    const srcIsHost = d.source.type === 'host';
                    const tgtIsHost = d.target.type === 'host';
                    const srcHasVlan = !srcIsHost && this.nodeHasVlanOnLink(d, true, vlan);
                    const tgtHasVlan = !tgtIsHost && this.nodeHasVlanOnLink(d, false, vlan);
                    if (!srcHasVlan && !tgtHasVlan) return 0.4;
                }
                return 1;
            });

        if (vlan) {
            this.g.selectAll(".vlan-dot")
                .data(dotsData)
                .enter()
                .append("circle")
                .attr("class", "vlan-dot")
                .attr("r", 4);

            this.log(`Filtre VLAN ${vlan} : ${matchCount} lien(s) concerné(s).`);
            this.simulation.alpha(0.1).restart();
        }
    }

    nodeHasVlanOnLink(link, isSource, vlanId) {
        const nodeId = isSource ? link.source.id : link.target.id;
        const ifaceName = isSource ? link.source_interface : link.target_interface;

        const ifaces = this.allInterfaces[nodeId] || [];
        const iface = ifaces.find(i => i.name === ifaceName);

        if (!iface) return false;
        if (iface.vlan_id === vlanId) return true;
        if (iface.allowed_vlans) {
            const vlans = iface.allowed_vlans.split(',').map(v => parseInt(v.trim()));
            if (vlans.includes(vlanId)) return true;
        }
        return false;
    }

    // =============================================
    // ANOMALY INJECTION (demo / non-conforme mode)
    // =============================================
    _injectVlanAnomalies() {
        const anomalyTypes = ['missing_trunk_vlan', 'wrong_access_vlan', 'orphan_host_vlan'];
        let injected = 0;

        this.nodes.forEach(n => {
            if (!n._ifaces) return;
            n._ifaces.forEach(iface => {
                // Only tamper trunk allowed_vlans OR access vlan_id
                if (Math.random() > 0.45) return; // ~45% chance per interface

                const type = anomalyTypes[Math.floor(Math.random() * anomalyTypes.length)];

                if (type === 'missing_trunk_vlan' && iface.mode === 'trunk' && iface.allowed_vlans) {
                    // Remove one VLAN from allowed list
                    const vlans = iface.allowed_vlans.split(',').map(v => parseInt(v.trim())).filter(v => !isNaN(v));
                    if (vlans.length > 1) {
                        const removeIdx = Math.floor(Math.random() * vlans.length);
                        vlans.splice(removeIdx, 1);
                        iface.allowed_vlans = vlans.join(',');
                        iface.description = (iface.description || '') + ' [ANOMALY: missing VLAN]';
                        injected++;
                    }

                } else if (type === 'wrong_access_vlan' && iface.mode === 'access' && n.type === 'switch' && iface.vlan_id) {
                    // Change access VLAN to a wrong one
                    const allVlans = [10, 20, 30, 40, 50, 99];
                    const others = allVlans.filter(v => v !== iface.vlan_id);
                    const wrongVlan = others[Math.floor(Math.random() * others.length)];
                    iface.description = (iface.description || '') + ` [ANOMALY: was VLAN ${iface.vlan_id}, set to ${wrongVlan}]`;
                    iface.vlan_id = wrongVlan;
                    injected++;

                } else if (type === 'orphan_host_vlan' && iface.mode === 'access' && n.type === 'switch') {
                    // Assign a VLAN that probably doesn't exist on any trunk
                    const orphanVlan = 952;
                    iface.description = (iface.description || '') + ` [ANOMALY: orphan VLAN ${orphanVlan}]`;
                    iface.vlan_id = orphanVlan;
                    injected++;
                }
            });
        });
        return injected;
    }

    // =============================================
    // VLAN FEASIBILITY CHECK (client-side)
    // =============================================
    async checkVlanFeasibility() {
        this.log("[CHECK] Vérification de la faisabilité VLAN...");
        const btn = document.getElementById('btn-check-vlan');
        if (btn) { btn.disabled = true; btn.textContent = "Analyse..."; }

        // Make sure allInterfaces is populated
        await this.fetchAllInterfaces();

        const errors = [];
        const errorNodeIds = new Set();
        const errorLinkKeys = new Set();

        // Helper: parse allowed_vlans string into a Set of integers
        const parseAllowed = (str) => {
            if (!str) return new Set();
            return new Set(
                str.split(',').map(v => parseInt(v.trim())).filter(v => !isNaN(v))
            );
        };

        // Helper: get interface for a node+ifaceName pair
        const getIface = (nodeId, ifaceName) => {
            const ifaces = this.allInterfaces[nodeId] || [];
            return ifaces.find(i => i.name === ifaceName);
        };

        // Check every link
        this.links.forEach(l => {
            const srcNode = typeof l.source === 'object' ? l.source : this.nodes.find(n => n.id === l.source);
            const tgtNode = typeof l.target === 'object' ? l.target : this.nodes.find(n => n.id === l.target);
            if (!srcNode || !tgtNode) return;

            // Skip external links
            if (srcNode.type === 'external' || tgtNode.type === 'external') return;

            const srcIface = getIface(srcNode.id, l.source_interface);
            const tgtIface = getIface(tgtNode.id, l.target_interface);

            const linkKey = `${srcNode.id}-${tgtNode.id}`;

            // ---- Check 1: host ↔ switch (access link) ----
            if ((srcNode.type === 'host' || tgtNode.type === 'host')) {
                const hostNode = srcNode.type === 'host' ? srcNode : tgtNode;
                const switchNode = srcNode.type === 'host' ? tgtNode : srcNode;
                const swIface = srcNode.type === 'host' ? tgtIface : srcIface;

                if (swIface) {
                    const swVlan = swIface.vlan_id;

                    // Check if host VLAN (assigned to the switch interface) is orphan (= not present on any trunk of this switch)
                    if (swVlan) {
                        const switchTrunkIfaces = (this.allInterfaces[switchNode.id] || []).filter(i => i.mode === 'trunk');
                        const vlanReachable = switchTrunkIfaces.some(ti => parseAllowed(ti.allowed_vlans).has(swVlan));
                        if (!vlanReachable && switchTrunkIfaces.length > 0) {
                            errors.push({
                                type: 'critical',
                                icon: '[ERR]',
                                message: `VLAN orphelin : VLAN ${swVlan} sur l'interface ${switchNode.label}:${swIface.name} (connectée à ${hostNode.label}) n'est autorisé sur aucun trunk de ${switchNode.label}`
                            });
                            errorNodeIds.add(hostNode.id);
                            errorNodeIds.add(switchNode.id);
                            errorLinkKeys.add(linkKey);
                        }
                    }
                }
                return; // done for host links
            }

            // ---- Check 2: trunk links (switch ↔ switch, router ↔ switch) ----
            if (srcIface && tgtIface) {
                if (srcIface.mode === 'trunk' && tgtIface.mode === 'trunk') {
                    // Both sides trunk: check intersection of allowed VLANs
                    const srcAllowed = parseAllowed(srcIface.allowed_vlans);
                    const tgtAllowed = parseAllowed(tgtIface.allowed_vlans);

                    // Check Native VLAN Mismatch (for switch-to-switch trunks)
                    if (srcNode.type === 'switch' && tgtNode.type === 'switch') {
                        const srcNative = srcIface.vlan_id || 1;
                        const tgtNative = tgtIface.vlan_id || 1;
                        if (srcNative !== tgtNative) {
                            errors.push({
                                type: 'warning',
                                icon: '[ALERTE]',
                                message: `Mismatch de VLAN natif : ${srcNode.label}:${srcIface.name} (VLAN natif ${srcNative}) ↔ ${tgtNode.label}:${tgtIface.name} (VLAN natif ${tgtNative})`
                            });
                            errorNodeIds.add(srcNode.id);
                            errorNodeIds.add(tgtNode.id);
                            errorLinkKeys.add(linkKey);
                        }
                    }

                    if (srcAllowed.size === 0 && tgtAllowed.size === 0) return;

                    const intersection = [...srcAllowed].filter(v => tgtAllowed.has(v));
                    if (intersection.length === 0 && (srcAllowed.size > 0 || tgtAllowed.size > 0)) {
                        errors.push({
                            type: 'critical',
                            icon: '[ERR]',
                            message: `Trunk sans VLANs communs: ${srcNode.label}:${srcIface.name} [${srcIface.allowed_vlans}] <-> ${tgtNode.label}:${tgtIface.name} [${tgtIface.allowed_vlans}]`
                        });
                        errorNodeIds.add(srcNode.id);
                        errorNodeIds.add(tgtNode.id);
                        errorLinkKeys.add(linkKey);
                    } else if (intersection.length < Math.max(srcAllowed.size, tgtAllowed.size)) {
                        // Asymmetric — some VLANs blocked one way
                        const srcOnly = [...srcAllowed].filter(v => !tgtAllowed.has(v));
                        const tgtOnly = [...tgtAllowed].filter(v => !srcAllowed.has(v));
                        if (srcOnly.length > 0) {
                            errors.push({
                                type: 'warning',
                                icon: '[ALERTE]',
                                message: `VLANs ${srcOnly.join(',')} autorisés sur ${srcNode.label}:${srcIface.name} mais bloqués côté ${tgtNode.label}:${tgtIface.name}`
                            });
                            errorNodeIds.add(srcNode.id);
                            errorLinkKeys.add(linkKey);
                        }
                        if (tgtOnly.length > 0) {
                            errors.push({
                                type: 'warning',
                                icon: '[ALERTE]',
                                message: `VLANs ${tgtOnly.join(',')} autorisés sur ${tgtNode.label}:${tgtIface.name} mais bloqués côté ${srcNode.label}:${srcIface.name}`
                            });
                            errorNodeIds.add(tgtNode.id);
                            errorLinkKeys.add(linkKey);
                        }
                    }

                } else if (srcNode.type === 'switch' && tgtNode.type === 'switch' && (srcIface.mode === 'trunk' || tgtIface.mode === 'trunk')) {
                    // Switch to switch link, but only one side is trunk!
                    errors.push({
                        type: 'critical',
                        icon: '[ERR]',
                        message: `Incohérence de mode trunk : ${srcNode.label}:${srcIface.name} (mode ${srcIface.mode || 'non configuré'}) ↔ ${tgtNode.label}:${tgtIface.name} (mode ${tgtIface.mode || 'non configuré'})`
                    });
                    errorNodeIds.add(srcNode.id);
                    errorNodeIds.add(tgtNode.id);
                    errorLinkKeys.add(linkKey);

                } else if (srcNode.type === 'switch' && tgtNode.type === 'switch' && srcIface.mode === 'access' && tgtIface.mode === 'access') {
                    // Both switches but mismatch in access VLANs
                    const srcVlan = srcIface.vlan_id || 1;
                    const tgtVlan = tgtIface.vlan_id || 1;
                    if (srcVlan !== tgtVlan) {
                        errors.push({
                            type: 'critical',
                            icon: '[ERR]',
                            message: `Mismatch de VLAN d'accès entre switchs : ${srcNode.label}:${srcIface.name} (VLAN ${srcVlan}) ↔ ${tgtNode.label}:${tgtIface.name} (VLAN ${tgtVlan})`
                        });
                        errorNodeIds.add(srcNode.id);
                        errorNodeIds.add(tgtNode.id);
                        errorLinkKeys.add(linkKey);
                    }

                } else if (srcIface.mode === 'routed' && tgtIface.mode === 'trunk') {
                    // Router physical interface to switch trunk — normal for router-on-a-stick
                    // Warn if switch has VLANs but router has no sub-interfaces
                    const routerSubIfaces = (this.allInterfaces[srcNode.id] || []).filter(i => i.mode === 'dot1q');
                    if (routerSubIfaces.length === 0) {
                        errors.push({
                            type: 'warning',
                            icon: '[ALERTE]',
                            message: `Router-on-a-stick: ${srcNode.label} n'a pas de sous-interfaces dot1q pour le trunk vers ${tgtNode.label}`
                        });
                        errorNodeIds.add(srcNode.id);
                        errorLinkKeys.add(linkKey);
                    }
                } else if (tgtIface.mode === 'routed' && srcIface.mode === 'trunk') {
                    const routerSubIfaces = (this.allInterfaces[tgtNode.id] || []).filter(i => i.mode === 'dot1q');
                    if (routerSubIfaces.length === 0) {
                        errors.push({
                            type: 'warning',
                            icon: '[ALERTE]',
                            message: `Router-on-a-stick: ${tgtNode.label} n'a pas de sous-interfaces dot1q pour le trunk vers ${srcNode.label}`
                        });
                        errorNodeIds.add(tgtNode.id);
                        errorLinkKeys.add(linkKey);
                    }
                }
            }
        });

        // ---- Visual: highlight erroneous links ----
        this.linkGroup.selectAll("line").style("stroke", d => {
            const sId = typeof d.source === 'object' ? d.source.id : d.source;
            const tId = typeof d.target === 'object' ? d.target.id : d.target;
            const k1 = `${sId}-${tId}`;
            const k2 = `${tId}-${sId}`;
            if (errorLinkKeys.has(k1) || errorLinkKeys.has(k2)) return "#f43f5e";
            return null; // keep existing
        }).style("stroke-width", d => {
            const sId = typeof d.source === 'object' ? d.source.id : d.source;
            const tId = typeof d.target === 'object' ? d.target.id : d.target;
            const k1 = `${sId}-${tId}`;
            const k2 = `${tId}-${sId}`;
            if (errorLinkKeys.has(k1) || errorLinkKeys.has(k2)) return 3.5;
            return null;
        });

        // ---- Visual: highlight erroneous nodes (pulsing red stroke) ----
        this.node.select("circle")
            .style("stroke", d => errorNodeIds.has(d.id) ? "#f43f5e" : null)
            .style("stroke-width", d => errorNodeIds.has(d.id) ? 4 : null)
            .style("stroke-opacity", d => errorNodeIds.has(d.id) ? 0.85 : null);

        // ---- Render feasibility panel ----
        this._renderFeasibilityPanel(errors);

        if (btn) { btn.disabled = false; btn.textContent = "Vérifier la faisabilité"; }

        if (errors.length === 0) {
            this.log("[OK] Faisabilité VLAN : aucune erreur détectée.");
        } else {
            const critical = errors.filter(e => e.type === 'critical').length;
            const warnings = errors.filter(e => e.type === 'warning').length;
            this.log(`[ALERTE] Faisabilité VLAN : ${critical} erreur(s) critique(s), ${warnings} avertissement(s).`);
        }
    }

    _renderFeasibilityPanel(errors) {
        const panel = document.getElementById('feasibility-panel');
        const content = document.getElementById('feasibility-content');
        if (!panel || !content) return;

        panel.style.display = 'flex';

        if (errors.length === 0) {
            content.innerHTML = `
                <div class="feasibility-ok">
                    <span>[OK]</span>
                    <span>Aucune incohérence VLAN détectée. La topologie est conforme.</span>
                </div>`;
            return;
        }

        const critical = errors.filter(e => e.type === 'critical');
        const warnings = errors.filter(e => e.type === 'warning');

        let html = `<div class="feasibility-summary">`;
        if (critical.length) html += `<span class="feasibility-badge critical">${critical.length} critique${critical.length > 1 ? 's' : ''}</span>`;
        if (warnings.length) html += `<span class="feasibility-badge warning">${warnings.length} avertissement${warnings.length > 1 ? 's' : ''}</span>`;
        html += `</div>`;

        errors.forEach(e => {
            html += `<div class="feasibility-error-item type-${e.type}">
                <span class="err-icon">${e.icon}</span>
                <span>${e.message}</span>
            </div>`;
        });

        content.innerHTML = html;
    }

    closeFeasibilityPanel() {
        const panel = document.getElementById('feasibility-panel');
        if (panel) panel.style.display = 'none';
        // Reset link and node highlighting from feasibility check
        this.updateLinkStyles();
        this.node.select("circle")
            .style("stroke", null)
            .style("stroke-width", null)
            .style("stroke-opacity", null);
        // Re-apply selection highlight if any
        if (this.selectedNode) {
            const nodeElement = this.node.nodes().find(n => n.__data__ && n.__data__.id === this.selectedNode.id);
            if (nodeElement) {
                d3.select(nodeElement).select("circle")
                    .style("stroke-width", 4)
                    .style("stroke", "#f1c40f");
            }
        }
    }
    showAddSubInterfaceModal(parentName) {
        this._addSubParent = parentName;
        const modal = document.getElementById('add-sub-modal');
        const parentText = document.getElementById('add-sub-parent-text');
        const vlanInput = document.getElementById('add-sub-vlan');
        const descInput = document.getElementById('add-sub-desc');

        if (parentText) parentText.textContent = `Interface physique parente : ${parentName}`;
        if (vlanInput) vlanInput.value = '';
        if (descInput) descInput.value = '';

        if (modal) modal.style.display = 'flex';
    }

    hideAddSubInterfaceModal() {
        const modal = document.getElementById('add-sub-modal');
        if (modal) modal.style.display = 'none';
        this._addSubParent = null;
    }

    async submitAddSubInterface() {
        if (!this.selectedNode || !this._addSubParent) return;

        const vlanInput = document.getElementById('add-sub-vlan');
        const descInput = document.getElementById('add-sub-desc');
        const vlanVal = vlanInput ? parseInt(vlanInput.value) : null;
        const descVal = descInput ? descInput.value.trim() : '';

        if (!vlanVal || isNaN(vlanVal) || vlanVal < 1 || vlanVal > 4094) {
            alert("Veuillez entrer un numéro de VLAN valide (entre 1 et 4094).");
            return;
        }

        const subName = `${this._addSubParent}.${vlanVal}`;
        const alreadyExists = this.currentInterfaces && this.currentInterfaces.some(i => i.name === subName);
        if (alreadyExists) {
            alert(`La sous-interface ${subName} existe déjà.`);
            return;
        }

        const payload = {
            name: subName,
            description: descVal || `dot1q encapsulation ${vlanVal}`,
            mode: "dot1q",
            vlan_id: vlanVal,
            allowed_vlans: null
        };

        this.log(`Création de la sous-interface ${subName}...`);

        try {
            const response = await fetch(`${API_BASE}/db/node/${this.selectedNode.id}/interface`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error("Échec lors de la création de la sous-interface.");

            this.log(`Sous-interface ${subName} créée avec succès.`);
            this.hideAddSubInterfaceModal();
            await this.fetchSelectedNode();
        } catch (error) {
            this.log(`Erreur lors de la création : ${error.message}`);
            alert(`Erreur : ${error.message}`);
        }
    }

    async deleteInterface(id, name) {
        if (!confirm(`Voulez-vous vraiment supprimer la sous-interface ${name} ?`)) {
            return;
        }

        this.log(`Suppression de la sous-interface ${name}...`);

        try {
            const response = await fetch(`${API_BASE}/db/interface/${id}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error("Échec lors de la suppression.");

            this.log(`Sous-interface ${name} supprimée.`);
            await this.fetchSelectedNode();
        } catch (error) {
            this.log(`Erreur lors de la suppression : ${error.message}`);
            alert(`Erreur : ${error.message}`);
        }
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
