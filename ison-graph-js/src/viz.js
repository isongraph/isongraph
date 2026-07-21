/**
 * ISONGraph Visualization - deterministic layout and SVG/HTML rendering.
 *
 * Three-stage pipeline:
 * 1. Graph data - an ISONGraph instance.
 * 2. Layout     - computeLayout() runs a seeded, deterministic force
 *    simulation and assigns every node an (x, y) coordinate.
 * 3. Rendering  - renderSvg() / renderHtml() turn those coordinates into a
 *    standalone SVG image or a self-contained interactive HTML page.
 *
 * The layout algorithm and PRNG mirror `ison_graph.viz.compute_layout`
 * (Python) and the TypeScript port exactly: the same graph, size, and seed produce bit-identical
 * geometry in both languages. The PRNG is a portable 32-bit LCG
 * (state * 1664525 + 1013904223 mod 2^32).
 */






// Categorical palette (validated: CVD-safe adjacent pairs, both modes).
// Types get slots in sorted order; past 8 types fall back to OTHER.
export const LIGHT_PALETTE = [
  '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
  '#e87ba4', '#008300', '#4a3aa7', '#e34948',
];
export const DARK_PALETTE = [
  '#3987e5', '#d95926', '#199e70', '#c98500',
  '#d55181', '#008300', '#9085e9', '#e66767',
];
export const OTHER_LIGHT = '#7a7975';
export const OTHER_DARK = '#8f8e89';

const SURFACE_LIGHT = '#fcfcfb';
const SURFACE_DARK = '#1a1a19';
const INK_PRIMARY = '#0b0b0b';
const INK_SECONDARY = '#52514e';
const INK_PRIMARY_DARK = '#ffffff';
const INK_SECONDARY_DARK = '#c3c2b7';
const EDGE_LIGHT = '#d7d6d2';
const EDGE_DARK = '#3a3936';

/** Stable string key for a node ref, used by Layout maps. */
export function layoutKey(ref) {
  return `${ref[0]} ${String(ref[1])}`;
}

// ===========================================================================
// Stage 2: Layout
// ===========================================================================

/**
 * Compute a deterministic force-directed layout (Fruchterman-Reingold).
 *
 * Repulsion between every node pair, spring attraction along edges, and a
 * linear cooling schedule. The seed fixes the initial positions, so the same
 * graph, size, and seed always yield the same coordinates - across processes
 * and across language ports.
 */
export function computeLayout(graph, options = {}) {
  const width = options.width ?? 900;
  const height = options.height ?? 600;
  const iterations = options.iterations ?? 170;
  const seed = options.seed ?? 42;
  const margin = options.margin ?? 60;

  const refs = [];
  for (const node of graph.nodes()) {
    refs.push([node.type, String(node.id)]);
  }
  refs.sort((a, b) => {
    if (a[0] !== b[0]) return a[0] < b[0] ? -1 : 1;
    if (a[1] !== b[1]) return a[1] < b[1] ? -1 : 1;
    return 0;
  });

  const n = refs.length;
  const pos = new Map();
  if (n === 0) return pos;
  if (n === 1) {
    pos.set(`${refs[0][0]} ${refs[0][1]}`, [width / 2, height / 2]);
    return pos;
  }

  let state = seed >>> 0;
  const rand = () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };

  const innerW = Math.max(1, width - 2 * margin);
  const innerH = Math.max(1, height - 2 * margin);
  const keys = refs.map((r) => `${r[0]} ${r[1]}`);
  for (const key of keys) {
    pos.set(key, [margin + rand() * innerW, margin + rand() * innerH]);
  }

  // Springs: deduped unordered pairs, iterated in sorted order - float
  // accumulation order must be deterministic for cross-language parity.
  const springMap = new Map();
  for (const edge of graph.edges()) {
    const ka = `${edge.source[0]} ${String(edge.source[1])}`;
    const kb = `${edge.target[0]} ${String(edge.target[1])}`;
    if (ka === kb || !pos.has(ka) || !pos.has(kb)) continue;
    const pair = ka <= kb ? [ka, kb] : [kb, ka];
    springMap.set(`${pair[0]}|${pair[1]}`, pair);
  }
  const springs = Array.from(springMap.values());
  springs.sort((p, q) => {
    if (p[0] !== q[0]) return p[0] < q[0] ? -1 : 1;
    if (p[1] !== q[1]) return p[1] < q[1] ? -1 : 1;
    return 0;
  });

  const area = innerW * innerH;
  const k = Math.sqrt(area / n);
  let temp = Math.min(innerW, innerH) / 10;
  const cool = temp / (iterations + 1);

  for (let it = 0; it < iterations; it++) {
    const disp = new Map();
    for (const key of keys) disp.set(key, [0, 0]);

    for (let i = 0; i < n; i++) {
      const ki = keys[i];
      const pi = pos.get(ki);
      const di = disp.get(ki);
      for (let j = i + 1; j < n; j++) {
        const kj = keys[j];
        const pj = pos.get(kj);
        const dx = pi[0] - pj[0];
        const dy = pi[1] - pj[1];
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const force = (k * k) / dist;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const dj = disp.get(kj);
        di[0] += fx; di[1] += fy;
        dj[0] -= fx; dj[1] -= fy;
      }
    }

    for (const [a, b] of springs) {
      const pa = pos.get(a);
      const pb = pos.get(b);
      const dx = pa[0] - pb[0];
      const dy = pa[1] - pb[1];
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const force = (dist * dist) / k;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      const da = disp.get(a);
      const db = disp.get(b);
      da[0] -= fx; da[1] -= fy;
      db[0] += fx; db[1] += fy;
    }

    for (const key of keys) {
      const d = disp.get(key);
      const p = pos.get(key);
      const dist = Math.sqrt(d[0] * d[0] + d[1] * d[1]) || 0.01;
      const step = Math.min(dist, temp);
      const x = p[0] + (d[0] / dist) * step;
      const y = p[1] + (d[1] / dist) * step;
      p[0] = Math.min(width - margin, Math.max(margin, x));
      p[1] = Math.min(height - margin, Math.max(margin, y));
    }
    temp = Math.max(0.01, temp - cool);
  }

  // Deterministic collision pass: separate every pair to at least
  // (rA + rB) * spacing. Sorted pair order keeps this reproducible across
  // processes and language ports (mirrors the Python implementation).
  if (options.radii) {
    const spacing = options.spacing ?? 1;
    const radiiIn = options.radii;
    const getRad = (key) => {
      const v = radiiIn instanceof Map ? radiiIn.get(key) : radiiIn[key];
      return typeof v === 'number' ? v : 0;
    };
    const rad = new Map();
    for (const key of keys) rad.set(key, getRad(key));
    for (let pass = 0; pass < 50; pass++) {
      let moved = false;
      for (let i = 0; i < n; i++) {
        const ka = keys[i];
        for (let j = i + 1; j < n; j++) {
          const kb = keys[j];
          const minD = (rad.get(ka) + rad.get(kb)) * spacing;
          if (minD <= 0) continue;
          const pa = pos.get(ka);
          const pb = pos.get(kb);
          const dx = pb[0] - pa[0];
          const dy = pb[1] - pa[1];
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist >= minD) continue;
          let ux;
          let uy;
          if (dist < 1e-9) {
            ux = 1; uy = 0;
          } else {
            ux = dx / dist; uy = dy / dist;
          }
          const push = (minD - dist) / 2;
          pa[0] = Math.min(width - margin, Math.max(margin, pa[0] - ux * push));
          pa[1] = Math.min(height - margin, Math.max(margin, pa[1] - uy * push));
          pb[0] = Math.min(width - margin, Math.max(margin, pb[0] + ux * push));
          pb[1] = Math.min(height - margin, Math.max(margin, pb[1] + uy * push));
          moved = true;
        }
      }
      if (!moved) break;
    }
  }

  return pos;
}

// ===========================================================================
// Stage 3: Rendering
// ===========================================================================

function escapeXml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function quoteAttr(s) {
  return `"${escapeXml(s).replace(/"/g, '&quot;')}"`;
}

function typeSlots(graph) {
  const slots = new Map();
  const types = graph.nodeTypes().slice().sort();
  types.forEach((t, i) => slots.set(t, i));
  return slots;
}

function fillFor(slot, palette, other) {
  return slot < palette.length ? palette[slot] : other;
}

function radius(degree, dmin, dmax) {
  if (dmax <= dmin) return 9;
  return 6 + (10 * (degree - dmin)) / (dmax - dmin);
}

function nodeLabel(node, labelProperty) {
  if (labelProperty && labelProperty in node.properties) {
    return String(node.properties[labelProperty]);
  }
  if ('name' in node.properties) {
    return String(node.properties['name']);
  }
  return String(node.id);
}

/** Edges to draw: for undirected graphs, skip the auto-added reverse twin. */
function* visibleEdges(graph) {
  const seen = new Set();
  for (const edge of graph.edges()) {
    if (!graph.directed) {
      const ka = `${edge.source[0]} ${String(edge.source[1])}`;
      const kb = `${edge.target[0]} ${String(edge.target[1])}`;
      const key = ka <= kb
        ? `${edge.relType}|${ka}|${kb}`
        : `${edge.relType}|${kb}|${ka}`;
      if (seen.has(key)) continue;
      seen.add(key);
    }
    yield edge;
  }
}

function buildSvg(graph, layout, width, height, title, labelProperty, edgeLabels, classed) {
  const slots = typeSlots(graph);
  const degrees = new Map();
  for (const node of graph.nodes()) {
    degrees.set(layoutKey(node.ref), graph.degree(node.ref));
  }
  const dvals = Array.from(degrees.values());
  const dmin = dvals.length ? Math.min(...dvals) : 0;
  const dmax = dvals.length ? Math.max(...dvals) : 0;
  const directed = graph.directed;

  const parts = [];
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" ` +
    `viewBox="0 0 ${width} ${height}" role="img" ` +
    `aria-label=${quoteAttr(title ?? graph.name ?? 'graph')}>`,
  );
  if (!classed) {
    parts.push(`<rect width="${width}" height="${height}" fill="${SURFACE_LIGHT}"/>`);
  } else {
    parts.push(`<rect class="surface" width="${width}" height="${height}"/>`);
  }

  if (directed) {
    const arrowFill = classed ? '' : ` fill="${EDGE_LIGHT}"`;
    parts.push(
      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" ' +
      'markerWidth="7" markerHeight="7" orient="auto-start-reverse">' +
      `<path d="M 0 0 L 10 5 L 0 10 z" class="edge-arrow"${arrowFill}/></marker></defs>`,
    );
  }

  parts.push('<g class="edges">');
  for (const edge of visibleEdges(graph)) {
    const ks = layoutKey(edge.source);
    const kt = layoutKey(edge.target);
    const ps = layout.get(ks);
    const pt = layout.get(kt);
    if (!ps || !pt) continue;
    const x1 = ps[0];
    const y1 = ps[1];
    let x2 = pt[0];
    let y2 = pt[1];
    if (directed) {
      const r2 = radius(degrees.get(kt) ?? 0, dmin, dmax) + 3;
      const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) || 1;
      x2 -= ((x2 - x1) / dist) * r2;
      y2 -= ((y2 - y1) / dist) * r2;
    }
    const stroke = classed ? '' : ` stroke="${EDGE_LIGHT}"`;
    const marker = directed ? ' marker-end="url(#arrow)"' : '';
    parts.push(
      `<line class="edge" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" ` +
      `x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"${stroke} stroke-width="2"${marker}/>`,
    );
    if (edgeLabels) {
      const mx = (x1 + x2) / 2;
      const my = (y1 + y2) / 2;
      const fill = classed ? '' : ` fill="${INK_SECONDARY}"`;
      parts.push(
        `<text class="edge-label" x="${mx.toFixed(1)}" y="${(my - 4).toFixed(1)}" ` +
        `font-size="10" text-anchor="middle"${fill}>${escapeXml(edge.relType)}</text>`,
      );
    }
  }
  parts.push('</g>');

  parts.push('<g class="nodes">');
  for (const node of graph.nodes()) {
    const key = layoutKey(node.ref);
    const p = layout.get(key);
    if (!p) continue;
    const [x, y] = p;
    const slot = slots.get(node.type) ?? 0;
    const r = radius(degrees.get(key) ?? 0, dmin, dmax);
    const label = nodeLabel(node, labelProperty);
    let data = '';
    let paint;
    if (classed) {
      const props = JSON.stringify(node.properties);
      data = ` data-ref=${quoteAttr(`${node.type}:${node.id}`)} data-props=${quoteAttr(props)}`;
      paint = ` class="node t${slot}"`;
    } else {
      paint = ` class="node" fill="${fillFor(slot, LIGHT_PALETTE, OTHER_LIGHT)}" stroke="${SURFACE_LIGHT}"`;
    }
    parts.push(
      `<circle${paint} cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" stroke-width="2"${data}/>`,
    );
    const fill = classed ? '' : ` fill="${INK_SECONDARY}"`;
    parts.push(
      `<text class="node-label" x="${x.toFixed(1)}" y="${(y + r + 13).toFixed(1)}" font-size="12" ` +
      `font-family="system-ui, sans-serif" text-anchor="middle"${fill}>${escapeXml(label)}</text>`,
    );
  }
  parts.push('</g>');

  parts.push('<g class="legend">');
  let lx = 16;
  const ly = 24;
  for (const t of Array.from(slots.keys()).sort()) {
    const slot = slots.get(t);
    if (classed) {
      parts.push(`<circle class="t${slot}" cx="${lx.toFixed(1)}" cy="${(ly - 4).toFixed(1)}" r="6"/>`);
    } else {
      parts.push(
        `<circle cx="${lx.toFixed(1)}" cy="${(ly - 4).toFixed(1)}" r="6" ` +
        `fill="${fillFor(slot, LIGHT_PALETTE, OTHER_LIGHT)}"/>`,
      );
    }
    const fill = classed ? '' : ` fill="${INK_PRIMARY}"`;
    parts.push(
      `<text class="legend-label" x="${(lx + 12).toFixed(1)}" y="${ly.toFixed(1)}" font-size="12" ` +
      `font-family="system-ui, sans-serif"${fill}>${escapeXml(t)}</text>`,
    );
    lx += 24 + 7.2 * t.length;
  }
  parts.push('</g>');

  if (title) {
    const fill = classed ? '' : ` fill="${INK_PRIMARY}"`;
    parts.push(
      `<text class="title" x="${(width / 2).toFixed(1)}" y="${(height - 14).toFixed(1)}" font-size="13" ` +
      `font-family="system-ui, sans-serif" text-anchor="middle"${fill}>${escapeXml(title)}</text>`,
    );
  }

  parts.push('</svg>');
  return parts.join('\n');
}

/**
 * Render the graph to a standalone SVG string (light theme, inline colors).
 * If options.layout is omitted it is computed with computeLayout().
 */
export function renderSvg(graph, options = {}) {
  const width = options.width ?? 900;
  const height = options.height ?? 600;
  const layout = options.layout ?? computeLayout(graph, options);
  return buildSvg(
    graph, layout, width, height,
    options.title, options.labelProperty, options.edgeLabels ?? false, false,
  );
}

function themeCss(palette, other, surface, ink1, ink2, edge) {
  const rules = [
    `.surface{fill:${surface}}`,
    `.edge{stroke:${edge}} .edge-arrow{fill:${edge}}`,
    `.node{stroke:${surface}}`,
    `.node-label,.edge-label{fill:${ink2}}`,
    `.legend-label,.title{fill:${ink1}}`,
  ];
  palette.forEach((c, i) => rules.push(`.t${i}{fill:${c}}`));
  rules.push(`.t8,.t9,.t10,.t11,.t12,.t13,.t14,.t15{fill:${other}}`);
  return rules.join('\n');
}

/**
 * Render the graph to a self-contained interactive HTML page: light and dark
 * themes (follows the OS setting), hover tooltips with node properties, and
 * wheel-zoom / drag-pan. No external resources.
 */
export function renderHtml(graph, options = {}) {
  const width = options.width ?? 900;
  const height = options.height ?? 600;
  const layout = options.layout ?? computeLayout(graph, options);
  const name = options.title ?? graph.name ?? 'graph';
  const svg = buildSvg(
    graph, layout, width, height,
    options.title, options.labelProperty, options.edgeLabels ?? false, true,
  );

  const light = themeCss(LIGHT_PALETTE, OTHER_LIGHT, SURFACE_LIGHT, INK_PRIMARY, INK_SECONDARY, EDGE_LIGHT);
  const dark = themeCss(DARK_PALETTE, OTHER_DARK, SURFACE_DARK, INK_PRIMARY_DARK, INK_SECONDARY_DARK, EDGE_DARK);

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeXml(name)}</title>
<style>
html,body{margin:0;height:100%;background:${SURFACE_LIGHT}}
body{display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif}
#wrap{position:relative;max-width:100%;overflow:hidden}
svg{display:block;max-width:100%;height:auto;cursor:grab}
svg:active{cursor:grabbing}
.node{stroke-width:2px;cursor:pointer}
#tip{position:absolute;display:none;pointer-events:none;background:${INK_PRIMARY};color:${SURFACE_LIGHT};
padding:6px 10px;border-radius:6px;font-size:12px;max-width:280px;line-height:1.5;z-index:2}
${light}
@media (prefers-color-scheme: dark){
html,body{background:${SURFACE_DARK}}
#tip{background:${INK_PRIMARY_DARK};color:${SURFACE_DARK}}
${dark}
}
</style>
</head>
<body>
<div id="wrap">
${svg}
<div id="tip"></div>
</div>
<script>
(function () {
  var svg = document.querySelector('svg');
  var tip = document.getElementById('tip');
  var vb = svg.viewBox.baseVal;
  var view = {x: vb.x, y: vb.y, w: vb.width, h: vb.height};

  function apply() {
    svg.setAttribute('viewBox', view.x + ' ' + view.y + ' ' + view.w + ' ' + view.h);
  }

  svg.addEventListener('wheel', function (e) {
    e.preventDefault();
    var factor = e.deltaY < 0 ? 0.9 : 1.1;
    var rect = svg.getBoundingClientRect();
    var mx = view.x + (e.clientX - rect.left) / rect.width * view.w;
    var my = view.y + (e.clientY - rect.top) / rect.height * view.h;
    view.w *= factor; view.h *= factor;
    view.x = mx - (mx - view.x) * factor;
    view.y = my - (my - view.y) * factor;
    apply();
  }, {passive: false});

  var drag = null;
  svg.addEventListener('pointerdown', function (e) {
    drag = {x: e.clientX, y: e.clientY};
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener('pointermove', function (e) {
    if (!drag) return;
    var rect = svg.getBoundingClientRect();
    view.x -= (e.clientX - drag.x) / rect.width * view.w;
    view.y -= (e.clientY - drag.y) / rect.height * view.h;
    drag = {x: e.clientX, y: e.clientY};
    apply();
  });
  svg.addEventListener('pointerup', function () { drag = null; });

  document.querySelectorAll('.node').forEach(function (c) {
    c.addEventListener('mouseenter', function () {
      var props = JSON.parse(c.getAttribute('data-props') || '{}');
      var lines = ['<strong>' + c.getAttribute('data-ref') + '</strong>'];
      Object.keys(props).forEach(function (k) {
        lines.push(k + ': ' + String(props[k]));
      });
      tip.innerHTML = lines.join('<br>');
      tip.style.display = 'block';
    });
    c.addEventListener('mousemove', function (e) {
      var wrap = document.getElementById('wrap').getBoundingClientRect();
      tip.style.left = (e.clientX - wrap.left + 14) + 'px';
      tip.style.top = (e.clientY - wrap.top + 14) + 'px';
    });
    c.addEventListener('mouseleave', function () { tip.style.display = 'none'; });
  });
})();
</script>
</body>
</html>
`;
}
