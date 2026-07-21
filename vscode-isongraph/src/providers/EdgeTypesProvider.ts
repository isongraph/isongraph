import * as vscode from 'vscode';
import { GraphData } from '../types';

/**
 * Tree data provider for edge types view
 */
export class EdgeTypesProvider implements vscode.TreeDataProvider<EdgeTypeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<EdgeTypeItem | undefined | void> =
        new vscode.EventEmitter<EdgeTypeItem | undefined | void>();
    readonly onDidChangeTreeData: vscode.Event<EdgeTypeItem | undefined | void> =
        this._onDidChangeTreeData.event;

    private graphData: GraphData = { name: '', nodes: [], edges: [] };

    refresh(graphData: GraphData): void {
        this.graphData = graphData;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: EdgeTypeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: EdgeTypeItem): Thenable<EdgeTypeItem[]> {
        if (!element) {
            // Root level - show edge types
            const typeCounts = new Map<string, number>();

            for (const edge of this.graphData.edges) {
                typeCounts.set(edge.relType, (typeCounts.get(edge.relType) || 0) + 1);
            }

            const items: EdgeTypeItem[] = [];
            for (const [type, count] of typeCounts) {
                items.push(new EdgeTypeItem(
                    type,
                    count,
                    vscode.TreeItemCollapsibleState.Collapsed
                ));
            }

            return Promise.resolve(items.sort((a, b) => a.label.localeCompare(b.label as string)));
        }

        // Show edges of this type
        const edges = this.graphData.edges.filter(e => e.relType === element.edgeType);
        const items = edges.map(edge => {
            const label = `${edge.sourceId} → ${edge.targetId}`;
            return new EdgeTypeItem(
                label,
                0,
                vscode.TreeItemCollapsibleState.None,
                edge.relType,
                true
            );
        });

        return Promise.resolve(items);
    }
}

class EdgeTypeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly count: number,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly edgeType?: string,
        public readonly isEdge: boolean = false
    ) {
        super(label, collapsibleState);

        if (!isEdge) {
            this.description = `(${count})`;
            this.iconPath = new vscode.ThemeIcon('arrow-both');
            this.contextValue = 'edgeType';
        } else {
            this.iconPath = new vscode.ThemeIcon('arrow-small-right');
            this.contextValue = 'edge';
        }
    }
}
