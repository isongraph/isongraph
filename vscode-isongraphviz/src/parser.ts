/**
 * Minimal parser for the ISONGraph text format:
 *
 *   nodes.<type>
 *   <field> <field> ...
 *   <value> <value> ...
 *
 *   edges.<REL_TYPE>
 *   source target <field> ...
 *   :type:id :type:id <value> ...
 *
 * Values containing spaces, pipes, quotes, or newlines are double-quoted
 * with `\"` and `\n` escapes (the convention shared by every ISONGraph
 * implementation).
 */

export interface GraphNode {
    type: string;
    id: string;
    properties: Record<string, string>;
}

export interface GraphEdge {
    relType: string;
    source: [string, string];
    target: [string, string];
    properties: Record<string, string>;
}

export interface GraphData {
    name: string;
    nodes: GraphNode[];
    edges: GraphEdge[];
}

/** Split a row into fields, honoring double-quoted values with escapes. */
export function splitFields(line: string): string[] {
    const out: string[] = [];
    let i = 0;
    const n = line.length;
    while (i < n) {
        while (i < n && (line[i] === ' ' || line[i] === '\t')) i++;
        if (i >= n) break;
        if (line[i] === '"') {
            i++;
            let val = '';
            while (i < n) {
                const c = line[i];
                if (c === '\\' && i + 1 < n) {
                    const next = line[i + 1];
                    if (next === '"') { val += '"'; i += 2; continue; }
                    if (next === 'n') { val += '\n'; i += 2; continue; }
                    if (next === '\\') { val += '\\'; i += 2; continue; }
                }
                if (c === '"') { i++; break; }
                val += c;
                i++;
            }
            out.push(val);
        } else {
            let val = '';
            while (i < n && line[i] !== ' ' && line[i] !== '\t') {
                val += line[i];
                i++;
            }
            out.push(val);
        }
    }
    return out;
}

function parseRef(token: string): [string, string] | null {
    // :type:id
    if (!token.startsWith(':')) return null;
    const rest = token.slice(1);
    const sep = rest.indexOf(':');
    if (sep < 0) return null;
    return [rest.slice(0, sep), rest.slice(sep + 1)];
}

export function parseGraph(text: string, name: string): GraphData {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    const lines = text.split(/\r?\n/);

    let mode: 'nodes' | 'edges' | null = null;
    let blockType = '';
    let fields: string[] = [];

    for (const raw of lines) {
        const line = raw.trimEnd();
        if (line.trim() === '' || line.trimStart().startsWith('#')) {
            continue;
        }
        if (line.startsWith('nodes.')) {
            mode = 'nodes';
            blockType = line.slice('nodes.'.length).trim();
            fields = [];
            continue;
        }
        if (line.startsWith('edges.')) {
            mode = 'edges';
            blockType = line.slice('edges.'.length).trim();
            fields = [];
            continue;
        }
        if (!mode) continue;
        if (fields.length === 0) {
            fields = splitFields(line);
            continue;
        }
        const values = splitFields(line);
        if (values.length === 0) continue;

        if (mode === 'nodes') {
            const props: Record<string, string> = {};
            let id = '';
            fields.forEach((f, idx) => {
                const v = values[idx] ?? '';
                if (f === 'id') id = v;
                else props[f] = v;
            });
            nodes.push({ type: blockType, id, properties: props });
        } else {
            const props: Record<string, string> = {};
            let source: [string, string] | null = null;
            let target: [string, string] | null = null;
            fields.forEach((f, idx) => {
                const v = values[idx] ?? '';
                if (f === 'source') source = parseRef(v);
                else if (f === 'target') target = parseRef(v);
                else props[f] = v;
            });
            if (source && target) {
                edges.push({ relType: blockType, source, target, properties: props });
            }
        }
    }
    return { name, nodes, edges };
}
