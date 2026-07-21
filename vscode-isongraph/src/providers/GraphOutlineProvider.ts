import * as vscode from 'vscode';
import { GraphData, GraphNode, GraphEdge } from '../types';

/**
 * Tree data provider for graph outline view
 */
export class GraphOutlineProvider implements vscode.TreeDataProvider<GraphOutlineItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<GraphOutlineItem | undefined | void> =
        new vscode.EventEmitter<GraphOutlineItem | undefined | void>();
    readonly onDidChangeTreeData: vscode.Event<GraphOutlineItem | undefined | void> =
        this._onDidChangeTreeData.event;

    private graphData: GraphData = { name: '', nodes: [], edges: [] };

    refresh(graphData: GraphData): void {
        this.graphData = graphData;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: GraphOutlineItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: GraphOutlineItem): Thenable<GraphOutlineItem[]> {
        if (!element) {
            // Root level - show summary
            const items: GraphOutlineItem[] = [];

            // Graph name
            items.push(new GraphOutlineItem(
                `Graph: ${this.graphData.name || 'unnamed'}`,
                vscode.TreeItemCollapsibleState.None,
                'graph'
            ));

            // Nodes folder
            items.push(new GraphOutlineItem(
                `Nodes (${this.graphData.nodes.length})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                'nodes-folder'
            ));

            // Edges folder
            items.push(new GraphOutlineItem(
                `Edges (${this.graphData.edges.length})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                'edges-folder'
            ));

            return Promise.resolve(items);
        }

        if (element.contextValue === 'nodes-folder') {
            // Group nodes by type
            const nodesByType = new Map<string, GraphNode[]>();
            for (const node of this.graphData.nodes) {
                if (!nodesByType.has(node.type)) {
                    nodesByType.set(node.type, []);
                }
                nodesByType.get(node.type)!.push(node);
            }

            const items: GraphOutlineItem[] = [];
            for (const [type, nodes] of nodesByType) {
                items.push(new GraphOutlineItem(
                    `${type} (${nodes.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'node-type',
                    { type, nodes }
                ));
            }
            return Promise.resolve(items);
        }

        if (element.contextValue === 'node-type') {
            const nodes = element.data?.nodes as GraphNode[];
            return Promise.resolve(
                nodes.map(node => new GraphOutlineItem(
                    node.id,
                    vscode.TreeItemCollapsibleState.None,
                    'node',
                    { node }
                ))
            );
        }

        if (element.contextValue === 'edges-folder') {
            // Group edges by type
            const edgesByType = new Map<string, GraphEdge[]>();
            for (const edge of this.graphData.edges) {
                if (!edgesByType.has(edge.relType)) {
                    edgesByType.set(edge.relType, []);
                }
                edgesByType.get(edge.relType)!.push(edge);
            }

            const items: GraphOutlineItem[] = [];
            for (const [type, edges] of edgesByType) {
                items.push(new GraphOutlineItem(
                    `${type} (${edges.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'edge-type',
                    { type, edges }
                ));
            }
            return Promise.resolve(items);
        }

        if (element.contextValue === 'edge-type') {
            const edges = element.data?.edges as GraphEdge[];
            return Promise.resolve(
                edges.map(edge => new GraphOutlineItem(
                    `${edge.sourceType}:${edge.sourceId} → ${edge.targetType}:${edge.targetId}`,
                    vscode.TreeItemCollapsibleState.None,
                    'edge',
                    { edge }
                ))
            );
        }

        return Promise.resolve([]);
    }
}

class GraphOutlineItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string,
        public readonly data?: Record<string, any>
    ) {
        super(label, collapsibleState);

        // Set icons based on context
        switch (contextValue) {
            case 'graph':
                this.iconPath = new vscode.ThemeIcon('graph');
                break;
            case 'nodes-folder':
                this.iconPath = new vscode.ThemeIcon('symbol-class');
                break;
            case 'edges-folder':
                this.iconPath = new vscode.ThemeIcon('arrow-both');
                break;
            case 'node-type':
                this.iconPath = new vscode.ThemeIcon('symbol-interface');
                break;
            case 'node':
                this.iconPath = new vscode.ThemeIcon('circle-filled');
                break;
            case 'edge-type':
                this.iconPath = new vscode.ThemeIcon('arrow-right');
                break;
            case 'edge':
                this.iconPath = new vscode.ThemeIcon('arrow-small-right');
                break;
        }
    }
}
