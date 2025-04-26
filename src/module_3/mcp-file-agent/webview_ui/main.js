// main.js for Webview UI

// This script will run within the webview context, not the extension context.
// It cannot access Node.js APIs directly. It communicates with the extension
// using vscode.postMessage().

// Get a reference to the VS Code API instance (provided by the extension framework)
// Check if running in a context where acquireVsCodeApi is available
let vscode;
if (typeof acquireVsCodeApi === 'function') {
    vscode = acquireVsCodeApi();
} else {
    // Provide a mock for local development/testing outside VS Code if needed
    console.warn("acquireVsCodeApi not found, using mock.");
    vscode = {
        postMessage: (message) => console.log("Mock postMessage:", message),
        getState: () => ({}), // Mock state
        setState: (state) => console.log("Mock setState:", state)
    };
}

// --- Get DOM Elements ---
const messageList = document.getElementById('message-list');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

// --- State (Optional but helpful for more complex UIs) ---
// You could use vscode.getState() and vscode.setState() to persist state across reloads

// --- Event Listeners ---

// Send message when button is clicked
sendButton.addEventListener('click', sendMessage);

// Send message when Enter is pressed in the textarea (Shift+Enter for new line)
userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevent default Enter behavior (new line)
        sendMessage();
    }
});

// Listen for messages from the extension backend
window.addEventListener('message', event => {
    const message = event.data; // The JSON data sent from the extension

    switch (message.type) {
        case 'agentResponse':
            addMessage(message.text, 'agent');
            break;
        case 'userEcho': // Display the user's message after sending
             addMessage(message.text, 'user');
             break;
        case 'error': // Display an error message differently
            addMessage(message.text, 'error');
            break;
        // Add more message types as needed (e.g., status updates)
    }
});

// --- Functions ---

function sendMessage() {
    const text = userInput.value.trim();
    if (text) {
        // Send the message text to the extension backend
        vscode.postMessage({
            type: 'userMessage',
            text: text
        });

        // Clear the input field
        userInput.value = '';
    }
}

function addMessage(text, senderType) {
    if (!messageList) return;

    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(senderType); // 'user', 'agent', or 'error'

    // Basic sanitization/rendering (replace with a markdown library for richer formatting)
    // For now, just handle newlines simply and set textContent for basic security.
    // Using innerHTML directly with unsanitized input is risky.
    // Convert newlines to <br> for display
    const contentWithBreaks = text.replace(/\n/g, '<br>');
    messageElement.innerHTML = contentWithBreaks; // Be cautious if text can contain HTML

    // Append the new message element
    messageList.appendChild(messageElement);

    // Scroll to the bottom of the message list
    messageList.scrollTop = messageList.scrollHeight;
}

// --- Initialization ---
userInput.focus(); // Focus the input field when the webview loads