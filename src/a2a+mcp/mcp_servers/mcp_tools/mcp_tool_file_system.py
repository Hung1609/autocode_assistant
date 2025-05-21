# This file is used to pass a server to an ADK agent as a tool

from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

async def return_sse_mcp_tools_file_system():
    print("Attempting to connect to MCP server for file system ...")
    server_params = SseServerParams(
        url="http://localhost:8080/sse", # make sure the PORT is fit with the chosen one from mcp_servers.file_system_server.py
    )
    tools, exit_stack = await MCPToolset.from_server(connection_params=server_params)
    print("MCP Toolset created successfully.")
    return tools, exit_stack # what is exit_stack, what does it use for
