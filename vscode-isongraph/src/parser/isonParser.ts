/**
 * ISON Parser for VSCode extension
 *
 * Parses ISON and ISONL format files into GraphData structure.
 */

import { GraphData, GraphNode, GraphEdge } from '../types';

/**
 * Parse ISON format string into GraphData
 */
export function parseISON(content: string): GraphData {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    let graphName = 'graph';

    const lines = content.split('\n');
    let currentSection: 'nodes' | 'edges' | null = null;
    let currentType = '';
    let headers: string[] = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Skip empty lines and comments
        if (line === '' || line.startsWith('#')) {
            continue;
        }

        // Check for section header
        if (line.startsWith('nodes.')) {
            currentSection = 'nodes';
            currentType = line.substring(6);
            headers = [];
            continue;
        }

        if (line.startsWith('edges.')) {
            currentSection = 'edges';
            currentType = line.substring(6);
            headers = [];
            continue;
        }

        // Check for graph name
        if (line.startsWith('graph.')) {
            graphName = line.substring(6);
            continue;
        }

        // Parse data rows
        if (currentSection && line.includes('\t')) {
            const values = line.split('\t');

            // First data line is header
            if (headers.length === 0) {
                headers = values;
                continue;
            }

            // Parse data row
            if (currentSection === 'nodes') {
                const node = parseNodeRow(currentType, headers, values);
                if (node) {
                    nodes.push(node);
                }
            } else if (currentSection === 'edges') {
                const edge = parseEdgeRow(currentType, headers, values);
                if (edge) {
                    edges.push(edge);
                }
            }
        }
    }

    return { name: graphName, nodes, edges };
}

/**
 * Parse ISONL format string into GraphData
 */
export function parseISONL(content: string): GraphData {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    let graphName = 'graph';

    const lines = content.split('\n');

    for (const line of lines) {
        const trimmed = line.trim();

        // Skip empty lines and comments
        if (trimmed === '' || trimmed.startsWith('#')) {
            continue;
        }

        // Parse ISONL line format:
        // nodes.type id key=value key=value
        // edges.type :source_type:source_id :target_type:target_id key=value

        if (trimmed.startsWith('nodes.')) {
            const node = parseISONLNodeLine(trimmed);
            if (node) {
                nodes.push(node);
            }
        } else if (trimmed.startsWith('edges.')) {
            const edge = parseISONLEdgeLine(trimmed);
            if (edge) {
                edges.push(edge);
            }
        } else if (trimmed.startsWith('graph.')) {
            graphName = trimmed.substring(6).split(' ')[0];
        }
    }

    return { name: graphName, nodes, edges };
}

function parseNodeRow(
    nodeType: string,
    headers: string[],
    values: string[]
): GraphNode | null {
    if (values.length < 1) return null;

    const properties: Record<string, any> = {};
    let id = '';

    for (let i = 0; i < headers.length && i < values.length; i++) {
        const header = headers[i];
        const value = values[i];

        if (header === 'id') {
            id = value;
        } else {
            properties[header] = parseValue(value);
        }
    }

    // If no explicit id column, use first value
    if (!id && values.length > 0) {
        id = values[0];
    }

    return { type: nodeType, id, properties };
}

function parseEdgeRow(
    relType: string,
    headers: string[],
    values: string[]
): GraphEdge | null {
    if (values.length < 2) return null;

    let sourceType = '';
    let sourceId = '';
    let targetType = '';
    let targetId = '';
    const properties: Record<string, any> = {};

    for (let i = 0; i < headers.length && i < values.length; i++) {
        const header = headers[i].toLowerCase();
        const value = values[i];

        if (header === 'source' || header === 'from') {
            const parsed = parseNodeRef(value);
            sourceType = parsed.type;
            sourceId = parsed.id;
        } else if (header === 'target' || header === 'to') {
            const parsed = parseNodeRef(value);
            targetType = parsed.type;
            targetId = parsed.id;
        } else {
            properties[headers[i]] = parseValue(value);
        }
    }

    if (!sourceType || !targetType) return null;

    return {
        relType,
        sourceType,
        sourceId,
        targetType,
        targetId,
        properties
    };
}

function parseISONLNodeLine(line: string): GraphNode | null {
    // Format: nodes.type id key=value key=value
    const match = line.match(/^nodes\.(\w+)\s+(\S+)\s*(.*)?$/);
    if (!match) return null;

    const [, nodeType, id, propsStr] = match;
    const properties: Record<string, any> = {};

    if (propsStr) {
        const propPairs = propsStr.match(/(\w+)=("[^"]*"|\S+)/g);
        if (propPairs) {
            for (const pair of propPairs) {
                const [key, value] = pair.split('=');
                properties[key] = parseValue(value.replace(/^"|"$/g, ''));
            }
        }
    }

    return { type: nodeType, id, properties };
}

function parseISONLEdgeLine(line: string): GraphEdge | null {
    // Format: edges.TYPE :source_type:source_id :target_type:target_id key=value
    const match = line.match(/^edges\.(\w+)\s+:(\w+):(\S+)\s+:(\w+):(\S+)\s*(.*)?$/);
    if (!match) return null;

    const [, relType, sourceType, sourceId, targetType, targetId, propsStr] = match;
    const properties: Record<string, any> = {};

    if (propsStr) {
        const propPairs = propsStr.match(/(\w+)=("[^"]*"|\S+)/g);
        if (propPairs) {
            for (const pair of propPairs) {
                const [key, value] = pair.split('=');
                properties[key] = parseValue(value.replace(/^"|"$/g, ''));
            }
        }
    }

    return {
        relType,
        sourceType,
        sourceId,
        targetType,
        targetId,
        properties
    };
}

function parseNodeRef(ref: string): { type: string; id: string } {
    // Format: :type:id or type:id
    const cleaned = ref.replace(/^:/, '');
    const parts = cleaned.split(':');

    if (parts.length >= 2) {
        return { type: parts[0], id: parts.slice(1).join(':') };
    }

    return { type: 'node', id: cleaned };
}

function parseValue(value: string): any {
    // Try to parse as number
    if (/^-?\d+$/.test(value)) {
        return parseInt(value, 10);
    }
    if (/^-?\d+\.\d+$/.test(value)) {
        return parseFloat(value);
    }

    // Boolean
    if (value.toLowerCase() === 'true') return true;
    if (value.toLowerCase() === 'false') return false;

    // String
    return value;
}
