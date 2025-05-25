# This file is used to pass a server to an ADK agent as a tool

from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

async def return_sse_mcp_tools_file_system():
    print("Attempting to connect to MCP server for file system ...")
    server_params = SseServerParams(
        url="http://localhost:8080/sse", # make sure the PORT is fit with the chosen one from mcp_servers.file_system_server.py
    )
    tools, exit_stack = await MCPToolset.from_server(connection_params=server_params) # this is for version 0.1.0 which we will use for this project
    # toolset = MCPToolset(connection_params=server_params) # this is for adk version 1.0.0
    # tools, exit_stack = await toolset.get_tools()
    print("MCP Toolset created successfully.")
    return tools, exit_stack 

# --> exit_stack là một instance của contextlib.AsyncExitStack (hoặc tương tự), được trả về bởi MCPToolset.from_server để quản lý tài nguyên bất đồng bộ.
# --> Khi MCPToolset.from_server thiết lập kết nối SSE đến server MCP, nó có thể mở các tài nguyên như luồng mạng hoặc hàng đợi.
# --> exit_stack theo dõi các tài nguyên này và đảm bảo chúng được đóng (hoặc giải phóng) khi context manager thoát.
# --> exit_stack được trả về cùng tools để agent ADK có thể sử dụng context manager này trong quá trình chạy.