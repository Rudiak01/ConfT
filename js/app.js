import { appState } from "./state.js";
import { initGraph, updateGraphHighlights, resizeGraph } from "./graph.js";

// DOM Elements
const viewLanding = document.getElementById("landing-view");
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

// Data structures for random config generation
const generateMockConfig = () => {
  return {
    ipv4: `192.168.${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 254) + 1}`,
    ipv6: `fe80::${Math.floor(Math.random() * 9e4)}`,
    mask: "255.255.255.0",
    gateway: "192.168.0.1",
    vlan: Math.floor(Math.random() * 20) + 1,
  };
};

async function loadData() {
  try {
    const resNodes = await fetch("node_edge/outputnodes.json");
    const nodes = await resNodes.json();
    const resEdges = await fetch("node_edge/outputedges.json");
    const edges = await resEdges.json();

    // Add mock configurations to edges to simulate port data
    edges.forEach((edge, i) => {
      edge.portId = `port-${i + 1}`;
      edge.config = generateMockConfig();
    });

    return { nodes, edges };
  } catch (err) {
    console.error("Failed to load data", err);
    return { nodes: [], edges: [] };
  }
}

function parseSidebarLists(nodes) {
  const routers = nodes.filter((n) => n.id.includes("router"));
  const switches = nodes.filter((n) => n.id.includes("switch"));
  const hosts = nodes.filter(
    (n) => !n.id.includes("router") && !n.id.includes("switch"),
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
    viewLanding.classList.add("active");
    viewApp.classList.add("hidden");
    return;
  } else {
    viewLanding.classList.remove("active");
    viewApp.classList.remove("hidden");
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
    bottomPanel.classList.remove("hidden", "port-mode");
    bottomPanel.classList.add("active");
    rightPanel.classList.add("hidden");
    btnBack.classList.remove("hidden");
    breadcrumb.textContent = `Node: ${state.selectedNode.label}`;
    bottomPanelTitle.textContent = `Interfaces Connectées`;

    // Find connected links
    const sn = state.selectedNode;
    const connectedLinks = state.links.filter(
      (l) => l.source.id === sn.id || l.target.id === sn.id,
    );

    // Render links as a table
    if (connectedLinks.length === 0) {
      bottomPanelContent.innerHTML = `<p>Pas d'interface connectée.</p>`;
    } else {
      let tableHtml = `<table class="data-table">
          <thead><tr><th>Port</th><th>VLAN</th><th>IP du port</th></tr></thead>
          <tbody>`;

      connectedLinks.forEach((link, idx) => {
        // We find index of link amongst connections as port index
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
          <label>IPV4</label>
          <div class="input-wrapper">
            <input type="text" value="${cfg.ipv4}">
          </div>
        </div>
        <div class="form-group">
          <label>IPV6</label>
          <div class="input-wrapper">
            <input type="text" value="${cfg.ipv6}">
          </div>
        </div>
        <div class="form-group">
          <label>Masque sous-réseau</label>
          <div class="input-wrapper">
            <input type="text" value="${cfg.mask}"
          </div>
        </div>
        <div class="form-group">
          <label>Gateway</label>
          <div class="input-wrapper">
            <input type="text" value="${cfg.gateway}">
          </div>
        </div>
        <div class="form-group">
          <label>Vlan</label>
          <div class="input-wrapper">
            <input type="text" value="${cfg.vlan}">
          </div>
        </div>
      </div>
      <div class="bottom-actions" style="margin-top:auto; padding-top:2rem;">
        <button class="secondary-btn">Vérifier</button>
        <button class="primary-btn" style="margin-top:0;">Appliquer</button>
      </div>
    `;

    // Resize graph
    setTimeout(() => resizeGraph("graph-container"), 50);
  }

  // 4. Graph highlighting
  updateGraphHighlights(state);
});

// Event Listeners
btnGetConfig.addEventListener("click", async () => {
  btnGetConfig.textContent = "Loading...";
  const data = await loadData();

  // First update state to make the container visible
  appState.setState({
    view: "main",
    nodes: data.nodes,
    links: data.edges,
  });

  // Wait for the DOM to update to get correct dimensions
  setTimeout(() => {
    // Initialize D3 graph
    initGraph("graph-container", data.nodes, data.edges, (node) => {
      appState.setState({
        view: "node",
        selectedNode: node,
        selectedPort: null,
      });
    });
  }, 50);
});

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
    appState.setState({ view: "node", selectedPort: null });
  });
}

btnBack.addEventListener("click", () => {
  if (appState.view === "port") {
    appState.setState({ view: "node", selectedPort: null });
  } else if (appState.view === "node") {
    appState.setState({ view: "main", selectedNode: null, selectedPort: null });
  }
});
