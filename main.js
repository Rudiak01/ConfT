async function loadedges() {
  try {
    let edges;
    const res_edge = await fetch("node_edge/outputedges.json");
    edges = await res_edge.json();
    return edges;
  } catch (err) {
    console.error(err);
  }
}
async function loadnode() {
  try {
    let nodes;
    const res_node = await fetch("node_edge/outputnodes.json");
    nodes = await res_node.json();
    return nodes;
  } catch (err) {
    console.error(err);
  }
}
let links = [];
let nodes = [];
async function init() {
  links = await loadedges();
  nodes = await loadnode();
}
await init();

var colorGroups = [];

var width = window.innerWidth;
var height = window.innerHeight;

var svg = d3
  .select("#graph")
  .append("svg")
  .attr("width", width)
  .attr("height", height);

var g = svg.append("g");

var zoom = d3.zoom().scaleExtent([0.1, 4]).on("zoom", zoomed);
svg.call(zoom);

function zoomed() {
  g.attr("transform", d3.event.transform);
}

function customForce(alpha) {
  const centerX = width / 2;
  const centerY = height / 2;
  const strength = 0.05;

  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    node.vx += (centerX - node.x) * strength * alpha;
    node.vy += (centerY - node.y) * strength * alpha;
  }
}

var simulation = d3
  .forceSimulation(nodes)
  .force(
    "link",
    d3
      .forceLink(links)
      .id((d) => d.id)
      .distance((d) => {
        const sourceLinks = links.filter(
          (link) =>
            link.source.id === d.source.id || link.target.id === d.source.id,
        ).length;
        const targetLinks = links.filter(
          (link) =>
            link.source.id === d.target.id || link.target.id === d.target.id,
        ).length;
        return Math.min(150, Math.max(50, (sourceLinks + targetLinks) * 10));
      }),
  )
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("custom", customForce)
  .force("collision", labelCollision())
  .alphaDecay(0.02)
  .alphaMin(0.001)
  .on("tick", ticked);

var link = g
  .append("g")
  .attr("class", "links")
  .selectAll("line")
  .data(links)
  .enter()
  .append("line")
  .attr("class", "link")
  .attr("stroke-width",4)
  //.style("stroke", "blue");

var node = g
  .append("g")
  .attr("class", "nodes")
  .selectAll("circle")
  .data(nodes)
  .enter()
  .append("circle")
  .attr("class", "node")
  .attr("r", function (d) {
    var radius = 5 + d.link_count * 3;
    return radius;
  })
  .attr("fill", function (d) {
    return d.color;
  })
    // .call( //activate drag
    //   d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended),
    // )
  .on("click", function (event, d) {
    console.log("Clic sur le nœud :", d);
  });
var text = g
  .append("g")
  .attr("class", "texts")
  .selectAll("text")
  .data(nodes)
  .enter()
  .append("text")
  .attr("x", 8)
  .attr("y", ".31em")
  .text((d) => d.label);

function ticked() {
  link
    .attr("x1", (d) => d.source.x)
    .attr("y1", (d) => d.source.y)
    .attr("x2", (d) => d.target.x)
    .attr("y2", (d) => d.target.y);

  node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);

  text.attr("x", (d) => d.x + 8).attr("y", (d) => d.y + 3);
}

function dragstarted(d) {
  if (!d3.event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(d) {
  d.fx = d3.event.x;
  d.fy = d3.event.y;
}

function dragended(d) {
  if (!d3.event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

function labelCollision() {
  var alpha = 0.5;
  return function () {
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var nodeA = nodes[i];
        var nodeB = nodes[j];
        if (nodeA === nodeB) continue;

        var dx = nodeA.x - nodeB.x;
        var dy = nodeA.y - nodeB.y;
        var distance = Math.sqrt(dx * dx + dy * dy);
        var minDistance = 20;

        if (distance < minDistance) {
          var moveFactor = ((minDistance - distance) / distance) * alpha;
          var mx = dx * moveFactor;
          var my = dy * moveFactor;
          nodeA.x += mx;
          nodeA.y += my;
          nodeB.x -= mx;
          nodeB.y -= my;
        }
      }
    }
  };
}
