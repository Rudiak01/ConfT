import re

# PATCH APP.JS
with open("e:\\Projects\\ConfT\\js\\app.js", "r", encoding="utf-8") as f:
    app_js = f.read()

# 1. Replace fetch( with fetchWithAuth(
app_js = app_js.replace('fetch(', 'fetchWithAuth(')

# But wait, inside btn-login, we don't want fetchWithAuth. We'll add the auth code manually at the end, using standard fetch.

# 2. Inject fetchWithAuth definition
injection = """
const getAuthHeaders = () => {
  const token = localStorage.getItem("auth_token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
};

async function fetchWithAuth(url, options = {}) {
  options.headers = { ...options.headers, ...getAuthHeaders() };
  const res = await fetch(url, options);
  if (res.status === 401) {
    document.getElementById("auth-overlay").classList.remove("hidden");
    document.getElementById("app-wrapper").classList.add("hidden");
    document.getElementById("init-overlay").classList.add("hidden");
    throw new Error("Unauthorized");
  }
  return res;
}

let globalSettings = null;
"""
app_js = app_js.replace('import { initGraph, updateGraphHighlights, resizeGraph, setDragEnabled } from "./graph.js";', 'import { initGraph, updateGraphHighlights, resizeGraph, setDragEnabled } from "./graph.js";\n' + injection)


# 3. DOMContentLoaded Auth Check and Settings Load
domcontentloaded_original = """window.addEventListener("DOMContentLoaded", async () => {
  try {
    const settingsRes = await fetchWithAuth("/api/settings");"""

domcontentloaded_new = """window.addEventListener("DOMContentLoaded", async () => {
   const token = localStorage.getItem("auth_token");
   if(!token) {
     document.getElementById("auth-overlay").classList.remove("hidden");
     document.getElementById("app-wrapper").classList.add("hidden");
     document.getElementById("init-overlay").classList.add("hidden");
     return;
   } else {
     document.getElementById("auth-overlay").classList.add("hidden");
   }

   try {
     const setRes = await fetchWithAuth("/api/users/settings");
     globalSettings = await setRes.json();
     appState.userSettings = globalSettings;
     
     document.getElementById("set-theme").value = globalSettings.theme;
     document.getElementById("set-bg-color").value = globalSettings.bg_color;
     document.getElementById("set-def-color").value = globalSettings.default_node_color;
     document.getElementById("set-router-color").value = globalSettings.router_color;
     document.getElementById("set-switch-color").value = globalSettings.switch_color;
     document.getElementById("set-host-color").value = globalSettings.host_color;
     
     document.getElementById("graph-container").style.background = globalSettings.bg_color;
     if(document.getElementById("set-obsidian-bg").checked) {
       document.getElementById("graph-container").classList.add("obsidian-bg");
     }
   } catch(e) {}

  try {
    const settingsRes = await fetchWithAuth("/api/settings");"""

app_js = app_js.replace(domcontentloaded_original, domcontentloaded_new)

# 4. Inject Node Custom Color UI
custom_color_html = """            <div class="form-group" style="flex:1;">
              <label>STP Root VLAN</label>"""
custom_color_replacement = """            <div class="form-group" style="flex:1;">
              <label>Couleur personnalisée</label>
              <div class="input-wrapper" style="display:flex; gap:10px;">
                <input id="node-custom-color" type="color" value="${(globalSettings && globalSettings.node_colors && globalSettings.node_colors[sn.id]) || '#cccccc'}" style="padding:0; height:38px; width: 100px;">
                <button id="btn-save-node-color" class="secondary-btn" style="padding: 0.2rem 1rem;">Appliquer</button>
              </div>
            </div>
            <div class="form-group" style="flex:1;">
              <label>STP Root VLAN</label>"""
app_js = app_js.replace(custom_color_html, custom_color_replacement)

# 5. Inject event listener for btn-save-node-color inside the render block
save_node_btn = """    const btnSaveNode = document.getElementById("btn-save-node");"""
save_node_color_js = """    const btnSaveNodeColor = document.getElementById("btn-save-node-color");
    if(btnSaveNodeColor) {
      btnSaveNodeColor.addEventListener("click", async () => {
        const c = document.getElementById("node-custom-color").value;
        await fetchWithAuth(`/api/nodes/${sn.id}/color`, {
           method: "PUT", headers: {"Content-Type": "application/json"},
           body: JSON.stringify({color: c})
        });
        if(!globalSettings.node_colors) globalSettings.node_colors = {};
        globalSettings.node_colors[sn.id] = c;
        appState.userSettings = globalSettings;
        updateGraphHighlights(appState.getState());
      });
    }
    
    const btnSaveNode = document.getElementById("btn-save-node");"""
app_js = app_js.replace(save_node_btn, save_node_color_js)

# 6. Add Auth & Settings Listeners at the end of app.js
auth_listeners = """
// --- AUTH & SETTINGS ---
const btnLogin = document.getElementById("btn-login");
if(btnLogin) {
  btnLogin.addEventListener("click", async () => {
    const u = document.getElementById("login-username").value;
    const p = document.getElementById("login-password").value;
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username: u, password: p})
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      localStorage.setItem("auth_token", data.token);
      window.location.reload();
    } catch (e) {
      document.getElementById("login-error").style.display = "block";
    }
  });
}

const btnLogout = document.getElementById("btn-logout");
if(btnLogout) {
  btnLogout.addEventListener("click", () => {
    localStorage.removeItem("auth_token");
    window.location.reload();
  });
}

const btnSettings = document.getElementById("btn-settings");
if(btnSettings) {
  btnSettings.addEventListener("click", async () => {
    document.getElementById("settings-overlay").classList.remove("hidden");
    try {
      const me = await (await fetchWithAuth("/api/auth/me")).json();
      if(me.is_admin) {
        document.getElementById("tab-users-btn").style.display = "block";
        const users = await (await fetchWithAuth("/api/users")).json();
        document.getElementById("users-list-container").innerHTML = users.map(u => `<div>${u.username} ${u.is_admin ? '(Admin)' : ''}</div>`).join('');
      }
    } catch(e) {}
  });
}

const btnCloseSettings = document.getElementById("btn-close-settings");
if(btnCloseSettings) {
  btnCloseSettings.addEventListener("click", () => {
    document.getElementById("settings-overlay").classList.add("hidden");
  });
}

document.querySelectorAll(".modal-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".modal-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.getAttribute("data-tab")).classList.add("active");
  });
});

const btnSaveAppearance = document.getElementById("btn-save-appearance");
if(btnSaveAppearance) {
  btnSaveAppearance.addEventListener("click", async () => {
    const newSet = {
      theme: document.getElementById("set-theme").value,
      bg_color: document.getElementById("set-bg-color").value,
      default_node_color: document.getElementById("set-def-color").value,
      router_color: document.getElementById("set-router-color").value,
      switch_color: document.getElementById("set-switch-color").value,
      host_color: document.getElementById("set-host-color").value
    };
    await fetchWithAuth("/api/users/settings", {
      method: "PUT", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(newSet)
    });
    window.location.reload();
  });
}

const btnCreateUser = document.getElementById("btn-create-user");
if(btnCreateUser) {
  btnCreateUser.addEventListener("click", async () => {
    const u = document.getElementById("new-user-name").value;
    const p = document.getElementById("new-user-pass").value;
    const a = document.getElementById("new-user-admin").checked;
    await fetchWithAuth("/api/users", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username: u, password: p, is_admin: a})
    });
    alert("Utilisateur créé !");
    document.getElementById("btn-settings").click(); // reload users
  });
}

const obsidianCb = document.getElementById("set-obsidian-bg");
if (obsidianCb) {
  obsidianCb.addEventListener("change", (e) => {
    if(e.target.checked) document.getElementById("graph-container").classList.add("obsidian-bg");
    else document.getElementById("graph-container").classList.remove("obsidian-bg");
  });
}
"""

app_js += auth_listeners

with open("e:\\Projects\\ConfT\\js\\app.js", "w", encoding="utf-8") as f:
    f.write(app_js)

print("Patching app.js done")

# PATCH GRAPH.JS
with open("e:\\Projects\\ConfT\\js\\graph.js", "r", encoding="utf-8") as f:
    graph_js = f.read()

# 1. Add getNodeColor(d)
get_node_color = """
export function getNodeColor(d) {
  const set = appState.userSettings;
  if(!set) return d.color || "#ccc";
  
  if(set.node_colors && set.node_colors[d.id]) {
    return set.node_colors[d.id];
  }
  
  const label = (d.label || "").toLowerCase();
  if(label.includes("router")) return set.router_color;
  if(label.includes("switch") || label.includes("core") || label.includes("dist") || label.includes("access")) return set.switch_color;
  if(label.includes("host") || d.true_link_count <= 1) return set.host_color;
  
  return set.default_node_color;
}

function getNodeRadius(d, state = 'normal') {"""

graph_js = graph_js.replace("function getNodeRadius(d, state = 'normal') {", get_node_color)

# 2. Replace d.color || "#ccc" with getNodeColor(d)
graph_js = graph_js.replace('d.color || "#ccc"', 'getNodeColor(d)')
graph_js = graph_js.replace('n.color || "#ccc"', 'getNodeColor(n)')

with open("e:\\Projects\\ConfT\\js\\graph.js", "w", encoding="utf-8") as f:
    f.write(graph_js)

print("Patching graph.js done")
