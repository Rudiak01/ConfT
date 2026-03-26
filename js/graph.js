import { appState } from './state.js';

let svg, g, zoom;
let simulation, link, node, text;
let width, height;

export function initGraph(containerId, nodes, links, onNodeClick) {
  const container = document.getElementById(containerId);
  width = container.clientWidth || window.innerWidth - 320;
  height = container.clientHeight || window.innerHeight;

  d3.select(`#${containerId}`).selectAll("*").remove();

  svg = d3.select(`#${containerId}`).append("svg")
    .attr("width", width)
    .attr("height", height);

  g = svg.append("g");

  zoom = d3.zoom().scaleExtent([0.1, 4]).on("zoom", () => {
    g.attr("transform", d3.event.transform);
  });
  svg.call(zoom);

  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(d => {
      const sourceLinks = links.filter(l => l.source.id === d.source.id || l.target.id === d.source.id).length;
      const targetLinks = links.filter(l => l.source.id === d.target.id || l.target.id === d.target.id).length;
      return Math.min(150, Math.max(50, (sourceLinks + targetLinks) * 10));
    }))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .alphaDecay(0.02)
    .alphaMin(0.001)
    .on("tick", ticked);

  link = g.append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(links)
    .enter().append("line")
    .attr("class", "link")
    .attr("stroke-width", 4)
    .style("stroke", "#999")
    .style("opacity", 0.6);

  node = g.append("g")
    .attr("class", "nodes")
    .selectAll("circle")
    .data(nodes)
    .enter().append("circle")
    .attr("class", "node")
    .attr("r", d => 5 + (d.link_count || 1) * 3)
    .attr("fill", d => d.color || "#ccc")
    .on("click", (d) => onNodeClick(d))
    .on("mouseover", function(d) {
      if(appState.view === 'main') {
        d3.select(this).attr("fill", "var(--accent-color)").attr("r", 10 + (d.link_count || 1) * 2);
        link.style("stroke", l => l.source === d || l.target === d ? "var(--primary-color)" : "#999")
            .style("opacity", l => l.source === d || l.target === d ? 1 : 0.2);
        node.style("opacity", n => {
          const isConnected = links.some(l => (l.source === d && l.target === n) || (l.target === d && l.source === n));
          return isConnected || n === d ? 1 : 0.2;
        });
      }
    })
    .on("mouseout", function(d) {
      if(appState.view === 'main') {
        d3.select(this).attr("fill", n => n.color || "#ccc").attr("r", n => 5 + (n.link_count || 1) * 3);
        link.style("stroke", "#999").style("opacity", 0.6);
        node.style("opacity", 1);
      }
    });

  text = g.append("g")
    .attr("class", "texts")
    .selectAll("text")
    .data(nodes)
    .enter().append("text")
    .attr("x", 8)
    .attr("y", ".31em")
    .text(d => d.label)
    .style("fill", "#fff")
    .style("font-family", "inherit")
    .style("font-size", "12px");

  function ticked() {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node
      .attr("cx", d => d.x)
      .attr("cy", d => d.y);

    text
      .attr("x", d => d.x + 8)
      .attr("y", d => d.y + 3);
  }
}

export function updateGraphHighlights(state) {
  if (!node || !link) return;

  if (state.view === 'main') {
    // Reset highlights
    node.attr("fill", d => d.color || "#ccc").attr("r", d => 5 + (d.link_count || 1) * 3).style("opacity", 1);
    link.style("stroke", "#999").style("opacity", 0.6).attr("stroke-width", 4);
    text.style("opacity", 1);
    
    // reset zoom
    svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
  } 
  else if (state.view === 'node' && state.selectedNode) {
    const sn = state.selectedNode;
    
    // Highlight the selected node and its direct neighbors
    node.attr("fill", d => d === sn ? "var(--accent-color)" : (d.color || "#ccc"))
        .attr("r", d => d === sn ? 10 + (d.link_count || 1) * 3 : 5 + (d.link_count || 1) * 3)
        .style("opacity", d => {
          const isConnected = state.links.some(l => (l.source === sn && l.target === d) || (l.target === sn && l.source === d));
          return isConnected || d === sn ? 1 : 0.1;
        });

    link.style("stroke", l => l.source === sn || l.target === sn ? "var(--primary-color)" : "#999")
        .style("opacity", l => l.source === sn || l.target === sn ? 0.8 : 0.05)
        .attr("stroke-width", l => l.source === sn || l.target === sn ? 6 : 2);
    
    text.style("opacity", d => {
       const isConnected = state.links.some(l => (l.source === sn && l.target === d) || (l.target === sn && l.source === d));
       return isConnected || d === sn ? 1 : 0.1;
    });

    // Zoom to node
    const scale = 2;
    const x = width / 2 - sn.x * scale;
    const y = height / 2 - sn.y * scale; // removed offset since panel pushes graph up
    svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
  }
  else if (state.view === 'port' && state.selectedPort) {
    const sp = state.selectedPort;
    const sn = state.selectedNode;
    // Show only the selected port (link) and the two connected nodes
    node.style("opacity", d => (d === sp.source || d === sp.target) ? 1 : 0.05)
        .attr("fill", d => d === sn ? "var(--accent-color)" : (d.color || "#ccc"));
        
    link.style("stroke", l => l === sp ? "var(--accent-color)" : "#999")
        .style("opacity", l => l === sp ? 1 : 0.02)
        .attr("stroke-width", l => l === sp ? 8 : 2);
    
    text.style("opacity", d => (d === sp.source || d === sp.target) ? 1 : 0.05);

    // Zoom to link center
    const cx = (sp.source.x + sp.target.x) / 2;
    const cy = (sp.source.y + sp.target.y) / 2;
    const scale = 2.5;
    const x = width / 2 - cx * scale;
    const y = height / 2 - cy * scale;
    svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
  }
}

export function resizeGraph(containerId) {
  if (!svg || !simulation) return;
  const container = document.getElementById(containerId);
  width = container.clientWidth || width;
  height = container.clientHeight || height;
  
  svg.attr("width", width).attr("height", height);
  simulation.force("center", d3.forceCenter(width / 2, height / 2));
  simulation.alpha(0.3).restart();
}
