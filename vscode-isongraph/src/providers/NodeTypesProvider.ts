import * as vscode from 'vscode';
import { GraphData } from '../types';

/**
 * Tree data provider for node types view
 */
export class NodeTypesProvider implements vscode.TreeDataProvider<NodeTypeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<NodeTypeItem | undefined | void> =
        new vscode.EventEmitter<NodeTypeItem | undefined | void>();
    readonly onDidChangeTreeData: vscode.Event<NodeTypeItem | undefined | void> =
        this._onDidChangeTreeData.event;

    private graphData: GraphData = { name: '', nodes: [], edges: [] };

    refresh(graphData: GraphData): void {
        this.graphData = graphData;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: NodeTypeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: NodeTypeItem): Thenable<NodeTypeItem[]> {
        if (!element) {
            // Root level - show node types
            const typeCounts = new Map<string, number>();

            for (const node of this.graphData.nodes) {
                typeCounts.set(node.type, (typeCounts.get(node.type) || 0) + 1);
            }

            const items: NodeTypeItem[] = [];
            for (const [type, count] of typeCounts) {
                items.push(new NodeTypeItem(
                    type,
                    count,
                    vscode.TreeItemCollapsibleState.Collapsed
                ));
            }

            return Promise.resolve(items.sort((a, b) => a.label.localeCompare(b.label as string)));
        }

        // Show nodes of this type
        const nodes = this.graphData.nodes.filter(n => n.type === element.nodeType);
        const items = nodes.map(node => {
            const label = node.properties['name'] || node.id;
            return new NodeTypeItem(
                label,
                0,
                vscode.TreeItemCollapsibleState.None,
                node.type,
                true
            );
        });

        return Promise.resolve(items);
    }
}

class NodeTypeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly count: number,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly nodeType?: string,
        public readonly isNode: boolean = false
    ) {
        super(label, collapsibleState);

        if (!isNode) {
            this.description = `(${count})`;
            this.iconPath = new vscode.ThemeIcon('symbol-class');
            this.contextValue = 'nodeType';
        } else {
            this.iconPath = new vscode.ThemeIcon('circle-filled');
            this.contextValue = 'node';
        }
    }
}
