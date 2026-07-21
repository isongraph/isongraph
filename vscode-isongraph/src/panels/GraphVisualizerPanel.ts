import * as vscode from 'vscode';
import { GraphData, VisualizationData, VisualizationNode, VisualizationEdge } from '../types';

/**
 * Manages the graph visualizer webview panel
 */
export class GraphVisualizerPanel {
    public static currentPanel: GraphVisualizerPanel | undefined;
    private static readonly viewType = 'isongraphVisualizer';

    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _graphData: GraphData;
    private _documentUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(
        extensionUri: vscode.Uri,
        graphData: GraphData,
        documentUri: vscode.Uri
    ): void {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If we already have a panel, show it
        if (GraphVisualizerPanel.currentPanel) {
            GraphVisualizerPanel.currentPanel._panel.reveal(column);
            GraphVisualizerPanel.currentPanel._update(graphData);
            return;
        }

        // Otherwise, create a new panel
        const panel = vscode.window.createWebviewPanel(
            GraphVisualizerPanel.viewType,
            'ISONGraph Visualizer',
            column || vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.joinPath(extensionUri, 'out'),
                    vscode.Uri.joinPath(extensionUri, 'media')
                ]
            }
        );

        GraphVisualizerPanel.currentPanel = new GraphVisualizerPanel(
            panel,
            extensionUri,
            graphData,
            documentUri
        );
    }

    public static updateIfVisible(graphData: GraphData): void {
        if (GraphVisualizerPanel.currentPanel) {
            GraphVisualizerPanel.currentPanel._update(graphData);
        }
    }

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        graphData: GraphData,
        documentUri: vscode.Uri
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._graphData = graphData;
        this._documentUri = documentUri;

        // Set the webview's initial html content
        this._updateWebview();

        // Listen for when the panel is disposed
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'nodeClicked':
                        this._handleNodeClicked(message.node);
                        break;
                    case 'edgeClicked':
                        this._handleEdgeClicked(message.edge);
                        break;
                    case 'exportPng':
                        this._handleExportPng(message.dataUrl);
                        break;
                    case 'exportSvg':
                        this._handleExportSvg(message.svg);
                        break;
                }
            },
            null,
            this._disposables
        );
    }

    private _update(graphData: GraphData): void {
        this._graphData = graphData;
        this._panel.webview.postMessage({
            command: 'updateGraph',
            data: this._transformGraphData()
        });
    }

    private _updateWebview(): void {
        this._panel.webview.html = this._getHtmlForWebview();

        // Send initial data
        setTimeout(() => {
            this._panel.webview.postMessage({
                command: 'initGraph',
                data: this._transformGraphData(),
                config: this._getConfig()
            });
        }, 100);
    }

    private _transformGraphData(): VisualizationData {
        const config = vscode.workspace.getConfiguration('isongraph');
        const labelProperty = config.get<string>('labelProperty', 'name');

        const nodes: VisualizationNode[] = this._graphData.nodes.map(node => ({
            id: `${node.type}:${node.id}`,
            type: node.type,
            label: node.properties[labelProperty] || node.id,
            properties: node.properties
        }));

        const edges: VisualizationEdge[] = this._graphData.edges.map(edge => ({
            source: `${edge.sourceType}:${edge.sourceId}`,
            target: `${edge.targetType}:${edge.targetId}`,
            type: edge.relType,
            properties: edge.properties
        }));

        return { nodes, edges };
    }

    private _getConfig(): Record<string, any> {
        const config = vscode.workspace.getConfiguration('isongraph');
        return {
            layout: config.get('defaultLayout', 'force'),
            physics: config.get('physics', true),
            showLabels: config.get('showLabels', true),
            nodeColors: config.get('nodeColors', {})
        };
    }

    private _handleNodeClicked(node: VisualizationNode): void {
        const propsStr = Object.entries(node.properties)
            .map(([k, v]) => `${k}: ${v}`)
            .join('\n');

        vscode.window.showInformationMessage(
            `Node: ${node.id}\nType: ${node.type}\n${propsStr}`,
            { modal: false }
        );
    }

    private _handleEdgeClicked(edge: VisualizationEdge): void {
        vscode.window.showInformationMessage(
            `Edge: ${edge.source} -[${edge.type}]-> ${edge.target}`,
            { modal: false }
        );
    }

    private async _handleExportPng(dataUrl: string): Promise<void> {
        const uri = await vscode.window.showSaveDialog({
            filters: { 'PNG Image': ['png'] },
            defaultUri: vscode.Uri.file(`${this._graphData.name || 'graph'}.png`)
        });

        if (uri) {
            const data = dataUrl.replace(/^data:image\/png;base64,/, '');
            const buffer = Buffer.from(data, 'base64');
            await vscode.workspace.fs.writeFile(uri, buffer);
            vscode.window.showInformationMessage(`Exported to ${uri.fsPath}`);
        }
    }

    private async _handleExportSvg(svg: string): Promise<void> {
        const uri = await vscode.window.showSaveDialog({
            filters: { 'SVG Image': ['svg'] },
            defaultUri: vscode.Uri.file(`${this._graphData.name || 'graph'}.svg`)
        });

        if (uri) {
            const buffer = Buffer.from(svg, 'utf8');
            await vscode.workspace.fs.writeFile(uri, buffer);
            vscode.window.showInformationMessage(`Exported to ${uri.fsPath}`);
        }
    }

    public dispose(): void {
        GraphVisualizerPanel.currentPanel = undefined;

        this._panel.dispose();

        while (this._disposables.length) {
            const disposable = this._disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }

    private _getHtmlForWebview(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ISONGraph Visualizer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: var(--vscode-font-family);
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            overflow: hidden;
        }

        #container {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        #toolbar {
            display: flex;
            gap: 8px;
            padding: 8px;
            background-color: var(--vscode-titleBar-activeBackground);
            border-bottom: 1px solid var(--vscode-panel-border);
        }

        #toolbar button {
            padding: 4px 12px;
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        #toolbar button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }

        #toolbar select {
            padding: 4px 8px;
            background-color: var(--vscode-dropdown-background);
            color: var(--vscode-dropdown-foreground);
            border: 1px solid var(--vscode-dropdown-border);
            border-radius: 4px;
        }

        #graph-container {
            flex: 1;
            position: relative;
        }

        #graph {
            width: 100%;
            height: 100%;
        }

        .node {
            cursor: pointer;
        }

        .node circle {
            stroke: var(--vscode-editor-foreground);
            stroke-width: 1.5px;
        }

        .node text.node-label {
            font-size: 12px;
            font-weight: 600;
            fill: var(--vscode-editor-foreground);
            pointer-events: none;
            text-shadow:
                -1px -1px 0 var(--vscode-editor-background),
                1px -1px 0 var(--vscode-editor-background),
                -1px 1px 0 var(--vscode-editor-background),
                1px 1px 0 var(--vscode-editor-background),
                0 0 3px var(--vscode-editor-background);
        }

        .node text.node-type {
            font-size: 9px;
            fill: var(--vscode-descriptionForeground);
            pointer-events: none;
        }

        .link {
            stroke: #666;
            stroke-width: 2px;
            stroke-opacity: 0.7;
            fill: none;
        }

        .link:hover {
            stroke: var(--vscode-textLink-foreground);
            stroke-width: 3px;
            stroke-opacity: 1;
        }

        .link-label {
            font-size: 10px;
            font-weight: 500;
            fill: var(--vscode-editor-foreground);
            text-shadow:
                -1px -1px 0 var(--vscode-editor-background),
                1px -1px 0 var(--vscode-editor-background),
                -1px 1px 0 var(--vscode-editor-background),
                1px 1px 0 var(--vscode-editor-background);
        }

        #tooltip {
            position: absolute;
            padding: 8px 12px;
            background-color: var(--vscode-editorWidget-background);
            border: 1px solid var(--vscode-widget-border);
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 1000;
            max-width: 300px;
        }

        #tooltip.visible {
            opacity: 1;
        }

        #stats {
            position: absolute;
            bottom: 8px;
            left: 8px;
            padding: 8px;
            background-color: var(--vscode-editorWidget-background);
            border: 1px solid var(--vscode-widget-border);
            border-radius: 4px;
            font-size: 11px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="toolbar">
            <button id="btn-zoom-in">+</button>
            <button id="btn-zoom-out">−</button>
            <button id="btn-fit">Fit</button>
            <select id="layout-select">
                <option value="force">Force Layout</option>
                <option value="hierarchical">Hierarchical</option>
                <option value="circular">Circular</option>
            </select>
            <button id="btn-export-png">Export PNG</button>
            <button id="btn-export-svg">Export SVG</button>
        </div>
        <div id="graph-container">
            <svg id="graph"></svg>
            <div id="tooltip"></div>
            <div id="stats"></div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let graphData = { nodes: [], edges: [] };
        let config = {};
        let simulation;
        let svg, g, zoom;

        // Default colors for node types
        const defaultColors = {
            person: '#a8d5ba',
            company: '#f4a460',
            document: '#87ceeb',
            concept: '#dda0dd',
            event: '#f0e68c',
            default: '#cccccc'
        };

        function getNodeColor(type) {
            return config.nodeColors?.[type] || defaultColors[type] || defaultColors.default;
        }

        function initGraph(data, cfg) {
            graphData = data;
            config = cfg;

            svg = d3.select('#graph');
            const container = document.getElementById('graph-container');
            const width = container.clientWidth;
            const height = container.clientHeight;

            svg.attr('width', width).attr('height', height);

            // Setup zoom
            zoom = d3.zoom()
                .scaleExtent([0.1, 4])
                .on('zoom', (event) => {
                    g.attr('transform', event.transform);
                });

            svg.call(zoom);

            g = svg.append('g');

            // Build simulation
            simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.edges)
                    .id(d => d.id)
                    .distance(150))
                .force('charge', d3.forceManyBody().strength(-400))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(50));

            renderGraph();
            updateStats();

            simulation.on('tick', () => {
                g.selectAll('.link')
                    .attr('d', linkPath);

                g.selectAll('.node')
                    .attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');

                g.selectAll('.link-label')
                    .attr('transform', d => {
                        const midX = (d.source.x + d.target.x) / 2;
                        const midY = (d.source.y + d.target.y) / 2 - 8;
                        return 'translate(' + midX + ',' + midY + ')';
                    });
            });
        }

        function linkPath(d) {
            const nodeRadius = 25;
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist === 0) return '';

            // Calculate start point (edge of source node)
            const startX = d.source.x + (dx / dist) * nodeRadius;
            const startY = d.source.y + (dy / dist) * nodeRadius;

            // Calculate end point (edge of target node, leaving room for arrow)
            const endX = d.target.x - (dx / dist) * (nodeRadius + 5);
            const endY = d.target.y - (dy / dist) * (nodeRadius + 5);

            return 'M' + startX + ',' + startY + 'L' + endX + ',' + endY;
        }

        function renderGraph() {
            g.selectAll('*').remove();

            // Add arrow markers
            svg.append('defs').selectAll('marker')
                .data(['arrow'])
                .enter().append('marker')
                .attr('id', 'arrow')
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 10)
                .attr('refY', 0)
                .attr('markerWidth', 10)
                .attr('markerHeight', 10)
                .attr('orient', 'auto')
                .append('path')
                .attr('fill', '#555')
                .attr('d', 'M0,-4L10,0L0,4Z');

            // Draw edges
            const link = g.append('g')
                .selectAll('.link')
                .data(graphData.edges)
                .enter().append('path')
                .attr('class', 'link')
                .attr('marker-end', 'url(#arrow)')
                .on('click', (event, d) => {
                    vscode.postMessage({ command: 'edgeClicked', edge: d });
                });

            // Draw edge labels
            if (config.showLabels) {
                g.append('g')
                    .selectAll('.link-label')
                    .data(graphData.edges)
                    .enter().append('text')
                    .attr('class', 'link-label')
                    .text(d => d.type);
            }

            // Draw nodes
            const node = g.append('g')
                .selectAll('.node')
                .data(graphData.nodes)
                .enter().append('g')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragStarted)
                    .on('drag', dragged)
                    .on('end', dragEnded))
                .on('click', (event, d) => {
                    vscode.postMessage({ command: 'nodeClicked', node: d });
                })
                .on('mouseover', showTooltip)
                .on('mouseout', hideTooltip);

            // Node circle with larger radius
            node.append('circle')
                .attr('r', 25)
                .attr('fill', d => getNodeColor(d.type))
                .attr('stroke', '#333')
                .attr('stroke-width', 2);

            // Add label inside the circle (first letter or short name)
            node.append('text')
                .attr('class', 'node-label')
                .attr('dy', 5)
                .attr('text-anchor', 'middle')
                .style('font-size', '11px')
                .style('font-weight', '200')
                .style('fill', '#444')
                .text(d => d.label.substring(0, 4));

            // Add full label below the node
            if (config.showLabels) {
                node.append('text')
                    .attr('class', 'node-label')
                    .attr('dy', 45)
                    .attr('text-anchor', 'middle')
                    .text(d => d.label.length > 15 ? d.label.substring(0, 15) + '...' : d.label);

                // Add node type as subtitle
                node.append('text')
                    .attr('class', 'node-type')
                    .attr('dy', 58)
                    .attr('text-anchor', 'middle')
                    .text(d => '(' + d.type + ')');
            }
        }

        function updateGraph(data) {
            graphData = data;

            simulation.nodes(graphData.nodes);
            simulation.force('link').links(graphData.edges);
            simulation.alpha(0.3).restart();

            renderGraph();
            updateStats();
        }

        function updateStats() {
            const nodeTypes = [...new Set(graphData.nodes.map(n => n.type))];
            const edgeTypes = [...new Set(graphData.edges.map(e => e.type))];

            document.getElementById('stats').innerHTML =
                'Nodes: ' + graphData.nodes.length +
                ' | Edges: ' + graphData.edges.length +
                '<br>Types: ' + nodeTypes.join(', ');
        }

        function showTooltip(event, d) {
            const tooltip = document.getElementById('tooltip');
            const props = Object.entries(d.properties || {})
                .map(([k, v]) => '<b>' + k + '</b>: ' + v)
                .join('<br>');

            tooltip.innerHTML = '<b>' + d.type + ':' + d.id.split(':')[1] + '</b><br>' + props;
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top = (event.pageY + 10) + 'px';
            tooltip.classList.add('visible');
        }

        function hideTooltip() {
            document.getElementById('tooltip').classList.remove('visible');
        }

        function dragStarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragEnded(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        function fitGraph() {
            const bounds = g.node().getBBox();
            const container = document.getElementById('graph-container');
            const width = container.clientWidth;
            const height = container.clientHeight;

            const scale = 0.9 * Math.min(width / bounds.width, height / bounds.height);
            const tx = (width - bounds.width * scale) / 2 - bounds.x * scale;
            const ty = (height - bounds.height * scale) / 2 - bounds.y * scale;

            svg.transition().duration(500).call(
                zoom.transform,
                d3.zoomIdentity.translate(tx, ty).scale(scale)
            );
        }

        function changeLayout(layout) {
            const container = document.getElementById('graph-container');
            const width = container.clientWidth;
            const height = container.clientHeight;

            if (layout === 'hierarchical') {
                // Simple hierarchical layout
                const levels = {};
                graphData.nodes.forEach((n, i) => {
                    if (!levels[n.type]) levels[n.type] = [];
                    levels[n.type].push(n);
                });

                let y = 50;
                Object.values(levels).forEach(nodes => {
                    nodes.forEach((n, i) => {
                        n.fx = (i + 1) * width / (nodes.length + 1);
                        n.fy = y;
                    });
                    y += 150;
                });
            } else if (layout === 'circular') {
                const n = graphData.nodes.length;
                const radius = Math.min(width, height) / 3;
                graphData.nodes.forEach((node, i) => {
                    const angle = (2 * Math.PI * i) / n;
                    node.fx = width / 2 + radius * Math.cos(angle);
                    node.fy = height / 2 + radius * Math.sin(angle);
                });
            } else {
                // Force layout - remove fixed positions
                graphData.nodes.forEach(n => {
                    n.fx = null;
                    n.fy = null;
                });
            }

            simulation.alpha(0.5).restart();
        }

        // Button handlers
        document.getElementById('btn-zoom-in').onclick = () => {
            svg.transition().call(zoom.scaleBy, 1.2);
        };

        document.getElementById('btn-zoom-out').onclick = () => {
            svg.transition().call(zoom.scaleBy, 0.8);
        };

        document.getElementById('btn-fit').onclick = fitGraph;

        document.getElementById('layout-select').onchange = (e) => {
            changeLayout(e.target.value);
        };

        document.getElementById('btn-export-png').onclick = () => {
            const svgElement = document.getElementById('graph');
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const data = new XMLSerializer().serializeToString(svgElement);
            const img = new Image();

            img.onload = () => {
                canvas.width = svgElement.clientWidth;
                canvas.height = svgElement.clientHeight;
                ctx.fillStyle = getComputedStyle(document.body).backgroundColor;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
                const dataUrl = canvas.toDataURL('image/png');
                vscode.postMessage({ command: 'exportPng', dataUrl });
            };

            img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(data);
        };

        document.getElementById('btn-export-svg').onclick = () => {
            const svgElement = document.getElementById('graph');
            const data = new XMLSerializer().serializeToString(svgElement);
            vscode.postMessage({ command: 'exportSvg', svg: data });
        };

        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.command) {
                case 'initGraph':
                    initGraph(message.data, message.config);
                    break;
                case 'updateGraph':
                    updateGraph(message.data);
                    break;
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            const container = document.getElementById('graph-container');
            svg.attr('width', container.clientWidth)
               .attr('height', container.clientHeight);
            simulation.force('center', d3.forceCenter(container.clientWidth / 2, container.clientHeight / 2));
            simulation.alpha(0.3).restart();
        });
    </script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
</body>
</html>`;
    }
}
