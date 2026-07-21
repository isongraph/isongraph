# ISONGraph VSCode Extension

Visual graph editor and explorer for ISONGraph files with interactive visualization.

## Features

### Graph Visualization
- **Interactive D3.js-based visualization** - Drag nodes, zoom, and pan
- **Multiple layout algorithms** - Force-directed, hierarchical, circular
- **Node type coloring** - Automatic coloring by node type
- **Edge labels** - Relationship types displayed on edges
- **Tooltips** - Hover over nodes to see properties

### Graph Explorer
- **Graph Outline** - Tree view of all nodes and edges
- **Node Types** - Browse nodes organized by type
- **Edge Types** - Browse edges organized by relationship type

### Graph Editing
- **Add Node** - Right-click to add new nodes
- **Add Edge** - Right-click to add new relationships
- **Auto-sync** - Visualization updates on file save

### Export
- **Export PNG** - Save graph as PNG image
- **Export SVG** - Save graph as SVG vector graphic

### Analysis
- **Graph Statistics** - View node/edge counts and types
- **Path Finding** - Find shortest path between nodes
- **Hub Detection** - Identify highly connected nodes

## Usage

### Opening the Visualizer

1. Open any `.ison` or `.isonl` file
2. Click the graph icon in the editor title bar, or
3. Open Command Palette (`Ctrl+Shift+P`) and run "ISONGraph: Open Graph Visualizer"

### Adding Nodes

1. Right-click in the editor
2. Select "ISONGraph: Add Node"
3. Enter node type (e.g., `person`)
4. Enter node ID (e.g., `alice`)
5. Enter properties (e.g., `name=Alice, age=30`)

### Adding Edges

1. Right-click in the editor
2. Select "ISONGraph: Add Edge"
3. Enter relationship type (e.g., `KNOWS`)
4. Enter source node (e.g., `person:alice`)
5. Enter target node (e.g., `person:bob`)

### Keyboard Shortcuts

- `+` / `-` - Zoom in/out
- Mouse wheel - Zoom
- Click + drag on background - Pan
- Click + drag on node - Move node
- Click on node - Show details

## Configuration

Configure the extension in VS Code settings:

```json
{
  "isongraph.defaultLayout": "force",
  "isongraph.autoRefresh": true,
  "isongraph.showLabels": true,
  "isongraph.labelProperty": "name",
  "isongraph.physics": true,
  "isongraph.nodeColors": {
    "person": "#a8d5ba",
    "company": "#f4a460",
    "document": "#87ceeb"
  }
}
```

### Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `defaultLayout` | string | `"force"` | Default layout algorithm |
| `autoRefresh` | boolean | `true` | Auto-refresh on file save |
| `showLabels` | boolean | `true` | Show node/edge labels |
| `labelProperty` | string | `"name"` | Property to use as node label |
| `physics` | boolean | `true` | Enable physics simulation |
| `nodeColors` | object | `{}` | Custom colors for node types |

### Layout Options

- **force** - Force-directed layout (default)
- **hierarchical** - Top-to-bottom hierarchy
- **circular** - Nodes arranged in a circle

## Commands

| Command | Description |
|---------|-------------|
| `ISONGraph: Open Graph Visualizer` | Open visualization panel |
| `ISONGraph: Add Node` | Add a new node |
| `ISONGraph: Add Edge` | Add a new edge |
| `ISONGraph: Show Graph Statistics` | Display graph stats |
| `ISONGraph: Analyze Graph` | Analyze graph structure |
| `ISONGraph: Find Path Between Nodes` | Find shortest path |
| `ISONGraph: Export as PNG` | Export visualization as PNG |
| `ISONGraph: Export as SVG` | Export visualization as SVG |

## Example ISON File

```
nodes.person
id	name	age
alice	Alice	30
bob	Bob	25
carol	Carol	35

nodes.company
id	name
techcorp	TechCorp

edges.KNOWS
source	target	since
:person:alice	:person:bob	2020
:person:bob	:person:carol	2021

edges.WORKS_AT
source	target	role
:person:alice	:company:techcorp	Engineer
:person:bob	:company:techcorp	Designer
```

## Requirements

- VS Code 1.74.0 or higher
- ISON Language Support extension (optional, for syntax highlighting)

## Installation

### From VSIX

1. Download the `.vsix` file
2. Open VS Code
3. Go to Extensions view (`Ctrl+Shift+X`)
4. Click "..." menu → "Install from VSIX..."
5. Select the downloaded file

### From Source

```bash
cd tools/vscode-isongraph
npm install
npm run compile
# Press F5 to launch Extension Development Host
```

## Development

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch

# Run linter
npm run lint

# Package extension
npx vsce package
```

## License

MIT
