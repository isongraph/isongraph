"""
ISONGraph Visualization - deterministic layout and SVG/HTML rendering.

Three-stage pipeline:

1. Graph data - an :class:`~ison_graph.ISONGraph` (or a ``.ison`` file).
2. Layout     - :func:`compute_layout` runs a seeded, deterministic
   force-directed simulation and assigns every node an ``(x, y)`` coordinate.
3. Rendering  - :func:`render_svg` / :func:`render_html` turn those
   coordinates into a standalone SVG image or a self-contained interactive
   HTML page (hover tooltips, pan and zoom). No external dependencies.

The same seed always produces the same layout, so a server and a client
rendering the same graph get identical geometry.

Usage:
    from ison_graph import ISONGraph
    from ison_graph.viz import compute_layout, render_svg, render_html

    graph = ISONGraph.load("social.ison")
    layout = compute_layout(graph, seed=42)
    svg = render_svg(graph, layout)

Command line:
    python -m ison_graph.viz social.ison -o graph.svg
    python -m ison_graph.viz social.ison -o graph.html
"""

import math
import json
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape, quoteattr

__all__ = [
    'compute_layout',
    'render_svg',
    'render_html',
    'save',
    'LIGHT_PALETTE',
    'DARK_PALETTE',
]

NodeRef = Tuple[str, Any]
Point = Tuple[float, float]
Layout = Dict[NodeRef, Point]

# Categorical palette (validated: CVD-safe adjacent pairs, both modes).
# Types are assigned slots in sorted order; past 8 types fall back to OTHER.
LIGHT_PALETTE = [
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
]
DARK_PALETTE = [
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#008300", "#9085e9", "#e66767",
]
OTHER_LIGHT = "#7a7975"
OTHER_DARK = "#8f8e89"

_SURFACE_LIGHT = "#fcfcfb"
_SURFACE_DARK = "#1a1a19"
_INK_PRIMARY = "#0b0b0b"
_INK_SECONDARY = "#52514e"
_INK_PRIMARY_DARK = "#ffffff"
_INK_SECONDARY_DARK = "#c3c2b7"
_EDGE_LIGHT = "#d7d6d2"
_EDGE_DARK = "#3a3936"


# =============================================================================
# Stage 2: Layout
# =============================================================================

def compute_layout(
    graph,
    width: int = 900,
    height: int = 600,
    iterations: int = 170,
    seed: int = 42,
    margin: int = 60,
    radii: Optional[Dict[NodeRef, float]] = None,
    spacing: float = 1.0,
) -> Layout:
    """
    Compute a deterministic force-directed layout (Fruchterman-Reingold).

    Repulsion between every node pair, spring attraction along edges, and a
    linear cooling schedule. The ``seed`` fixes the initial positions, so the
    same graph, size, and seed always yield the same coordinates - across
    processes and across language ports: the PRNG is a portable 32-bit LCG
    (state * 1664525 + 1013904223 mod 2^32) so any implementation that
    mirrors it reproduces the exact geometry.

    When ``radii`` maps node refs to visual radii, a deterministic collision
    pass runs after the simulation, pushing every pair apart until their
    centers are at least ``(r_a + r_b) * spacing`` apart. Omitting ``radii``
    leaves the output byte-identical to earlier releases.

    Returns a dict mapping every node ref ``(type, id)`` to an ``(x, y)``
    position inside the ``width`` x ``height`` canvas (minus ``margin``).
    """
    refs = sorted((n.ref for n in graph.nodes()), key=lambda r: (r[0], str(r[1])))
    n = len(refs)
    if n == 0:
        return {}
    if n == 1:
        return {refs[0]: (width / 2.0, height / 2.0)}

    state = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 4294967296.0

    inner_w = max(1.0, width - 2.0 * margin)
    inner_h = max(1.0, height - 2.0 * margin)
    pos: Dict[NodeRef, List[float]] = {
        ref: [margin + rand() * inner_w, margin + rand() * inner_h]
        for ref in refs
    }

    # Springs: unordered node pairs connected by at least one edge.
    # Deduped via a set but iterated in sorted order - float accumulation
    # order must be deterministic for cross-process/cross-language parity.
    spring_set = set()
    for edge in graph.edges():
        if edge.source == edge.target:
            continue
        a, b = edge.source, edge.target
        key = (a, b) if (a[0], str(a[1])) <= (b[0], str(b[1])) else (b, a)
        if key[0] in pos and key[1] in pos:
            spring_set.add(key)
    springs = sorted(spring_set, key=lambda p: (p[0][0], str(p[0][1]), p[1][0], str(p[1][1])))

    area = inner_w * inner_h
    k = math.sqrt(area / n)
    temp = min(inner_w, inner_h) / 10.0
    cool = temp / (iterations + 1)

    for _ in range(iterations):
        disp = {ref: [0.0, 0.0] for ref in refs}

        # Repulsion: every pair pushes apart with k^2 / d.
        for i in range(n):
            ri = refs[i]
            xi, yi = pos[ri]
            for j in range(i + 1, n):
                rj = refs[j]
                dx = xi - pos[rj][0]
                dy = yi - pos[rj][1]
                dist = math.sqrt(dx * dx + dy * dy) or 0.01
                force = (k * k) / dist
                fx, fy = (dx / dist) * force, (dy / dist) * force
                disp[ri][0] += fx
                disp[ri][1] += fy
                disp[rj][0] -= fx
                disp[rj][1] -= fy

        # Attraction: connected pairs pull together with d^2 / k.
        for a, b in springs:
            dx = pos[a][0] - pos[b][0]
            dy = pos[a][1] - pos[b][1]
            dist = math.sqrt(dx * dx + dy * dy) or 0.01
            force = (dist * dist) / k
            fx, fy = (dx / dist) * force, (dy / dist) * force
            disp[a][0] -= fx
            disp[a][1] -= fy
            disp[b][0] += fx
            disp[b][1] += fy

        # Move, capped by temperature; clamp into the frame.
        for ref in refs:
            dx, dy = disp[ref]
            dist = math.sqrt(dx * dx + dy * dy) or 0.01
            step = min(dist, temp)
            x = pos[ref][0] + (dx / dist) * step
            y = pos[ref][1] + (dy / dist) * step
            pos[ref][0] = min(width - margin, max(margin, x))
            pos[ref][1] = min(height - margin, max(margin, y))

        temp = max(0.01, temp - cool)

    # Deterministic collision pass: separate every pair to at least
    # (r_a + r_b) * spacing. Sorted pair order keeps this reproducible
    # across processes and language ports.
    if radii:
        rad = {ref: float(radii.get(ref, 0.0)) for ref in refs}
        for _ in range(50):
            moved = False
            for i in range(n):
                ra = refs[i]
                for j in range(i + 1, n):
                    rb = refs[j]
                    min_d = (rad[ra] + rad[rb]) * spacing
                    if min_d <= 0.0:
                        continue
                    dx = pos[rb][0] - pos[ra][0]
                    dy = pos[rb][1] - pos[ra][1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist >= min_d:
                        continue
                    if dist < 1e-9:
                        ux, uy = 1.0, 0.0
                    else:
                        ux, uy = dx / dist, dy / dist
                    push = (min_d - dist) / 2.0
                    pos[ra][0] = min(width - margin, max(margin, pos[ra][0] - ux * push))
                    pos[ra][1] = min(height - margin, max(margin, pos[ra][1] - uy * push))
                    pos[rb][0] = min(width - margin, max(margin, pos[rb][0] + ux * push))
                    pos[rb][1] = min(height - margin, max(margin, pos[rb][1] + uy * push))
                    moved = True
            if not moved:
                break

    return {ref: (p[0], p[1]) for ref, p in pos.items()}


# =============================================================================
# Stage 3: Rendering
# =============================================================================

def _type_slots(graph) -> Dict[str, int]:
    """Assign each node type a palette slot in sorted order (fixed, never cycled)."""
    return {t: i for i, t in enumerate(sorted(graph.node_types()))}


def _fill_for(slot: int, palette: List[str], other: str) -> str:
    return palette[slot] if slot < len(palette) else other


def _degrees(graph) -> Dict[NodeRef, int]:
    return {n.ref: graph.degree(n.ref) for n in graph.nodes()}


def _radius(degree: int, dmin: int, dmax: int) -> float:
    if dmax <= dmin:
        return 9.0
    return 6.0 + 10.0 * (degree - dmin) / (dmax - dmin)


def _node_label(node, label_property: Optional[str]) -> str:
    if label_property and label_property in node.properties:
        return str(node.properties[label_property])
    if 'name' in node.properties:
        return str(node.properties['name'])
    return str(node.id)


def _visible_edges(graph):
    """Edges to draw: for undirected graphs, skip the auto-added reverse twin."""
    directed = getattr(graph, 'directed', True)
    seen = set()
    for edge in graph.edges():
        if not directed:
            a, b = edge.source, edge.target
            key = (edge.rel_type,) + ((a, b) if (a[0], str(a[1])) <= (b[0], str(b[1])) else (b, a))
            if key in seen:
                continue
            seen.add(key)
        yield edge


def _build_svg(
    graph,
    layout: Layout,
    width: int,
    height: int,
    title: Optional[str],
    label_property: Optional[str],
    edge_labels: bool,
    classed: bool,
) -> str:
    """
    Build the SVG body. With ``classed=True`` marks carry CSS classes and no
    inline colors (for themable HTML); otherwise light-mode colors are inlined
    so the file stands alone.
    """
    slots = _type_slots(graph)
    degrees = _degrees(graph)
    dmin = min(degrees.values(), default=0)
    dmax = max(degrees.values(), default=0)
    directed = getattr(graph, 'directed', True)

    parts: List[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label={quoteattr(title or getattr(graph, "name", "graph"))}>'
    )
    if not classed:
        parts.append(f'<rect width="{width}" height="{height}" fill="{_SURFACE_LIGHT}"/>')
    else:
        parts.append(f'<rect class="surface" width="{width}" height="{height}"/>')

    if directed:
        arrow_fill = '' if classed else f' fill="{_EDGE_LIGHT}"'
        parts.append(
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" class="edge-arrow"{arrow_fill}/></marker></defs>'
        )

    # Edges under nodes.
    parts.append('<g class="edges">')
    for edge in _visible_edges(graph):
        if edge.source not in layout or edge.target not in layout:
            continue
        x1, y1 = layout[edge.source]
        x2, y2 = layout[edge.target]
        # Shorten toward the target so arrowheads sit on the node rim.
        if directed:
            r2 = _radius(degrees.get(edge.target, 0), dmin, dmax) + 3.0
            dist = math.hypot(x2 - x1, y2 - y1) or 1.0
            x2 -= (x2 - x1) / dist * r2
            y2 -= (y2 - y1) / dist * r2
        stroke = '' if classed else f' stroke="{_EDGE_LIGHT}"'
        marker = ' marker-end="url(#arrow)"' if directed else ''
        parts.append(
            f'<line class="edge" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
            f'{stroke} stroke-width="2"{marker}/>'
        )
        if edge_labels:
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            fill = '' if classed else f' fill="{_INK_SECONDARY}"'
            parts.append(
                f'<text class="edge-label" x="{mx:.1f}" y="{my - 4:.1f}" '
                f'font-size="10" text-anchor="middle"{fill}>{escape(edge.rel_type)}</text>'
            )
    parts.append('</g>')

    # Nodes with a 2px surface ring, labels in ink (never the series color).
    parts.append('<g class="nodes">')
    for node in graph.nodes():
        ref = node.ref
        if ref not in layout:
            continue
        x, y = layout[ref]
        slot = slots[node.type]
        r = _radius(degrees.get(ref, 0), dmin, dmax)
        label = _node_label(node, label_property)
        data = ''
        if classed:
            props = json.dumps(node.properties, default=str)
            data = f' data-ref={quoteattr(f"{node.type}:{node.id}")} data-props={quoteattr(props)}'
        if classed:
            paint = f' class="node t{slot}"'
        else:
            fill = _fill_for(slot, LIGHT_PALETTE, OTHER_LIGHT)
            paint = f' class="node" fill="{fill}" stroke="{_SURFACE_LIGHT}"'
        parts.append(f'<circle{paint} cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" stroke-width="2"{data}/>')
        fill = '' if classed else f' fill="{_INK_SECONDARY}"'
        parts.append(
            f'<text class="node-label" x="{x:.1f}" y="{y + r + 13:.1f}" font-size="12" '
            f'font-family="system-ui, sans-serif" text-anchor="middle"{fill}>{escape(label)}</text>'
        )
    parts.append('</g>')

    # Legend: one chip per type, primary ink text.
    parts.append('<g class="legend">')
    lx = 16.0
    ly = 24.0
    for t in sorted(slots):
        slot = slots[t]
        if classed:
            chip = f'<circle class="t{slot}" cx="{lx:.1f}" cy="{ly - 4:.1f}" r="6"/>'
        else:
            chip = (
                f'<circle cx="{lx:.1f}" cy="{ly - 4:.1f}" r="6" '
                f'fill="{_fill_for(slot, LIGHT_PALETTE, OTHER_LIGHT)}"/>'
            )
        fill = '' if classed else f' fill="{_INK_PRIMARY}"'
        parts.append(chip)
        parts.append(
            f'<text class="legend-label" x="{lx + 12:.1f}" y="{ly:.1f}" font-size="12" '
            f'font-family="system-ui, sans-serif"{fill}>{escape(t)}</text>'
        )
        lx += 24 + 7.2 * len(t)
    parts.append('</g>')

    if title:
        fill = '' if classed else f' fill="{_INK_PRIMARY}"'
        parts.append(
            f'<text class="title" x="{width / 2:.1f}" y="{height - 14:.1f}" font-size="13" '
            f'font-family="system-ui, sans-serif" text-anchor="middle"{fill}>{escape(title)}</text>'
        )

    parts.append('</svg>')
    return '\n'.join(parts)


def render_svg(
    graph,
    layout: Optional[Layout] = None,
    width: int = 900,
    height: int = 600,
    title: Optional[str] = None,
    label_property: Optional[str] = None,
    edge_labels: bool = False,
    seed: int = 42,
) -> str:
    """
    Render the graph to a standalone SVG string (light theme, inline colors).

    If ``layout`` is omitted it is computed with :func:`compute_layout` using
    ``width``, ``height``, and ``seed``.
    """
    if layout is None:
        layout = compute_layout(graph, width=width, height=height, seed=seed)
    return _build_svg(graph, layout, width, height, title, label_property, edge_labels, classed=False)


def _theme_css(palette: List[str], other: str, surface: str,
               ink1: str, ink2: str, edge: str) -> str:
    rules = [f'.surface{{fill:{surface}}}']
    rules.append(f'.edge{{stroke:{edge}}} .edge-arrow{{fill:{edge}}}')
    rules.append(f'.node{{stroke:{surface}}}')
    rules.append(f'.node-label,.edge-label{{fill:{ink2}}}')
    rules.append(f'.legend-label,.title{{fill:{ink1}}}')
    for i, c in enumerate(palette):
        rules.append(f'.t{i}{{fill:{c}}}')
    rules.append(f'.t8,.t9,.t10,.t11,.t12,.t13,.t14,.t15{{fill:{other}}}')
    return '\n'.join(rules)


def render_html(
    graph,
    layout: Optional[Layout] = None,
    width: int = 900,
    height: int = 600,
    title: Optional[str] = None,
    label_property: Optional[str] = None,
    edge_labels: bool = False,
    seed: int = 42,
) -> str:
    """
    Render the graph to a self-contained interactive HTML page.

    Light and dark themes (follows the OS setting), hover tooltips showing
    node properties, and wheel-zoom / drag-pan. No external resources.
    """
    if layout is None:
        layout = compute_layout(graph, width=width, height=height, seed=seed)
    name = title or getattr(graph, 'name', 'graph')
    svg = _build_svg(graph, layout, width, height, title, label_property, edge_labels, classed=True)

    light = _theme_css(LIGHT_PALETTE, OTHER_LIGHT, _SURFACE_LIGHT,
                       _INK_PRIMARY, _INK_SECONDARY, _EDGE_LIGHT)
    dark = _theme_css(DARK_PALETTE, OTHER_DARK, _SURFACE_DARK,
                      _INK_PRIMARY_DARK, _INK_SECONDARY_DARK, _EDGE_DARK)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(name)}</title>
<style>
html,body{{margin:0;height:100%;background:{_SURFACE_LIGHT}}}
body{{display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif}}
#wrap{{position:relative;max-width:100%;overflow:hidden}}
svg{{display:block;max-width:100%;height:auto;cursor:grab}}
svg:active{{cursor:grabbing}}
.node{{stroke-width:2px;cursor:pointer}}
#tip{{position:absolute;display:none;pointer-events:none;background:{_INK_PRIMARY};color:{_SURFACE_LIGHT};
padding:6px 10px;border-radius:6px;font-size:12px;max-width:280px;line-height:1.5;z-index:2}}
{light}
@media (prefers-color-scheme: dark){{
html,body{{background:{_SURFACE_DARK}}}
#tip{{background:{_INK_PRIMARY_DARK};color:{_SURFACE_DARK}}}
{dark}
}}
</style>
</head>
<body>
<div id="wrap">
{svg}
<div id="tip"></div>
</div>
<script>
(function () {{
  var svg = document.querySelector('svg');
  var tip = document.getElementById('tip');
  var vb = svg.viewBox.baseVal;
  var view = {{x: vb.x, y: vb.y, w: vb.width, h: vb.height}};

  function apply() {{
    svg.setAttribute('viewBox', view.x + ' ' + view.y + ' ' + view.w + ' ' + view.h);
  }}

  svg.addEventListener('wheel', function (e) {{
    e.preventDefault();
    var factor = e.deltaY < 0 ? 0.9 : 1.1;
    var rect = svg.getBoundingClientRect();
    var mx = view.x + (e.clientX - rect.left) / rect.width * view.w;
    var my = view.y + (e.clientY - rect.top) / rect.height * view.h;
    view.w *= factor; view.h *= factor;
    view.x = mx - (mx - view.x) * factor;
    view.y = my - (my - view.y) * factor;
    apply();
  }}, {{passive: false}});

  var drag = null;
  svg.addEventListener('pointerdown', function (e) {{
    drag = {{x: e.clientX, y: e.clientY}};
    svg.setPointerCapture(e.pointerId);
  }});
  svg.addEventListener('pointermove', function (e) {{
    if (!drag) return;
    var rect = svg.getBoundingClientRect();
    view.x -= (e.clientX - drag.x) / rect.width * view.w;
    view.y -= (e.clientY - drag.y) / rect.height * view.h;
    drag = {{x: e.clientX, y: e.clientY}};
    apply();
  }});
  svg.addEventListener('pointerup', function () {{ drag = null; }});

  document.querySelectorAll('.node').forEach(function (c) {{
    c.addEventListener('mouseenter', function (e) {{
      var props = JSON.parse(c.getAttribute('data-props') || '{{}}');
      var lines = ['<strong>' + c.getAttribute('data-ref') + '</strong>'];
      Object.keys(props).forEach(function (k) {{
        lines.push(k + ': ' + String(props[k]));
      }});
      tip.innerHTML = lines.join('<br>');
      tip.style.display = 'block';
    }});
    c.addEventListener('mousemove', function (e) {{
      var wrap = document.getElementById('wrap').getBoundingClientRect();
      tip.style.left = (e.clientX - wrap.left + 14) + 'px';
      tip.style.top = (e.clientY - wrap.top + 14) + 'px';
    }});
    c.addEventListener('mouseleave', function () {{ tip.style.display = 'none'; }});
  }});
}})();
</script>
</body>
</html>
"""


def save(graph, path, **kwargs) -> None:
    """Render to ``path``; format chosen by extension (.svg or .html/.htm)."""
    p = str(path)
    if p.lower().endswith(('.html', '.htm')):
        content = render_html(graph, **kwargs)
    elif p.lower().endswith('.svg'):
        content = render_svg(graph, **kwargs)
    else:
        raise ValueError(f"Unsupported output extension: {p} (use .svg or .html)")
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)


# =============================================================================
# CLI: python -m ison_graph.viz graph.ison -o out.svg
# =============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    from ison_graph import ISONGraph

    parser = argparse.ArgumentParser(
        prog='python -m ison_graph.viz',
        description='Render an ISONGraph .ison file to SVG or interactive HTML.',
    )
    parser.add_argument('input', help='Path to a .ison graph file')
    parser.add_argument('-o', '--output', required=True, help='Output path (.svg or .html)')
    parser.add_argument('--width', type=int, default=900)
    parser.add_argument('--height', type=int, default=600)
    parser.add_argument('--iterations', type=int, default=170)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--label', help='Node property to use as the label (default: name, else id)')
    parser.add_argument('--edge-labels', action='store_true', help='Draw relationship types on edges')
    parser.add_argument('--title', help='Caption drawn under the graph')
    args = parser.parse_args(argv)

    graph = ISONGraph.load(args.input)
    layout = compute_layout(
        graph, width=args.width, height=args.height,
        iterations=args.iterations, seed=args.seed,
    )
    save(
        graph, args.output, layout=layout, width=args.width, height=args.height,
        title=args.title, label_property=args.label, edge_labels=args.edge_labels,
    )
    print(f"Wrote {args.output} ({graph.node_count()} nodes, {graph.edge_count()} edges)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
