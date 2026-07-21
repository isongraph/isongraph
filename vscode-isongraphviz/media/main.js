// ISONGraph Viz webview: deterministic layout + renderer + live physics.
// The layout mirrors ison_graph.viz.compute_layout exactly (same LCG PRNG,
// same node/spring ordering, same math) so the same graph and seed produce
// identical geometry here and in the Python renderer.

'use strict';

// ---------------------------------------------------------------------------
// Stage 2: deterministic layout (portable mirror of Python compute_layout)
// ---------------------------------------------------------------------------

function makeRand(seed) {
    let state = seed >>> 0;
    return function () {
        state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
        return state / 4294967296;
    };
}

function refKey(ref) {
    return ref[0] + ' ' + String(ref[1]);
}

function computeLayout(nodes, edges, opts) {
    const width = opts.width, height = opts.height;
    const iterations = opts.iterations, seed = opts.seed;
    const margin = opts.margin !== undefined ? opts.margin : 60;

    const refs = nodes.map(function (n) { return [n.type, String(n.id)]; });
    refs.sort(function (a, b) {
        if (a[0] !== b[0]) return a[0] < b[0] ? -1 : 1;
        if (a[1] !== b[1]) return a[1] < b[1] ? -1 : 1;
        return 0;
    });
    const n = refs.length;
    const pos = {};
    if (n === 0) return pos;
    if (n === 1) {
        pos[refKey(refs[0])] = [width / 2, height / 2];
        return pos;
    }

    const rand = makeRand(seed);
    const innerW = Math.max(1, width - 2 * margin);
    const innerH = Math.max(1, height - 2 * margin);
    for (const ref of refs) {
        pos[refKey(ref)] = [margin + rand() * innerW, margin + rand() * innerH];
    }

    // Springs: deduped unordered pairs, iterated in sorted order.
    const springSet = new Map();
    for (const e of edges) {
        const a = [e.source[0], String(e.source[1])];
        const b = [e.target[0], String(e.target[1])];
        const ka = refKey(a), kb = refKey(b);
        if (ka === kb || !(ka in pos) || !(kb in pos)) continue;
        const key = ka <= kb ? ka + '|' + kb : kb + '|' + ka;
        if (!springSet.has(key)) {
            springSet.set(key, ka <= kb ? [ka, kb] : [kb, ka]);
        }
    }
    const springs = Array.from(springSet.values());
    springs.sort(function (p, q) {
        if (p[0] !== q[0]) return p[0] < q[0] ? -1 : 1;
        if (p[1] !== q[1]) return p[1] < q[1] ? -1 : 1;
        return 0;
    });

    const keys = refs.map(refKey);
    const area = innerW * innerH;
    const k = Math.sqrt(area / n);
    let temp = Math.min(innerW, innerH) / 10;
    const cool = temp / (iterations + 1);

    for (let it = 0; it < iterations; it++) {
        const disp = {};
        for (const key of keys) disp[key] = [0, 0];

        for (let i = 0; i < n; i++) {
            const ki = keys[i];
            const xi = pos[ki][0], yi = pos[ki][1];
            for (let j = i + 1; j < n; j++) {
                const kj = keys[j];
                const dx = xi - pos[kj][0];
                const dy = yi - pos[kj][1];
                const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
                const force = (k * k) / dist;
                const fx = (dx / dist) * force, fy = (dy / dist) * force;
                disp[ki][0] += fx; disp[ki][1] += fy;
                disp[kj][0] -= fx; disp[kj][1] -= fy;
            }
        }

        for (const s of springs) {
            const a = s[0], b = s[1];
            const dx = pos[a][0] - pos[b][0];
            const dy = pos[a][1] - pos[b][1];
            const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
            const force = (dist * dist) / k;
            const fx = (dx / dist) * force, fy = (dy / dist) * force;
            disp[a][0] -= fx; disp[a][1] -= fy;
            disp[b][0] += fx; disp[b][1] += fy;
        }

        for (const key of keys) {
            const dx = disp[key][0], dy = disp[key][1];
            const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
            const step = Math.min(dist, temp);
            const x = pos[key][0] + (dx / dist) * step;
            const y = pos[key][1] + (dy / dist) * step;
            pos[key][0] = Math.min(width - margin, Math.max(margin, x));
            pos[key][1] = Math.min(height - margin, Math.max(margin, y));
        }
        temp = Math.max(0.01, temp - cool);
    }
    return pos;
}

// Node/CommonJS export for parity testing outside the webview.
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { computeLayout: computeLayout, makeRand: makeRand };
}

// ---------------------------------------------------------------------------
// Stage 3 + interaction: only inside the webview
// ---------------------------------------------------------------------------

if (typeof acquireVsCodeApi === 'function') {
    (function () {
        const vscode = acquireVsCodeApi();
        const SVG_NS = 'http://www.w3.org/2000/svg';
        const LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];
        const DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
        const OTHER = { light: '#7a7975', dark: '#8f8e89' };
        const WORLD_W = 900, WORLD_H = 600;

        const stage = document.getElementById('stage');
        const tip = document.getElementById('tip');
        const status = document.getElementById('status');
        const chkAnimate = document.getElementById('chk-animate');

        let model = null;      // {nodes:[{type,id,key,props,x,y,r,slot,el,label}], edges:[...], springs, degrees}
        let view = { x: 0, y: 0, w: WORLD_W, h: WORLD_H };
        let svg = null, gEdges = null, gNodes = null;
        let seed = 42, iterations = 170;
        let dragging = null;
        let energy = 0;
        let rafId = 0;

        function isDark() {
            const cls = document.body.className;
            if (cls.indexOf('vscode-high-contrast-light') >= 0) return false;
            return cls.indexOf('vscode-dark') >= 0 || cls.indexOf('vscode-high-contrast') >= 0;
        }
        function palette() { return isDark() ? DARK : LIGHT; }
        function otherColor() { return isDark() ? OTHER.dark : OTHER.light; }

        function el(name, attrs) {
            const e = document.createElementNS(SVG_NS, name);
            for (const k in attrs) e.setAttribute(k, attrs[k]);
            return e;
        }

        function buildModel(graph) {
            const degrees = {};
            for (const e of graph.edges) {
                const ks = e.source[0] + ':' + e.source[1];
                const kt = e.target[0] + ':' + e.target[1];
                degrees[ks] = (degrees[ks] || 0) + 1;
                degrees[kt] = (degrees[kt] || 0) + 1;
            }
            const types = Array.from(new Set(graph.nodes.map(function (n) { return n.type; }))).sort();
            const slots = {};
            types.forEach(function (t, i) { slots[t] = i; });

            const dvals = graph.nodes.map(function (n) { return degrees[n.type + ':' + n.id] || 0; });
            const dmin = dvals.length ? Math.min.apply(null, dvals) : 0;
            const dmax = dvals.length ? Math.max.apply(null, dvals) : 0;

            const layout = computeLayout(graph.nodes, graph.edges, {
                width: WORLD_W, height: WORLD_H, iterations: iterations, seed: seed
            });

            const nodes = graph.nodes.map(function (n) {
                const key = refKey([n.type, String(n.id)]);
                const deg = degrees[n.type + ':' + n.id] || 0;
                const p = layout[key] || [WORLD_W / 2, WORLD_H / 2];
                return {
                    type: n.type, id: n.id, key: key, props: n.properties,
                    x: p[0], y: p[1],
                    r: dmax > dmin ? 6 + 10 * (deg - dmin) / (dmax - dmin) : 9,
                    slot: slots[n.type],
                    label: n.properties.name || String(n.id)
                };
            });
            const byKey = {};
            nodes.forEach(function (n) { byKey[n.key] = n; });

            const edges = [];
            const seen = new Set();
            for (const e of graph.edges) {
                const a = byKey[refKey([e.source[0], String(e.source[1])])];
                const b = byKey[refKey([e.target[0], String(e.target[1])])];
                if (!a || !b) continue;
                edges.push({ source: a, target: b, relType: e.relType, props: e.properties });
                seen.add(a.key < b.key ? a.key + '|' + b.key : b.key + '|' + a.key);
            }
            return { nodes: nodes, edges: edges, byKey: byKey, types: types, slots: slots };
        }

        function render() {
            stage.textContent = '';
            svg = el('svg', { viewBox: view.x + ' ' + view.y + ' ' + view.w + ' ' + view.h });
            svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

            const defs = el('defs', {});
            const marker = el('marker', {
                id: 'arrow', viewBox: '0 0 10 10', refX: '10', refY: '5',
                markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse'
            });
            marker.appendChild(el('path', { d: 'M 0 0 L 10 5 L 0 10 z', 'class': 'edge-arrow' }));
            defs.appendChild(marker);
            svg.appendChild(defs);

            gEdges = el('g', { 'class': 'edges' });
            for (const e of model.edges) {
                e.el = el('line', { 'class': 'edge', 'marker-end': 'url(#arrow)' });
                gEdges.appendChild(e.el);
            }
            svg.appendChild(gEdges);

            gNodes = el('g', { 'class': 'nodes' });
            const pal = palette();
            for (const nd of model.nodes) {
                nd.el = el('circle', {
                    'class': 'node', r: nd.r.toFixed(1),
                    fill: nd.slot < pal.length ? pal[nd.slot] : otherColor()
                });
                nd.labelEl = el('text', { 'class': 'node-label', 'text-anchor': 'middle' });
                nd.labelEl.textContent = nd.label;
                attachNodeEvents(nd);
                gNodes.appendChild(nd.el);
                gNodes.appendChild(nd.labelEl);
            }
            svg.appendChild(gNodes);

            const legend = el('g', { 'class': 'legend' });
            let lx = 16;
            model.types.forEach(function (t) {
                const slot = model.slots[t];
                legend.appendChild(el('circle', {
                    cx: lx, cy: 20, r: 6,
                    fill: slot < pal.length ? pal[slot] : otherColor()
                }));
                const txt = el('text', { 'class': 'legend-label', x: lx + 12, y: 24 });
                txt.textContent = t;
                legend.appendChild(txt);
                lx += 24 + 7.2 * t.length;
            });
            svg.appendChild(legend);

            attachStageEvents();
            stage.appendChild(svg);
            tick();
            status.textContent = model.nodes.length + ' nodes / ' + model.edges.length + ' edges / seed ' + seed;
        }

        function tick() {
            for (const e of model.edges) {
                const dx = e.target.x - e.source.x, dy = e.target.y - e.source.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const rt = e.target.r + 3;
                e.el.setAttribute('x1', e.source.x.toFixed(1));
                e.el.setAttribute('y1', e.source.y.toFixed(1));
                e.el.setAttribute('x2', (e.target.x - dx / dist * rt).toFixed(1));
                e.el.setAttribute('y2', (e.target.y - dy / dist * rt).toFixed(1));
            }
            for (const nd of model.nodes) {
                nd.el.setAttribute('cx', nd.x.toFixed(1));
                nd.el.setAttribute('cy', nd.y.toFixed(1));
                nd.labelEl.setAttribute('x', nd.x.toFixed(1));
                nd.labelEl.setAttribute('y', (nd.y + nd.r + 13).toFixed(1));
            }
        }

        // Live physics: low-temperature FR steps while energy remains.
        function physicsStep() {
            const nodes = model.nodes;
            const n = nodes.length;
            if (n < 2) { energy = 0; return; }
            const k = Math.sqrt((WORLD_W - 120) * (WORLD_H - 120) / n);
            for (const nd of nodes) { nd.fx = 0; nd.fy = 0; }
            for (let i = 0; i < n; i++) {
                for (let j = i + 1; j < n; j++) {
                    const a = nodes[i], b = nodes[j];
                    const dx = a.x - b.x, dy = a.y - b.y;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
                    const f = (k * k) / dist;
                    a.fx += dx / dist * f; a.fy += dy / dist * f;
                    b.fx -= dx / dist * f; b.fy -= dy / dist * f;
                }
            }
            for (const e of model.edges) {
                const a = e.source, b = e.target;
                const dx = a.x - b.x, dy = a.y - b.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
                const f = (dist * dist) / k;
                a.fx -= dx / dist * f; a.fy -= dy / dist * f;
                b.fx += dx / dist * f; b.fy += dy / dist * f;
            }
            const temp = 6 * energy;
            for (const nd of nodes) {
                if (dragging && nd === dragging.node) continue;
                const dist = Math.sqrt(nd.fx * nd.fx + nd.fy * nd.fy) || 0.01;
                const step = Math.min(dist, temp);
                nd.x = Math.min(WORLD_W - 40, Math.max(40, nd.x + nd.fx / dist * step));
                nd.y = Math.min(WORLD_H - 40, Math.max(40, nd.y + nd.fy / dist * step));
            }
            if (!dragging) energy *= 0.94;
            if (energy < 0.02) energy = 0;
        }

        function loop() {
            rafId = 0;
            if (energy > 0 && chkAnimate.checked) {
                physicsStep();
                tick();
                rafId = requestAnimationFrame(loop);
            }
        }
        function wake(e0) {
            energy = Math.max(energy, e0);
            if (!rafId && chkAnimate.checked) rafId = requestAnimationFrame(loop);
        }

        function toWorld(clientX, clientY) {
            const r = svg.getBoundingClientRect();
            return [
                view.x + (clientX - r.left) / r.width * view.w,
                view.y + (clientY - r.top) / r.height * view.h
            ];
        }

        function attachNodeEvents(nd) {
            nd.el.addEventListener('pointerdown', function (ev) {
                ev.stopPropagation();
                dragging = { node: nd };
                nd.el.setPointerCapture(ev.pointerId);
                wake(1);
            });
            nd.el.addEventListener('pointermove', function (ev) {
                if (!dragging || dragging.node !== nd) {
                    const lines = ['<strong>' + escapeHtml(nd.type + ':' + nd.id) + '</strong>'];
                    for (const k in nd.props) lines.push(escapeHtml(k + ': ' + nd.props[k]));
                    tip.innerHTML = lines.join('<br>');
                    tip.style.display = 'block';
                    tip.style.left = (ev.clientX + 14) + 'px';
                    tip.style.top = (ev.clientY + 14) + 'px';
                    return;
                }
                const w = toWorld(ev.clientX, ev.clientY);
                nd.x = w[0]; nd.y = w[1];
                if (chkAnimate.checked) { wake(1); } else { tick(); }
            });
            nd.el.addEventListener('pointerup', function () { dragging = null; });
            nd.el.addEventListener('pointerleave', function () { tip.style.display = 'none'; });
        }

        function attachStageEvents() {
            let pan = null;
            svg.addEventListener('pointerdown', function (ev) {
                pan = { x: ev.clientX, y: ev.clientY };
                svg.setPointerCapture(ev.pointerId);
            });
            svg.addEventListener('pointermove', function (ev) {
                if (!pan) return;
                const r = svg.getBoundingClientRect();
                view.x -= (ev.clientX - pan.x) / r.width * view.w;
                view.y -= (ev.clientY - pan.y) / r.height * view.h;
                pan = { x: ev.clientX, y: ev.clientY };
                svg.setAttribute('viewBox', view.x + ' ' + view.y + ' ' + view.w + ' ' + view.h);
            });
            svg.addEventListener('pointerup', function () { pan = null; });
            svg.addEventListener('wheel', function (ev) {
                ev.preventDefault();
                const f = ev.deltaY < 0 ? 0.9 : 1.1;
                const w = toWorld(ev.clientX, ev.clientY);
                view.w *= f; view.h *= f;
                view.x = w[0] - (w[0] - view.x) * f;
                view.y = w[1] - (w[1] - view.y) * f;
                svg.setAttribute('viewBox', view.x + ' ' + view.y + ' ' + view.w + ' ' + view.h);
            }, { passive: false });
        }

        function escapeHtml(s) {
            return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function resetView() {
            view = { x: 0, y: 0, w: WORLD_W, h: WORLD_H };
            if (svg) svg.setAttribute('viewBox', '0 0 ' + WORLD_W + ' ' + WORLD_H);
        }

        let lastGraph = null;
        window.addEventListener('message', function (event) {
            const msg = event.data;
            if (msg.type === 'graph') {
                seed = msg.seed; iterations = msg.iterations;
                lastGraph = msg.graph;
                model = buildModel(msg.graph);
                resetView();
                render();
            } else if (msg.type === 'error') {
                stage.textContent = '';
                status.textContent = 'Parse error: ' + msg.message;
            }
        });

        document.getElementById('btn-reset').addEventListener('click', function () {
            if (!lastGraph) return;
            const fresh = computeLayout(lastGraph.nodes, lastGraph.edges, {
                width: WORLD_W, height: WORLD_H, iterations: iterations, seed: seed
            });
            for (const nd of model.nodes) {
                const p = fresh[nd.key];
                if (p) { nd.x = p[0]; nd.y = p[1]; }
            }
            energy = 0;
            tick();
        });
        document.getElementById('btn-fit').addEventListener('click', resetView);

        new MutationObserver(function () {
            if (model) render();
        }).observe(document.body, { attributes: true, attributeFilter: ['class'] });

        // Everything is wired up - ask the extension for the graph.
        vscode.postMessage({ type: 'ready' });
    })();
}
