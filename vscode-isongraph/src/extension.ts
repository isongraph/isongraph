import * as vscode from 'vscode';
import { GraphVisualizerPanel } from './panels/GraphVisualizerPanel';
import { GraphOutlineProvider } from './providers/GraphOutlineProvider';
import { NodeTypesProvider } from './providers/NodeTypesProvider';
import { EdgeTypesProvider } from './providers/EdgeTypesProvider';
import { parseISON, parseISONL } from './parser/isonParser';
import { GraphData } from './types';

export function activate(context: vscode.ExtensionContext) {
    // Register tree view providers
    const graphOutlineProvider = new GraphOutlineProvider();
    const nodeTypesProvider = new NodeTypesProvider();
    const edgeTypesProvider = new EdgeTypesProvider();

    vscode.window.registerTreeDataProvider('isongraph.graphOutline', graphOutlineProvider);
    vscode.window.registerTreeDataProvider('isongraph.nodeTypes', nodeTypesProvider);
    vscode.window.registerTreeDataProvider('isongraph.edgeTypes', edgeTypesProvider);

    // Update providers when active editor changes
    vscode.window.onDidChangeActiveTextEditor(editor => {
        if (editor && isISONFile(editor.document)) {
            const graphData = parseDocument(editor.document);
            graphOutlineProvider.refresh(graphData);
            nodeTypesProvider.refresh(graphData);
            edgeTypesProvider.refresh(graphData);
        }
    });

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('isongraph.openVisualizer', () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && isISONFile(editor.document)) {
                const graphData = parseDocument(editor.document);
                GraphVisualizerPanel.createOrShow(context.extensionUri, graphData, editor.document.uri);
            } else {
                vscode.window.showErrorMessage('Please open an ISON or ISONL file first');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('isongraph.addNode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || !isISONFile(editor.document)) {
                vscode.window.showErrorMessage('Please open an ISON file first');
                return;
            }

            const nodeType = await vscode.window.showInputBox({
                prompt: 'Enter node type',
                placeHolder: 'person, company, document...'
            });
            if (!nodeType) return;

            const nodeId = await vscode.window.showInputBox({
                prompt: 'Enter node ID',
                placeHolder: 'unique_id'
            });
            if (!nodeId) return;

            const propsInput = await vscode.window.showInputBox({
                prompt: 'Enter properties (key=value, comma separated)',
                placeHolder: 'name=Alice, age=30'
            });

            // Parse properties
            const props: Record<string, string> = {};
            if (propsInput) {
                propsInput.split(',').forEach(pair => {
                    const [key, value] = pair.split('=').map(s => s.trim());
                    if (key && value) {
                        props[key] = value;
                    }
                });
            }

            // Insert node into document
            insertNode(editor, nodeType, nodeId, props);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('isongraph.addEdge', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || !isISONFile(editor.document)) {
                vscode.window.showErrorMessage('Please open an ISON file first');
                return;
            }

            const relType = await vscode.window.showInputBox({
                prompt: 'Enter relationship type',
                placeHolder: 'KNOWS, WORKS_AT, OWNS...'
            });
            if (!relType) return;

            const source = await vscode.window.showInputBox({
                prompt: 'Enter source node (type:id)',
                placeHolder: 'person:alice'
            });
            if (!source) return;

            const target = await vscode.window.showInputBox({
                prompt: 'Enter target node (type:id)',
                placeHolder: 'company:techcorp'
            });
            if (!target) return;

            // Insert edge into document
            insertEdge(editor, relType, source, target);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('isongraph.showStats', () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || !isISONFile(editor.document)) {
                vscode.window.showErrorMessage('Please open an ISON file first');
                return;
            }

            const graphData = parseDocument(editor.document);
            showGraphStats(graphData);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('isongraph.analyzeGraph', () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || !isISONFile(editor.document)) {
                vscode.window.showErrorMessage('Please open an ISON file first');
                return;
            }

            const graphData = parseDocument(editor.document);
            analyzeGraph(graphData);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('isongraph.findPath', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || !isISONFile(editor.document)) {
                vscode.window.showErrorMessage('Please open an ISON file first');
                return;
            }

            const start = await vscode.window.showInputBox({
                prompt: 'Enter start node (type:id)',
                placeHolder: 'person:alice'
            });
            if (!start) return;

            const end = await vscode.window.showInputBox({
                prompt: 'Enter end node (type:id)',
                placeHolder: 'person:bob'
            });
            if (!end) return;

            const graphData = parseDocument(editor.document);
            findPath(graphData, start, end);
        })
    );

    // Watch for document changes to update visualization
    vscode.workspace.onDidSaveTextDocument(document => {
        if (isISONFile(document)) {
            const config = vscode.workspace.getConfiguration('isongraph');
            if (config.get('autoRefresh')) {
                const graphData = parseDocument(document);
                GraphVisualizerPanel.updateIfVisible(graphData);
            }
        }
    });

    // Initial refresh if ISON file is open
    if (vscode.window.activeTextEditor && isISONFile(vscode.window.activeTextEditor.document)) {
        const graphData = parseDocument(vscode.window.activeTextEditor.document);
        graphOutlineProvider.refresh(graphData);
        nodeTypesProvider.refresh(graphData);
        edgeTypesProvider.refresh(graphData);
    }
}

function isISONFile(document: vscode.TextDocument): boolean {
    return document.languageId === 'ison' || document.languageId === 'isonl' ||
           document.fileName.endsWith('.ison') || document.fileName.endsWith('.isonl');
}

function parseDocument(document: vscode.TextDocument): GraphData {
    const content = document.getText();
    const isISONL = document.languageId === 'isonl' || document.fileName.endsWith('.isonl');

    try {
        if (isISONL) {
            return parseISONL(content);
        } else {
            return parseISON(content);
        }
    } catch (error) {
        console.error('Failed to parse ISON:', error);
        return { nodes: [], edges: [], name: 'error' };
    }
}

function insertNode(
    editor: vscode.TextEditor,
    nodeType: string,
    nodeId: string,
    props: Record<string, string>
): void {
    const document = editor.document;
    const text = document.getText();

    // Find or create nodes section for this type
    const sectionPattern = new RegExp(`^nodes\\.${nodeType}\\s*$`, 'm');
    const match = text.match(sectionPattern);

    if (match) {
        // Find the end of this section
        const sectionStart = match.index!;
        const sectionEnd = findSectionEnd(text, sectionStart);

        // Build row
        const headerLine = getHeaderLine(text, sectionStart);
        const row = buildNodeRow(nodeId, props, headerLine);

        // Insert before section end
        const insertPos = document.positionAt(sectionEnd);
        editor.edit(editBuilder => {
            editBuilder.insert(insertPos, row + '\n');
        });
    } else {
        // Create new section at end
        const propsKeys = Object.keys(props);
        const header = `nodes.${nodeType}\nid\t${propsKeys.join('\t')}\n`;
        const values = [nodeId, ...propsKeys.map(k => props[k])].join('\t');

        const endPos = document.positionAt(text.length);
        editor.edit(editBuilder => {
            editBuilder.insert(endPos, `\n${header}${values}\n`);
        });
    }
}

function insertEdge(
    editor: vscode.TextEditor,
    relType: string,
    source: string,
    target: string
): void {
    const document = editor.document;
    const text = document.getText();

    // Format source and target
    const formattedSource = source.startsWith(':') ? source : `:${source.replace(':', ':')}`;
    const formattedTarget = target.startsWith(':') ? target : `:${target.replace(':', ':')}`;

    // Find or create edges section for this type
    const sectionPattern = new RegExp(`^edges\\.${relType}\\s*$`, 'm');
    const match = text.match(sectionPattern);

    if (match) {
        const sectionStart = match.index!;
        const sectionEnd = findSectionEnd(text, sectionStart);
        const row = `${formattedSource}\t${formattedTarget}`;

        const insertPos = document.positionAt(sectionEnd);
        editor.edit(editBuilder => {
            editBuilder.insert(insertPos, row + '\n');
        });
    } else {
        // Create new section
        const section = `\nedges.${relType}\nsource\ttarget\n${formattedSource}\t${formattedTarget}\n`;

        const endPos = document.positionAt(text.length);
        editor.edit(editBuilder => {
            editBuilder.insert(endPos, section);
        });
    }
}

function findSectionEnd(text: string, sectionStart: number): number {
    const lines = text.substring(sectionStart).split('\n');
    let offset = sectionStart;

    for (let i = 1; i < lines.length; i++) {
        offset += lines[i - 1].length + 1;
        const line = lines[i].trim();

        // Section ends at empty line or new section header
        if (line === '' || line.startsWith('nodes.') || line.startsWith('edges.')) {
            return offset;
        }
    }

    return text.length;
}

function getHeaderLine(text: string, sectionStart: number): string {
    const lines = text.substring(sectionStart).split('\n');
    return lines[1] || 'id';
}

function buildNodeRow(id: string, props: Record<string, string>, headerLine: string): string {
    const headers = headerLine.split('\t');
    const values: string[] = [];

    for (const header of headers) {
        if (header === 'id') {
            values.push(id);
        } else {
            values.push(props[header] || '');
        }
    }

    return values.join('\t');
}

function showGraphStats(graphData: GraphData): void {
    const nodeTypes = new Set(graphData.nodes.map(n => n.type));
    const edgeTypes = new Set(graphData.edges.map(e => e.relType));

    const message = `
Graph: ${graphData.name || 'unnamed'}
━━━━━━━━━━━━━━━━━━━━━━
Nodes: ${graphData.nodes.length}
  Types: ${[...nodeTypes].join(', ')}
Edges: ${graphData.edges.length}
  Types: ${[...edgeTypes].join(', ')}
    `.trim();

    vscode.window.showInformationMessage(message, { modal: true });
}

function analyzeGraph(graphData: GraphData): void {
    // Calculate degree distribution
    const degrees: Record<string, number> = {};
    for (const node of graphData.nodes) {
        const key = `${node.type}:${node.id}`;
        degrees[key] = 0;
    }

    for (const edge of graphData.edges) {
        const sourceKey = `${edge.sourceType}:${edge.sourceId}`;
        const targetKey = `${edge.targetType}:${edge.targetId}`;
        degrees[sourceKey] = (degrees[sourceKey] || 0) + 1;
        degrees[targetKey] = (degrees[targetKey] || 0) + 1;
    }

    const degreeValues = Object.values(degrees);
    const maxDegree = Math.max(...degreeValues, 0);
    const avgDegreeNum = degreeValues.length > 0
        ? degreeValues.reduce((a, b) => a + b, 0) / degreeValues.length
        : 0;
    const avgDegree = avgDegreeNum.toFixed(2);

    // Find hub nodes
    const hubs = Object.entries(degrees)
        .filter(([_, deg]) => deg > avgDegreeNum)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    const message = `
Graph Analysis
━━━━━━━━━━━━━━━━━━━━━━
Max Degree: ${maxDegree}
Avg Degree: ${avgDegree}
Hub Nodes:
${hubs.map(([node, deg]) => `  ${node}: ${deg}`).join('\n')}
    `.trim();

    vscode.window.showInformationMessage(message, { modal: true });
}

function findPath(graphData: GraphData, startRef: string, endRef: string): void {
    // Build adjacency list
    const adj: Record<string, string[]> = {};
    for (const edge of graphData.edges) {
        const source = `${edge.sourceType}:${edge.sourceId}`;
        const target = `${edge.targetType}:${edge.targetId}`;

        if (!adj[source]) adj[source] = [];
        if (!adj[target]) adj[target] = [];
        adj[source].push(target);
        adj[target].push(source); // Undirected for path finding
    }

    // BFS for shortest path
    const queue: [string, string[]][] = [[startRef, [startRef]]];
    const visited = new Set<string>();

    while (queue.length > 0) {
        const [current, path] = queue.shift()!;

        if (current === endRef) {
            vscode.window.showInformationMessage(
                `Path found (${path.length - 1} hops):\n${path.join(' → ')}`
            );
            return;
        }

        if (visited.has(current)) continue;
        visited.add(current);

        for (const neighbor of adj[current] || []) {
            if (!visited.has(neighbor)) {
                queue.push([neighbor, [...path, neighbor]]);
            }
        }
    }

    vscode.window.showWarningMessage(`No path found between ${startRef} and ${endRef}`);
}

export function deactivate() {}
