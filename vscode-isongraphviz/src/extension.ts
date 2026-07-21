import * as vscode from 'vscode';
import * as path from 'path';
import { parseGraph } from './parser';

let panel: vscode.WebviewPanel | undefined;
let trackedDoc: vscode.Uri | undefined;
let lastDoc: vscode.TextDocument | undefined;
let updateTimer: ReturnType<typeof setTimeout> | undefined;

export function activate(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('isongraphviz.show', () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || !/\.isong?$/.test(editor.document.fileName)) {
                vscode.window.showWarningMessage('ISONGraph Viz: open a .ison graph file first.');
                return;
            }
            showPanel(context, editor.document);
        }),
        vscode.workspace.onDidChangeTextDocument((e) => {
            if (panel && trackedDoc && e.document.uri.toString() === trackedDoc.toString()) {
                lastDoc = e.document;
                if (updateTimer) clearTimeout(updateTimer);
                updateTimer = setTimeout(() => postGraph(e.document), 300);
            }
        })
    );
}

function showPanel(context: vscode.ExtensionContext, doc: vscode.TextDocument): void {
    trackedDoc = doc.uri;
    lastDoc = doc;
    if (panel) {
        panel.title = `Graph: ${path.basename(doc.fileName)}`;
        panel.reveal(vscode.ViewColumn.Beside, true);
        postGraph(doc);
    } else {
        panel = vscode.window.createWebviewPanel(
            'isongraphviz',
            `Graph: ${path.basename(doc.fileName)}`,
            { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')],
                retainContextWhenHidden: true,
            }
        );
        panel.onDidDispose(() => {
            panel = undefined;
            trackedDoc = undefined;
            lastDoc = undefined;
        });
        // Messages posted before the webview script loads are dropped, so the
        // initial graph is sent only after the webview reports it is ready.
        panel.webview.onDidReceiveMessage((msg) => {
            if (msg && msg.type === 'ready' && lastDoc) {
                postGraph(lastDoc);
            }
        });
        panel.webview.html = webviewHtml(context, panel.webview);
    }
}

function postGraph(doc: vscode.TextDocument): void {
    if (!panel) return;
    const config = vscode.workspace.getConfiguration('isongraphviz');
    const name = path.basename(doc.fileName);
    try {
        const graph = parseGraph(doc.getText(), name);
        panel.webview.postMessage({
            type: 'graph',
            graph,
            seed: config.get<number>('seed', 42),
            iterations: config.get<number>('iterations', 170),
        });
    } catch (err) {
        panel.webview.postMessage({ type: 'error', message: String(err) });
    }
}

function webviewHtml(context: vscode.ExtensionContext, webview: vscode.Webview): string {
    const nonce = Array.from({ length: 32 }, () =>
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[Math.floor(Math.random() * 62)]
    ).join('');
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', 'main.js'));
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', 'style.css'));
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="${styleUri}">
<title>ISONGraph Viz</title>
</head>
<body>
<div id="toolbar">
  <button id="btn-reset" title="Recompute the seeded deterministic layout">Reset layout</button>
  <button id="btn-fit" title="Fit graph to view">Fit</button>
  <label id="animate-label"><input type="checkbox" id="chk-animate" checked> Live physics</label>
  <span id="status"></span>
</div>
<div id="stage"></div>
<div id="tip"></div>
<script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}

export function deactivate(): void {
    panel = undefined;
}
