/** Tests for viz - layout determinism, Python parity, SVG/HTML rendering. */

import { describe, it, expect } from 'vitest';
import { ISONGraph } from './index';
import {
  computeLayout,
  renderSvg,
  renderHtml,
  layoutKey,
  LIGHT_PALETTE,
  OTHER_LIGHT,
} from './viz';

function socialGraph(): ISONGraph {
  const g = new ISONGraph('social');
  g.addNode('person', 1, { name: 'Alice', age: 30 });
  g.addNode('person', 2, { name: 'Bob', age: 25 });
  g.addNode('person', 3, { name: 'Carol', age: 28 });
  g.addNode('company', 100, { name: 'TechCorp' });
  g.addEdge('KNOWS', ['person', 1], ['person', 2], { since: 2020 });
  g.addEdge('KNOWS', ['person', 2], ['person', 3], { since: 2021 });
  g.addEdge('WORKS_AT', ['person', 1], ['company', 100], { role: 'Engineer' });
  return g;
}

// Exact coordinates produced by Python ison_graph.viz.compute_layout for the
// identical graph with default settings (900x600, 170 iterations, seed 42).
// Bit-for-bit parity is the contract; any drift here is a regression.
const PYTHON_PARITY_FIXTURE: Record<string, [number, number]> = {
  'company acme': [60, 60],
  'person alice': [293.3277424315421, 60],
  'person bob': [377.3280362355162, 354.58580004430877],
  'person carol': [601.3804168633184, 540],
  'project p1': [840, 540],
};

describe('computeLayout', () => {
  it('is deterministic for the same seed', () => {
    const g = socialGraph();
    expect(computeLayout(g, { seed: 42 })).toEqual(computeLayout(g, { seed: 42 }));
  });

  it('differs across seeds', () => {
    const g = socialGraph();
    expect(computeLayout(g, { seed: 1 })).not.toEqual(computeLayout(g, { seed: 2 }));
  });

  it('keeps positions within bounds', () => {
    const layout = computeLayout(socialGraph(), { width: 900, height: 600, margin: 60 });
    for (const [x, y] of layout.values()) {
      expect(x).toBeGreaterThanOrEqual(60);
      expect(x).toBeLessThanOrEqual(840);
      expect(y).toBeGreaterThanOrEqual(60);
      expect(y).toBeLessThanOrEqual(540);
    }
  });

  it('places every node', () => {
    const g = socialGraph();
    const layout = computeLayout(g);
    const expected = new Set<string>();
    for (const node of g.nodes()) expected.add(layoutKey(node.ref));
    expect(new Set(layout.keys())).toEqual(expected);
  });

  it('handles the empty graph', () => {
    expect(computeLayout(new ISONGraph('empty')).size).toBe(0);
  });

  it('centers a single node', () => {
    const g = new ISONGraph('one');
    g.addNode('thing', 1, {});
    expect(computeLayout(g, { width: 900, height: 600 }).get('thing 1')).toEqual([450, 300]);
  });

  it('matches the Python implementation bit-for-bit', () => {
    const g = new ISONGraph('parity');
    g.addNode('person', 'alice', { name: 'Alice', age: 30 });
    g.addNode('person', 'bob', { name: 'Bob', age: 25 });
    g.addNode('person', 'carol', { name: 'Carol', age: 35 });
    g.addNode('company', 'acme', { name: 'Acme' });
    g.addNode('project', 'p1', { name: 'Alpha' });
    g.addEdge('KNOWS', ['person', 'alice'], ['person', 'bob']);
    g.addEdge('KNOWS', ['person', 'bob'], ['person', 'carol']);
    g.addEdge('WORKS_AT', ['person', 'alice'], ['company', 'acme']);
    g.addEdge('WORKS_ON', ['person', 'carol'], ['project', 'p1']);

    const layout = computeLayout(g);
    expect(layout.size).toBe(Object.keys(PYTHON_PARITY_FIXTURE).length);
    for (const [key, [px, py]] of Object.entries(PYTHON_PARITY_FIXTURE)) {
      const p = layout.get(key);
      expect(p, `missing ${key}`).toBeDefined();
      expect(p![0]).toBe(px);
      expect(p![1]).toBe(py);
    }
  });
});

describe('renderSvg', () => {
  it('renders all nodes, edges, labels, and legend', () => {
    const svg = renderSvg(socialGraph());
    expect((svg.match(/<circle class="node"/g) ?? []).length).toBe(4);
    expect((svg.match(/<line class="edge"/g) ?? []).length).toBe(3);
    for (const name of ['Alice', 'Bob', 'Carol', 'TechCorp', 'person', 'company']) {
      expect(svg).toContain(name);
    }
  });

  it('assigns fixed sorted palette slots', () => {
    const svg = renderSvg(socialGraph());
    // Sorted types: company -> slot 0, person -> slot 1.
    expect(svg).toContain(LIGHT_PALETTE[0]);
    expect(svg).toContain(LIGHT_PALETTE[1]);
  });

  it('folds more than eight types to the neutral color', () => {
    const g = new ISONGraph('many');
    for (let i = 0; i < 10; i++) {
      g.addNode(`type${String(i).padStart(2, '0')}`, 1, { name: `n${i}` });
    }
    expect(renderSvg(g)).toContain(OTHER_LIGHT);
  });

  it('draws undirected edges once without arrows', () => {
    const g = new ISONGraph('u', false);
    g.addNode('n', 1, {});
    g.addNode('n', 2, {});
    g.addEdge('LINK', ['n', 1], ['n', 2]);
    const svg = renderSvg(g);
    expect((svg.match(/<line class="edge"/g) ?? []).length).toBe(1);
    expect(svg).not.toContain('marker-end');
  });

  it('adds arrow markers for directed graphs', () => {
    expect(renderSvg(socialGraph())).toContain('marker-end="url(#arrow)"');
  });

  it('renders edge labels and a title on request', () => {
    const svg = renderSvg(socialGraph(), { edgeLabels: true, title: 'My Graph' });
    expect(svg).toContain('KNOWS');
    expect(svg).toContain('My Graph');
  });

  it('escapes markup in values', () => {
    const g = new ISONGraph('x');
    g.addNode('a<b', 1, { name: 'Bad <script> & "quotes"' });
    const svg = renderSvg(g);
    expect(svg).not.toContain('<script>');
  });

  it('renders the empty graph', () => {
    expect(renderSvg(new ISONGraph('empty'))).toContain('</svg>');
  });
});

describe('renderHtml', () => {
  it('is self-contained and interactive', () => {
    const html = renderHtml(socialGraph());
    expect(html).toContain('<script>');
    expect(html).toContain('data-props');
    expect(html).toContain('prefers-color-scheme: dark');
    expect(html.replace('http://www.w3.org/2000/svg', '')).not.toContain('http://');
    expect(html).not.toContain('https://');
  });

  it('shares layout coordinates with renderSvg', () => {
    const g = socialGraph();
    const layout = computeLayout(g, { seed: 9 });
    const svg = renderSvg(g, { layout });
    const html = renderHtml(g, { layout });
    const p = layout.get('person 1')!;
    const coord = `cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}"`;
    expect(svg).toContain(coord);
    expect(html).toContain(coord);
  });
});
