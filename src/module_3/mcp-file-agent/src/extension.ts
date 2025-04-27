// This implementation is based on the assumptions that user starts manually beforehand. So the extension just needs the URL which is http://127.0.0.1:5100 that we are implementing.


// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { spawn, ChildProcess } from 'child_process';
import { kill } from 'process';


let webviewPanel: vscode.WebviewPanel | undefined;
// let childProcess: ChildProcess | undefined; // add later when implement auto-start/stop process
let agentClientProcess: ChildProcess | undefined;

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

	// Use the console to output diagnostic information (console.log) and errors (console.error)
	// This line of code will only be executed once when your extension is activated
	console.log('Congratulations, your extension "mcp-file-agent" is now active!');
	context.subscriptions.push(
		vscode.commands.registerCommand('mcp-file-agent.startChat', () => {
			createOrShowWebviewPanel(context);
		})
	);
	// Optional: Register command to stop managed processes if panel is closed manually
    // context.subscriptions.push(
    //     vscode.commands.registerCommand('mcp-file-agent.stopProcesses', () => {
    //         killAgentClientProcess();
    //         // killMcpServerProcess(); // If managed
    //     })
    // );
}

function createOrShowWebviewPanel(context: vscode.ExtensionContext) {
	const column = vscode.window.activateTextEditor ? vscode.window.activeTextEditor.viewColumn : undefined;
	// if we have a panel, show it
	if (webviewPanel) {
		webviewPanel.reveal(column);
		return;
	}
	// if not, create a new one
	webviewPanel = vscode.window.createWebviewPanel(
		'mcpFileAgent', // Typr of webview
		'MCP File Agent', // Title of the panel
		column || vscode.ViewColumn.One, // Editor column to show the panel in
		getWebViewOptions(context.extensionUri) // Security options
	);

	// Set the webview's HTML content
	webviewPanel.webview.html = getWebViewContent(webviewPanel.webview, context.extensionUri);
	// Handle messages from the webview
	webviewPanel.webview.onDidReceiveMessage(
		message =? handleWebviewMessage(message, webviewPanel as vscode.WebviewPannel, context),
		undefined,
		context.subscriptions
	);
	// Handle panel disposal
	webviewPanel.onDidDispose(
		() => {
			webviewPanel = undefined;
			killAgentClientProcess();
			// killMcpServerProcess(); // If managed
			console.log("Webview panel disposed, processes cleaned up.");
		},
		null,
		context.subscriptions
	);
	// for another implementation: Have the extension start the MCP server process when activated and terminate it when deactivated. Use child_process.spawn to run python path/to/mcp_server/server.py. You'll need to manage this process lifecycle, capture its output/errors for logging, and ensure the port is available. This is more complex.
	// startMcpServer(context);
}

function getWebViewOptions(extensionUri:vscode.Uri): vscode.WebviewOptions {
	return {
		enableScripts: true, // Enable JavaScript in the webview
		loacalResourceRoots: [vscode.Uri.joinPath(extensionUri, 'webview_ui')], // restrict to only loading content from our extension's webview_ui directory
	};
}

// Function to get Nonce (Number used once)
function getNonce() {
	let text = '';
	const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
	for (let i = 0; i < 32; i++) {
		text += possible.charAt(Math.floor(Math.random() * possible.length));
	}
	return text;
}

function getWebViewContent(webview: vscode.Webview, extensionUri: vscode.Uri): string {
	const scriptPath = vscode.Uri.joinPath(extensionUri, 'webview-ui', 'main.js');
    const stylesPath = vscode.Uri.joinPath(extensionUri, 'webview-ui', 'style.css');
    const htmlPath = vscode.Uri.joinPath(extensionUri, 'webview-ui', 'main.html');

    // Convert file paths to URIs consumable by the webview
    const scriptUri = webview.asWebviewUri(scriptPath);
    const stylesUri = webview.asWebviewUri(stylesPath);

    // Generate a nonce for script security
    const nonce = getNonce();

    // Read the actual HTML file content
    let htmlContent = "";
    try {
        htmlContent = fs.readFileSync(htmlPath.fsPath, 'utf8');
        // Replace placeholders in the HTML with the correct URIs and nonce
        htmlContent = htmlContent.replace('${stylesUri}', stylesUri.toString());
        htmlContent = htmlContent.replace('${scriptUri}', scriptUri.toString());
        htmlContent = htmlContent.replace(/\${nonce}/g, nonce); // Replace all nonce placeholders
    } catch (err) {
        console.error("Error reading webview HTML file:", err);
        vscode.window.showErrorMessage('Failed to load agent chat interface.');
        htmlContent = `<!DOCTYPE html><html><body>Error loading webview content. See console for details.</body></html>`;
    }
    return htmlContent;
}

function handleWebviewMessage(message: any, panel: vscode.WebviewPanel, context: vscode.ExtensionContext) {
	switch (message.type) {
        case 'userMessage':
            const userPrompt = message.text;
            console.log(`Received user prompt: ${userPrompt}`);
            if (!userPrompt) return;

            // Get current workspace folder path
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders || workspaceFolders.length === 0) {
                panel.webview.postMessage({ type: 'error', text: 'ERROR: Please open a project folder before using the agent.' });
                return;
            }
            // Use the path of the first workspace folder
            const workspacePath = workspaceFolders[0].uri.fsPath;
            console.log(`Using workspace path: ${workspacePath}`);

            // Echo user message back to UI immediately
            panel.webview.postMessage({ type: 'userEcho', text: userPrompt });
            // Show "thinking" status
            panel.webview.postMessage({ type: 'agentResponse', text: '<i>Processing your request...</i>' });

            // --- Execute the Python Agent Client ---
            try {
                // ** IMPORTANT: Define the correct paths relative to the *extension's* location **
                context.extensionPath = "AUTOCODE_ASSISTANT/src/module_3/";
                // We need to go UP one level from extensionPath to reach module_3, then into agent_client

                // Determine Python executable path based on OS (adjust 'Scripts' vs 'bin')
                const venvDirName = process.platform === "win32" ? "Scripts" : "bin";
                const pythonExecutable = process.platform === "win32" ? "python.exe" : "python";

                const agentClientBasePath = path.join(context.extensionPath, '..', 'agent_client'); // Path to agent_client folder
                const agentClientScriptPath = path.join(agentClientBasePath, 'agent_core.py');
                const agentClientVenvPythonPath = path.join(agentClientBasePath, 'venv', venvDirName, pythonExecutable);

                console.log(`Agent client Python path: ${agentClientVenvPythonPath}`);
                console.log(`Agent client script path: ${agentClientScriptPath}`);

                // --- Path Existence Checks ---
                if (!fs.existsSync(agentClientVenvPythonPath)) {
                    const errorMsg = `Python interpreter not found for agent client: ${agentClientVenvPythonPath}. Please ensure the 'agent_client' virtual environment exists and is structured correctly relative to the extension.`;
                    console.error(errorMsg);
                    vscode.window.showErrorMessage(errorMsg);
                    panel.webview.postMessage({ type: 'error', text: `SETUP ERROR: Agent client Python environment not found.` });
                    return;
                }
                 if (!fs.existsSync(agentClientScriptPath)) {
                    const errorMsg = `Agent client script not found: ${agentClientScriptPath}. Ensure agent_core.py exists.`;
                    console.error(errorMsg);
                    vscode.window.showErrorMessage(errorMsg);
                    panel.webview.postMessage({ type: 'error', text: `SETUP ERROR: Agent client script not found.` });
                    return;
                }
                // --- End Checks ---

                // Ensure previous process is killed before starting a new one
                killAgentClientProcess();

                console.log(`Spawning agent client: ${agentClientVenvPythonPath} ${agentClientScriptPath} --prompt "${userPrompt.substring(0,30)}..." --workspace "${workspacePath}"`);

                // Spawn the process using the specific Python interpreter from the venv
                agentClientProcess = spawn(
                    agentClientVenvPythonPath, // Use the python from the venv
                    [
                        agentClientScriptPath,
                        '--prompt', userPrompt,
                        '--workspace', workspacePath
                    ],
                    {
                        // Set CWD to the agent_client directory so it can find its .env file
                        cwd: agentClientBasePath,
                        // Ensure stdio streams use utf8 encoding
                        stdio: ['pipe', 'pipe', 'pipe'], // stdin, stdout, stderr
                        encoding: 'utf8'
                    }
                );

                let agentResponseData = '';
                let agentErrorData = '';

                // Handle stdout data (the agent's final response)
                if (agentClientProcess.stdout) {
                    agentClientProcess.stdout.on('data', (data) => {
                         console.log(`Agent stdout: ${data}`);
                        agentResponseData += data.toString();
                    });
                } else {
                     console.error("Agent client process stdout stream is null.");
                }


                // Handle stderr data (errors from the python script)
                 if (agentClientProcess.stderr) {
                    agentClientProcess.stderr.on('data', (data) => {
                         console.error(`Agent stderr: ${data}`);
                        agentErrorData += data.toString();
                    });
                 } else {
                     console.error("Agent client process stderr stream is null.");
                 }


                // Handle process exit
                agentClientProcess.on('close', (code) => {
                    console.log(`Agent client process exited with code ${code}`);
                    agentClientProcess = undefined; // Clear the process variable

                    if (code === 0 && agentResponseData) {
                        // Success
                        panel.webview.postMessage({ type: 'agentResponse', text: agentResponseData.trim() });
                    } else {
                        // Error or no response
                        const errorMessage = `Agent process finished with error (code ${code}). ${agentErrorData ? `Error Output: ${agentErrorData.trim()}` : (agentResponseData ? `Output: ${agentResponseData.trim()}` : 'No output received.')}`;
                        console.error(errorMessage);
                         // Send detailed error only if there was stderr output, otherwise send simpler message
                         const displayError = agentErrorData ? `Error: ${agentErrorData.trim()}` : `Agent execution failed (code ${code}). Check Output channel for details.`;
                         panel.webview.postMessage({ type: 'error', text: displayError });
                    }
                });

                // Handle spawn errors (e.g., command not found)
                agentClientProcess.on('error', (err) => {
                    console.error('Failed to start agent client process:', err);
                    vscode.window.showErrorMessage(`Failed to start agent process: ${err.message}`);
                    panel.webview.postMessage({ type: 'error', text: `FATAL ERROR: Could not start agent process. ${err.message}` });
                    agentClientProcess = undefined;
                });

            } catch (error: any) {
                console.error("Error executing agent client:", error);
                vscode.window.showErrorMessage(`Error running agent: ${error.message || error}`);
                panel.webview.postMessage({ type: 'error', text: `CLIENT ERROR: ${error.message || error}` });
            }
            return; // End of 'userMessage' case
    }
} // 27/4

function killAgentClientProcess() {
    if (agentClientProcess)
        try {
            console.log(`Attempting to kill agent client process (PID: ${agentClientProcess.pid})...`);
            // Use SIGTERM first, might need SIGKILL on some OS or stubborn processes
            const killed = agentClientProcess.kill('SIGTERM');
            if (killed) {
                 console.log("Agent client process killed successfully.");
            } else {
                 console.warn("Agent client process kill command returned false (process might have already exited?).");
            }
        } catch (error) {
            console.error("Error attempting to kill agent client process:", error);
        } finally {
            agentClientProcess = undefined; // Clear the process variable
        }
}

// This method is called when your extension is deactivated
export function deactivate() {
    console.log("Deactivating MCP File Agent extension.");
    // Clean up processes when the extension is deactivated
    killAgentClientProcess();
    // killMcpServerProcess(); // If managed by extension
    if (webviewPanel) {
        webviewPanel.dispose();
    }
}

// --- MCP Server Management Functions (Placeholders for Option B) ---
// function startMcpServer(context: vscode.ExtensionContext) {
//     // Implementation needed:
//     // 1. Define path to mcp_server/server.py and its venv python
//     // 2. Check if already running (e.g., check port or PID file)
//     // 3. Spawn the server process using child_process.spawn
//     // 4. Store the process handle in mcpServerProcess
//     // 5. Handle its stdout/stderr for logging
//     // 6. Handle its 'close' and 'error' events
//     console.log("MCP Server auto-start not implemented yet.");
// }

// function killMcpServerProcess() {
//     // Implementation needed:
//     // 1. Check if mcpServerProcess exists and is running
//     // 2. Send SIGTERM (or SIGKILL)
//     // 3. Clear mcpServerProcess variable
//     if (mcpServerProcess) {
//          console.log("Attempting to kill MCP server process...");
//          // mcpServerProcess.kill...
//          mcpServerProcess = undefined;
//     }
// }
