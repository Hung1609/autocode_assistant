# This project is specify for my thesis
# Name of author:  Aggin


# Implement MCP server
1. Activate the mcp server by running python -m mcp_server.server at module_3 level
2. Open new VS Code window with mcp-file-agent as the root folder and find "Run and Debug" (Ctrl+Shift+D) and press F5.

If you encounter an error called "npm.ps1 cannot be loaded because running scripts is disabled on this system."

Make sure to change the PowerShell Execution Policy to allow scripts to run:

- Open PowerShell as Administrator
- Check Current Policy with "Get-ExecutionPolicy -List"
- Set Execution Policy for Current User with "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"

3. In the new Extension Development Host window, open the test workspace.
4. Open Command Pallette(Ctrl+Shift+P)
5. Type the command title: Start MCP File Agent Chat