import { appState } from "./state.js";
import { initGraph, updateGraphHighlights, resizeGraph } from "./graph.js";

// DOM Elements
const initOverlay = document.getElementById("init-overlay");
const viewApp = document.getElementById("app-wrapper");
const btnGetConfig = document.getElementById("btn-get-config");

const routersList = document.getElementById("routers-list");
const switchesList = document.getElementById("switches-list");
const hostsList = document.getElementById("hosts-list");

const bottomPanel = document.getElementById("bottom-panel");
const bottomPanelTitle = document.getElementById("bottom-panel-title");
const bottomPanelContent = document.getElementById("bottom-panel-content");
const btnClosePanel = document.getElementById("btn-close-panel");
const btnBack = document.getElementById("btn-back");
const breadcrumb = document.getElementById("breadcrumb");

const rightPanel = document.getElementById("right-panel");
const rightPanelContent = document.getElementById("right-panel-content");
const btnCloseRight = document.getElementById("btn-close-right");

async function loadData() {
  const res = await fetch("/api/network");
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to load network: ${res.status} ${text}`);
  }
  const data = await res.json();
  return { nodes: data.nodes, edges: data.edges };
}

window.addEventListener("DOMContentLoaded", async () => {
  try {
    const settingsRes = await fetch("/api/settings");
    if (settingsRes.ok) {
      const settings = await settingsRes.json();
      localStorage.setItem("isMock", settings.mock_mode ? "true" : "false");
    }
  } catch (e) {
    console.error("Failed to fetch settings", e);
  }

  // Handle Mock Mode UI hiding on load if needed
  const isMock = localStorage.getItem("isMock") === "true";
  if (isMock) {
    const seedIpGroup = document.getElementById("seed-ip").closest('.form-group');
    const seedTypeGroup = document.getElementById("seed-type").closest('.form-group');
    const seedUserGroup = document.getElementById("seed-username").closest('.form-group');
    const seedPassGroup = document.getElementById("seed-password").closest('.form-group');
    const seedInstructions = document.getElementById("seed-instructions");
    
    if(seedIpGroup) seedIpGroup.style.display = "none";
    if(seedTypeGroup) seedTypeGroup.style.display = "none";
    if(seedUserGroup) seedUserGroup.style.display = "none";
    if(seedPassGroup) seedPassGroup.style.display = "none";
    if(seedInstructions) seedInstructions.style.display = "none";
    
    const btnGetConfig = document.getElementById("btn-get-config");
    if (btnGetConfig) btnGetConfig.textContent = "Launch Demo Network";
  }

  try {
    const data = await loadData();
    if (data.nodes && data.nodes.length > 0) {
      document.getElementById("init-overlay").classList.add("hidden");
      
      appState.setState({
        view: "main",
        nodes: data.nodes,
        links: data.edges,
      });
      setTimeout(() => {
        initGraph("graph-container", data.nodes, data.edges, (node) => {
          appState.setState({
            view: "node",
            selectedNode: node,
            selectedPort: null,
          });
        });
      }, 50);
    }
  } catch (e) {
    console.error("No existing network data, waiting for seed input.", e);
  }
});

btnGetConfig.addEventListener("click", async () => {
  const isMock = localStorage.getItem("isMock") === "true";
  const seedIp = document.getElementById("seed-ip").value;
  if (!isMock && !seedIp) {
      alert("Please enter a Seed IP address.");
      return;
  }
  btnGetConfig.textContent = "Starting...";
  
  try {
    const seedData = {
        seed_ip: seedIp,
        device_type: document.getElementById("seed-type").value || "cisco_ios",
        ssh_username: document.getElementById("seed-username").value,
        ssh_password: document.getElementById("seed-password").value,
        mock: isMock
    };
    
    const res = await fetch("/api/network/seed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(seedData)
    });
    if (!res.ok) throw new Error("Failed to start discovery");

    document.getElementById("init-overlay").classList.add("hidden");
    
    const overlay = document.getElementById("discovery-overlay");
    overlay.classList.remove("hidden");
    
    // Start polling status
    const pollStatus = async () => {
      try {
        const statusRes = await fetch("/api/network/status");
        if (!statusRes.ok) throw new Error("Status endpoint failed");
        const statusData = await statusRes.json();
        
        if (statusData.status === "completed") {
          overlay.classList.add("hidden");
          const newData = await loadData();
          appState.setState({
            view: "main",
            nodes: newData.nodes,
            links: newData.edges,
          });
          document.getElementById("graph-container").innerHTML = "";
          setTimeout(() => {
            initGraph("graph-container", newData.nodes, newData.edges, (node) => {
              appState.setState({
                view: "node",
                selectedNode: node,
                selectedPort: null,
              });
            });
          }, 50);
        } else {
          const statusText = document.getElementById("discovery-status-text");
          if (statusText) {
            statusText.textContent = `Pending: ${statusData.pending && statusData.pending.length ? statusData.pending.join(', ') : 'none'} | Failed: ${statusData.failed && statusData.failed.length ? statusData.failed.join(', ') : 'none'}`;
          }
          setTimeout(pollStatus, 2000);
        }
      } catch (e) {
        console.error("Polling error:", e);
        setTimeout(pollStatus, 2000);
      }
    };
    pollStatus();
  } catch (err) {
    btnGetConfig.textContent = "Error! Start Network Discovery";
    console.error(err);
    alert("Error: " + err.message);
  }
});

function parseSidebarLists(nodes) {
  const routers = nodes.filter((n) => (n.label || "").toLowerCase().includes("router"));
  const switches = nodes.filter((n) => (n.label || "").toLowerCase().includes("switch"));
  const hosts = nodes.filter(
    (n) => !(n.label || "").toLowerCase().includes("router") && !(n.label || "").toLowerCase().includes("switch"),
  ); // If any

  const populate = (listEl, items) => {
    listEl.innerHTML = "";
    items.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="dot" style="background-color: ${item.color || "#fff"}"></span> <span>${item.label}</span>`;
      li.onclick = () => {
        // Find actual node reference from graph state so D3 can highlight correctly
        const nodeRef = appState.nodes.find((n) => n.id === item.id);
        if (nodeRef) {
          appState.setState({
            view: "node",
            selectedNode: nodeRef,
            selectedPort: null,
          });
        }
      };
      // Highlighting class logic can be added here
      if (appState.selectedNode && appState.selectedNode.id === item.id) {
        li.classList.add("active");
      }
      listEl.appendChild(li);
    });
  };

  populate(routersList, routers);
  populate(switchesList, switches);
  populate(hostsList, hosts);
}

// Subscribe to state changes to update the UI
appState.subscribe((state) => {
  // 1. Views toggling
  if (state.view === "landing") {
    if (initOverlay) initOverlay.classList.remove("hidden");
    viewApp.classList.add("hidden");
    return;
  } else {
    if (initOverlay) initOverlay.classList.add("hidden");
    viewApp.classList.remove("hidden");
    
    // Set UI based on mock mode
    const isMock = localStorage.getItem("isMock") === "true";
    if (isMock) {
      const badge = document.getElementById("demo-badge");
      if (badge) badge.classList.remove("hidden");
      const retryBtn = document.getElementById("btn-retry-discovery");
      if (retryBtn) retryBtn.classList.add("hidden");
    } else {
      const badge = document.getElementById("demo-badge");
      if (badge) badge.classList.add("hidden");
      const retryBtn = document.getElementById("btn-retry-discovery");
      if (retryBtn) retryBtn.classList.remove("hidden");
    }
  }

  // 2. Sidebar active states
  parseSidebarLists(state.nodes); // Re-render to update active styling

  // 3. Bottom Panel
  if (state.view === "main") {
    bottomPanel.classList.remove("active", "port-mode");
    bottomPanel.classList.add("hidden");
    rightPanel.classList.add("hidden");
    btnBack.classList.add("hidden");
    breadcrumb.textContent = "Topographie du Réseau";

    // Resize after animating out slightly
    setTimeout(() => resizeGraph("graph-container"), 500);
  } else if (state.view === "node" && state.selectedNode) {
    const sn = state.selectedNode;
    const isHost = !(sn.label || "").toLowerCase().includes("router") && !(sn.label || "").toLowerCase().includes("switch");

    if (isHost) {
      bottomPanel.classList.add("hidden");
      bottomPanel.classList.remove("active", "port-mode");
      rightPanel.classList.remove("hidden");
      btnBack.classList.remove("hidden");
      breadcrumb.textContent = `Hôte: ${sn.label}`;

      rightPanelContent.innerHTML = `
        <div class="port-title-large">PC: ${sn.label}</div>
        <div class="config-grid" style="display:flex; flex-direction:column; gap:1.5rem; margin-top: 1.5rem;">
          <div class="form-group">
            <label>Nom</label>
            <div class="input-wrapper">
              <input type="text" value="${sn.label}" disabled style="background:#333; color:#aaa; cursor:not-allowed;">
            </div>
          </div>
          <div class="form-group">
            <label>Adresse IP</label>
            <div class="input-wrapper">
              <input id="host-mgmt_ip" type="text" value="${sn.mgmt_ip || ''}" placeholder="ex: 192.168.1.10">
            </div>
          </div>
          <div class="form-group">
            <label>Masque de sous-réseau</label>
            <div class="input-wrapper">
              <input id="host-device_type" type="text" value="${(sn.device_type !== 'cisco_ios' && sn.device_type !== 'host' && sn.device_type !== null) ? sn.device_type : '255.255.255.0'}" placeholder="ex: 255.255.255.0">
            </div>
          </div>
        </div>
        <div class="bottom-actions" style="margin-top:auto; padding-top:2rem;">
          <button id="btn-save-host" class="primary-btn" style="margin-top:0;">Appliquer</button>
        </div>
      `;

      document.getElementById("btn-save-host").addEventListener("click", async () => {
        const btn = document.getElementById("btn-save-host");
        btn.textContent = "Saving...";
        const newSettings = {
          device_type: document.getElementById("host-device_type").value,
          mgmt_ip: document.getElementById("host-mgmt_ip").value,
          ssh_username: "",
          ssh_password: ""
        };
        try {
          const res = await fetch(`/api/node/${sn.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newSettings),
          });
          if (!res.ok) throw new Error("Failed to save host settings");
          
          sn.device_type = newSettings.device_type;
          sn.mgmt_ip = newSettings.mgmt_ip;
          
          btn.textContent = "Appliqué";
          setTimeout(() => btn.textContent = "Appliquer", 2000);
        } catch (e) {
          console.error(e);
          btn.textContent = "Erreur";
        }
      });
      setTimeout(() => resizeGraph("graph-container"), 50);
      updateGraphHighlights(state);
      return;
    }

    bottomPanel.classList.remove("hidden", "port-mode");
    bottomPanel.classList.add("active");
    rightPanel.classList.add("hidden");
    btnBack.classList.remove("hidden");
    breadcrumb.textContent = `Node: ${state.selectedNode.label}`;
    bottomPanelTitle.textContent = `Interfaces Connectées`;

    // Find connected links
    const connectedLinks = state.links.filter(
      (l) => l.source.id === sn.id || l.target.id === sn.id,
    );
    
    let tableHtml = '';

    // We don't render the host config in the bottom panel anymore.
    // Render node settings + links as a table for Routers/Switches
    tableHtml = `
        <div style="margin-bottom: 2rem; background: #2a2a2a; padding: 1rem; border-radius: 8px;">
          <h4 style="margin-top: 0; color: #aaa;">Paramètres de l'Équipement</h4>
          <div class="config-grid" style="display:flex; gap:1rem; flex-wrap:wrap;">
            <div class="form-group" style="flex:1;">
              <label>Device Type</label>
              <div class="input-wrapper">
                <input id="node-device_type" type="text" value="${sn.device_type || 'cisco_ios'}" placeholder="e.g. cisco_ios">
              </div>
            </div>
            <div class="form-group" style="flex:1;">
              <label>Management IP</label>
              <div class="input-wrapper">
                <input id="node-mgmt_ip" type="text" value="${sn.mgmt_ip || ''}" placeholder="e.g. 192.168.1.2">
              </div>
            </div>
            <div class="form-group" style="flex:1;">
              <label>SSH Username</label>
              <div class="input-wrapper">
                <input id="node-ssh_username" type="text" value="${sn.ssh_username || ''}" placeholder="e.g. admin">
              </div>
            </div>
            <div class="form-group" style="flex:1;">
              <label>SSH Password</label>
              <div class="input-wrapper">
                <input id="node-ssh_password" type="password" placeholder="Leave blank to keep current">
              </div>
            </div>
            <div style="display:flex; align-items:flex-end;">
              <button id="btn-save-node" class="primary-btn">Save Device</button>
            </div>
          </div>
        </div>
      `;

      if (connectedLinks.length === 0) {
        tableHtml += `<p>Pas d'interface connectée.</p>`;
        bottomPanelContent.innerHTML = tableHtml;
      } else {
        tableHtml += `<table class="data-table">
            <thead><tr><th>Port</th><th>VLAN</th><th>IP du port</th></tr></thead>
            <tbody>`;

        connectedLinks.forEach((link, idx) => {
          tableHtml += `<tr data-linkid="${link.portId}" data-portidx="${idx + 1}" class="port-row">
              <td>Port ${idx + 1} (${link.source.id === sn.id ? link.target.id : link.source.id})</td>
              <td>${link.config.vlan}</td>
              <td>${link.config.ipv4}</td>
            </tr>`;
        });
        tableHtml += `</tbody></table>`;
        bottomPanelContent.innerHTML = tableHtml;

        // Add click listeners to rows
        document.querySelectorAll(".port-row").forEach((row) => {
          row.addEventListener("click", () => {
            const lid = row.getAttribute("data-linkid");
            const portIndex = row.getAttribute("data-portidx");
            const pLink = state.links.find((l) => l.portId === lid);
            if (pLink) {
              pLink.portNameRendered = `Port ${portIndex}`;
              appState.setState({ view: "port", selectedPort: pLink });
            }
          });
        });
      }

    // Add event listener for saving node
    const btnSaveNode = document.getElementById("btn-save-node");
    if (btnSaveNode) {
      btnSaveNode.addEventListener("click", async () => {
        btnSaveNode.textContent = "Saving...";
        const newSettings = {
          device_type: document.getElementById("node-device_type").value,
          mgmt_ip: document.getElementById("node-mgmt_ip").value,
          ssh_username: document.getElementById("node-ssh_username").value,
          ssh_password: document.getElementById("node-ssh_password").value
        };
        try {
          const res = await fetch(`/api/node/${sn.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newSettings),
          });
          if (!res.ok) throw new Error("Failed to save node settings");
          
          sn.device_type = newSettings.device_type;
          sn.mgmt_ip = newSettings.mgmt_ip;
          sn.ssh_username = newSettings.ssh_username;
          // password isn't stored locally
          
          btnSaveNode.textContent = "Saved!";
          setTimeout(() => btnSaveNode.textContent = "Save Device", 2000);
        } catch (e) {
          console.error(e);
          btnSaveNode.textContent = "Error";
        }
      });
    }

    // Resize graph
    setTimeout(() => resizeGraph("graph-container"), 50);
  } else if (state.view === "port" && state.selectedPort) {
    bottomPanel.classList.remove("hidden");
    bottomPanel.classList.add("active", "port-mode");
    rightPanel.classList.remove("hidden");
    btnBack.classList.remove("hidden");
    const sp = state.selectedPort;
    const targetLabel =
      sp.source === state.selectedNode ? sp.target.label : sp.source.label;
    breadcrumb.textContent = `Node: ${state.selectedNode.label} > Port to ${targetLabel}`;

    const cfg = sp.config;
    bottomPanelContent.innerHTML = `<div class="port-title-large">${sp.portNameRendered || "Port"}</div>`;

    rightPanelContent.innerHTML = `
      <div class="config-grid" style="display:flex; flex-direction:column; gap:1.5rem;">
        <div class="form-group">
          <label>Interface Name (e.g. Gi1/0/1)</label>
          <div class="input-wrapper">
            <input id="cfg-interface_name" type="text" value="${cfg.interface_name || ''}">
          </div>
        </div>
        <div class="form-group">
          <label>Mode</label>
          <div class="input-wrapper">
            <select id="cfg-mode" style="width:100%; padding:8px; border-radius:4px; border:1px solid #555; background:#222; color:white;">
                <option value="access" ${cfg.mode === 'access' ? 'selected' : ''}>Access</option>
                <option value="trunk" ${cfg.mode === 'trunk' ? 'selected' : ''}>Trunk</option>
            </select>
          </div>
        </div>
        <div class="form-group" style="display:flex; align-items:center; gap:10px;">
          <label>Portfast</label>
          <input id="cfg-portfast" type="checkbox" ${cfg.portfast ? 'checked' : ''}>
        </div>
        <div class="form-group">
          <label>Allowed VLANs (e.g. 10,20,30)</label>
          <div class="input-wrapper">
            <input id="cfg-allowed_vlans" type="text" value="${cfg.allowed_vlans || ''}">
          </div>
        </div>
        <div class="form-group">
          <label>VLAN</label>
          <div class="input-wrapper">
            <input id="cfg-vlan" type="text" value="${cfg.vlan}">
          </div>
        </div>
        <div class="form-group">
          <label>IPV4</label>
          <div class="input-wrapper">
            <input id="cfg-ipv4" type="text" value="${cfg.ipv4}">
          </div>
        </div>
        <div class="form-group">
          <label>IPV6</label>
          <div class="input-wrapper">
            <input id="cfg-ipv6" type="text" value="${cfg.ipv6}">
          </div>
        </div>
        <div class="form-group">
          <label>Masque sous-réseau</label>
          <div class="input-wrapper">
            <input id="cfg-mask" type="text" value="${cfg.mask}">
          </div>
        </div>
        <div class="form-group">
          <label>Gateway</label>
          <div class="input-wrapper">
            <input id="cfg-gw" type="text" value="${cfg.gateway}">
          </div>
        </div>
      </div>
      <div class="bottom-actions" style="margin-top:auto; padding-top:2rem;">
        <button class="secondary-btn">Vérifier</button>
        <button id="btn-apply-config" class="primary-btn" style="margin-top:0;">Appliquer</button>
      </div>
    `;

    document.getElementById("btn-apply-config").addEventListener("click", async () => {
      const btn = document.getElementById("btn-apply-config");
      btn.textContent = "Saving...";
      
      const newConfig = {
        ipv4: document.getElementById("cfg-ipv4").value,
        ipv6: document.getElementById("cfg-ipv6").value,
        mask: document.getElementById("cfg-mask").value,
        gateway: document.getElementById("cfg-gw").value,
        vlan: document.getElementById("cfg-vlan").value,
        interface_name: document.getElementById("cfg-interface_name").value,
        mode: document.getElementById("cfg-mode").value,
        portfast: document.getElementById("cfg-portfast").checked,
        allowed_vlans: document.getElementById("cfg-allowed_vlans").value,
      };

      try {
        const res = await fetch(`/api/config/${sp.portId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(newConfig),
        });
        if (!res.ok) throw new Error("Failed to save config");
        sp.config = newConfig; // update local state
        btn.textContent = "Appliqué";
        setTimeout(() => btn.textContent = "Appliquer", 2000);
      } catch (err) {
        console.error(err);
        btn.textContent = "Erreur";
      }
    });

    // Resize graph
    setTimeout(() => resizeGraph("graph-container"), 50);
  }

  // 4. Graph highlighting
  updateGraphHighlights(state);
});

// Admin Assess and Push Logic
const assessBtn = document.getElementById("btn-assess-push");
if (assessBtn) {
  assessBtn.addEventListener("click", async () => {
    const modal = document.getElementById("assessment-overlay");
    const content = document.getElementById("assessment-content");
    modal.classList.remove("hidden");
    content.innerHTML = "<p>Loading security assessment...</p>";
    
    try {
      const res = await fetch("/api/network/assess");
      if (!res.ok) throw new Error("Assessment failed to load");
      const data = await res.json();
      
      let html = "";
      let hasErrors = false;
      data.forEach(node => {
        if (node.errors.length > 0 || node.warnings.length > 0) {
          html += `<div style="margin-bottom: 1rem; padding: 1rem; background: #333; border-left: 4px solid ${node.errors.length > 0 ? '#e74c3c' : '#f39c12'};">
            <h4 style="margin-top: 0;">${node.label} (${node.node_id})</h4>
            <ul style="margin: 0; padding-left: 20px; color: #ffcccc;">`;
          node.errors.forEach(e => html += `<li><strong>ERROR:</strong> ${e}</li>`);
          node.warnings.forEach(w => html += `<li style="color: #ffebcc;"><strong>WARNING:</strong> ${w}</li>`);
          html += `</ul></div>`;
          if (node.errors.length > 0) hasErrors = true;
        }
      });
      
      if (!html) {
        html = "<p style='color: #2ecc71;'>All clear! No security warnings or configuration errors found.</p>";
      }
      
      if (hasErrors) {
        html += "<p style='color: #e74c3c; font-weight: bold;'>Cannot push configuration due to critical errors. Please fix them in the draft.</p>";
        document.getElementById("btn-confirm-push").disabled = true;
        document.getElementById("btn-confirm-push").style.opacity = "0.5";
      } else {
        document.getElementById("btn-confirm-push").disabled = false;
        document.getElementById("btn-confirm-push").style.opacity = "1";
      }
      
      content.innerHTML = html;
    } catch (e) {
      content.innerHTML = `<p style="color: red;">Error: ${e.message}</p>`;
    }
  });
}

const cancelPushBtn = document.getElementById("btn-cancel-push");
if (cancelPushBtn) {
  cancelPushBtn.addEventListener("click", () => {
    document.getElementById("assessment-overlay").classList.add("hidden");
  });
}

const confirmPushBtn = document.getElementById("btn-confirm-push");
if (confirmPushBtn) {
  confirmPushBtn.addEventListener("click", async () => {
    document.getElementById("assessment-overlay").classList.add("hidden");
    const overlay = document.getElementById("discovery-overlay");
    overlay.classList.remove("hidden");
    document.getElementById("discovery-status-text").textContent = "Pushing configuration to physical devices...";
    
    try {
      const res = await fetch("/api/network/push", { method: "POST" });
      if (!res.ok) throw new Error("Push failed");
      
      // Poll until push completes (discovery_status -> completed)
      const pollStatus = async () => {
        try {
          const statusRes = await fetch("/api/network/status");
          const statusData = await statusRes.json();
          if (statusData.status === "completed") {
            overlay.classList.add("hidden");
            alert("Push successful!");
          } else {
            setTimeout(pollStatus, 2000);
          }
        } catch (e) {
          setTimeout(pollStatus, 2000);
        }
      };
      setTimeout(pollStatus, 2000);
    } catch (e) {
      overlay.classList.add("hidden");
      alert("Push error: " + e.message);
    }
  });
}

// Event Listeners
const retryBtn = document.getElementById("btn-retry-discovery");
if (retryBtn) {
  retryBtn.addEventListener("click", async () => {
    const overlay = document.getElementById("discovery-overlay");
    overlay.classList.remove("hidden");
    document.getElementById("discovery-status-text").textContent = "Retrying SSH Discovery...";
    
    try {
      await fetch("/api/network/discover", { method: "POST" });
      
      const pollStatus = async () => {
        try {
          const statusRes = await fetch("/api/network/status");
          const statusData = await statusRes.json();
          if (statusData.status === "completed") {
            overlay.classList.add("hidden");
            const newData = await loadData();
            appState.setState({
              view: "main",
              nodes: newData.nodes,
              links: newData.edges,
            });
            // Re-init graph with new data
            document.getElementById("graph-container").innerHTML = "";
            initGraph("graph-container", newData.nodes, newData.edges, (node) => {
              appState.setState({
                view: "node",
                selectedNode: node,
                selectedPort: null,
              });
            });
          } else {
            const statusText = document.getElementById("discovery-status-text");
            if (statusText) {
              statusText.textContent = `Pending: ${statusData.pending && statusData.pending.length ? statusData.pending.join(', ') : 'none'} | Failed: ${statusData.failed && statusData.failed.length ? statusData.failed.join(', ') : 'none'}`;
            }
            setTimeout(pollStatus, 2000);
          }
        } catch (e) {
          setTimeout(pollStatus, 2000);
        }
      };
      pollStatus();
    } catch (e) {
      overlay.classList.add("hidden");
      alert("Error starting discovery: " + e.message);
    }
  });
}

btnClosePanel.addEventListener("click", () => {
  if (appState.view === "port") {
    // Go back to node view
    appState.setState({ view: "node", selectedPort: null });
  } else {
    // Go back to main view
    appState.setState({ view: "main", selectedNode: null, selectedPort: null });
  }
});

if (btnCloseRight) {
  btnCloseRight.addEventListener("click", () => {
    if (appState.view === "node") {
      appState.setState({ view: "main", selectedNode: null, selectedPort: null });
    } else {
      appState.setState({ view: "node", selectedPort: null });
    }
  });
}

btnBack.addEventListener("click", () => {
  if (appState.view === "port") {
    appState.setState({ view: "node", selectedPort: null });
  } else if (appState.view === "node") {
    appState.setState({ view: "main", selectedNode: null, selectedPort: null });
  }
});
