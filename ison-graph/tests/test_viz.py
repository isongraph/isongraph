"""Tests for ison_graph.viz - layout determinism and SVG/HTML rendering."""

import xml.etree.ElementTree as ET

import pytest

from ison_graph import ISONGraph
from ison_graph.viz import (
    compute_layout,
    render_svg,
    render_html,
    save,
    LIGHT_PALETTE,
    OTHER_LIGHT,
    main,
)

SVG_NS = '{http://www.w3.org/2000/svg}'


def social_graph():
    g = ISONGraph('social')
    g.add_node('person', 1, name='Alice', age=30)
    g.add_node('person', 2, name='Bob', age=25)
    g.add_node('person', 3, name='Carol', age=28)
    g.add_node('company', 100, name='TechCorp')
    g.add_edge('KNOWS', ('person', 1), ('person', 2), since=2020)
    g.add_edge('KNOWS', ('person', 2), ('person', 3), since=2021)
    g.add_edge('WORKS_AT', ('person', 1), ('company', 100), role='Engineer')
    return g


class TestLayout:
    def test_deterministic_same_seed(self):
        g = social_graph()
        assert compute_layout(g, seed=42) == compute_layout(g, seed=42)

    def test_different_seed_differs(self):
        g = social_graph()
        assert compute_layout(g, seed=1) != compute_layout(g, seed=2)

    def test_positions_within_bounds(self):
        g = social_graph()
        layout = compute_layout(g, width=900, height=600, margin=60)
        for x, y in layout.values():
            assert 60 <= x <= 840
            assert 60 <= y <= 540

    def test_all_nodes_placed(self):
        g = social_graph()
        layout = compute_layout(g)
        assert set(layout) == {n.ref for n in g.nodes()}

    def test_empty_graph(self):
        assert compute_layout(ISONGraph('empty')) == {}

    def test_single_node_centered(self):
        g = ISONGraph('one')
        g.add_node('thing', 1)
        assert compute_layout(g, width=900, height=600) == {('thing', 1): (450.0, 300.0)}

    def test_connected_nodes_closer_than_average(self):
        g = ISONGraph('clusters')
        for i in range(1, 7):
            g.add_node('n', i)
        g.add_edge('LINK', ('n', 1), ('n', 2))
        layout = compute_layout(g, seed=7)
        import math
        def d(a, b):
            (x1, y1), (x2, y2) = layout[('n', a)], layout[('n', b)]
            return math.hypot(x1 - x2, y1 - y2)
        pairs = [(a, b) for a in range(1, 7) for b in range(a + 1, 7)]
        avg = sum(d(a, b) for a, b in pairs) / len(pairs)
        assert d(1, 2) < avg


class TestSVG:
    def test_well_formed_and_complete(self):
        g = social_graph()
        root = ET.fromstring(render_svg(g))
        circles = root.findall(f'.//{SVG_NS}g[@class="nodes"]/{SVG_NS}circle')
        lines = root.findall(f'.//{SVG_NS}line')
        assert len(circles) == 4
        assert len(lines) == 3

    def test_labels_and_legend(self):
        g = social_graph()
        svg = render_svg(g)
        for name in ('Alice', 'Bob', 'Carol', 'TechCorp'):
            assert name in svg
        for t in ('person', 'company'):
            assert t in svg

    def test_types_get_fixed_sorted_slots(self):
        g = social_graph()
        svg = render_svg(g)
        # Sorted types: company -> slot 0, person -> slot 1.
        assert LIGHT_PALETTE[0] in svg and LIGHT_PALETTE[1] in svg

    def test_more_than_eight_types_fold_to_other(self):
        g = ISONGraph('many')
        for i in range(10):
            g.add_node(f'type{i:02d}', 1, name=f'n{i}')
        assert OTHER_LIGHT in render_svg(g)

    def test_undirected_draws_each_edge_once_no_arrows(self):
        g = ISONGraph('u', directed=False)
        g.add_node('n', 1)
        g.add_node('n', 2)
        g.add_edge('LINK', ('n', 1), ('n', 2))
        svg = render_svg(g)
        root = ET.fromstring(svg)
        assert len(root.findall(f'.//{SVG_NS}line')) == 1
        assert 'marker-end' not in svg

    def test_directed_has_arrow_marker(self):
        assert 'marker-end="url(#arrow)"' in render_svg(social_graph())

    def test_edge_labels_and_title(self):
        svg = render_svg(social_graph(), edge_labels=True, title='My Graph')
        assert 'KNOWS' in svg and 'My Graph' in svg

    def test_escapes_markup_in_values(self):
        g = ISONGraph('x')
        g.add_node('a<b', 1, name='Bad <script> & "quotes"')
        svg = render_svg(g)
        assert '<script>' not in svg
        ET.fromstring(svg)  # must stay well-formed

    def test_empty_graph_renders(self):
        ET.fromstring(render_svg(ISONGraph('empty')))


class TestHTML:
    def test_self_contained_interactive(self):
        html = render_html(social_graph())
        assert '<script>' in html and 'data-props' in html
        assert 'prefers-color-scheme: dark' in html
        assert 'http://' not in html.replace('http://www.w3.org/2000/svg', '')
        assert 'https://' not in html

    def test_layout_shared_between_svg_and_html(self):
        g = social_graph()
        layout = compute_layout(g, seed=9)
        svg = render_svg(g, layout=layout)
        html = render_html(g, layout=layout)
        x, y = layout[('person', 1)]
        coord = f'cx="{x:.1f}" cy="{y:.1f}"'
        assert coord in svg and coord in html


class TestSaveAndCLI:
    def test_save_svg_and_html(self, tmp_path):
        g = social_graph()
        save(g, tmp_path / 'g.svg')
        save(g, tmp_path / 'g.html')
        assert (tmp_path / 'g.svg').read_text(encoding='utf-8').startswith('<svg')
        assert (tmp_path / 'g.html').read_text(encoding='utf-8').startswith('<!DOCTYPE html>')

    def test_save_rejects_unknown_extension(self, tmp_path):
        with pytest.raises(ValueError):
            save(social_graph(), tmp_path / 'g.png')

    def test_cli_roundtrip(self, tmp_path):
        g = social_graph()
        src = tmp_path / 'g.ison'
        g.save(src)
        out = tmp_path / 'g.svg'
        assert main([str(src), '-o', str(out), '--seed', '5']) == 0
        ET.fromstring(out.read_text(encoding='utf-8'))
