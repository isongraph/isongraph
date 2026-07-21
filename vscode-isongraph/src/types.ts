/**
 * Type definitions for ISONGraph VSCode extension
 */

export interface GraphNode {
    type: string;
    id: string;
    properties: Record<string, any>;
}

export interface GraphEdge {
    relType: string;
    sourceType: string;
    sourceId: string;
    targetType: string;
    targetId: string;
    properties: Record<string, any>;
}

export interface GraphData {
    name: string;
    nodes: GraphNode[];
    edges: GraphEdge[];
    directed?: boolean;
}

export interface VisualizationNode {
    id: string;
    type: string;
    label: string;
    properties: Record<string, any>;
    x?: number;
    y?: number;
    fx?: number | null;
    fy?: number | null;
}

export interface VisualizationEdge {
    source: string;
    target: string;
    type: string;
    properties: Record<string, any>;
}

export interface VisualizationData {
    nodes: VisualizationNode[];
    edges: VisualizationEdge[];
}

export interface GraphStats {
    nodeCount: number;
    edgeCount: number;
    nodeTypes: string[];
    edgeTypes: string[];
    nodeCounts: Record<string, number>;
    edgeCounts: Record<string, number>;
}
