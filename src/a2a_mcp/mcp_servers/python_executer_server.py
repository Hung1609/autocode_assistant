import asyncio
import uvicorn
from mcp.server.sse import SseServerTransport
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
from pydantic import BaseModel
import subprocess
import argparse

mcp = FastMCP("Python Executor Server")

class ExecuteCodeArguments(BaseModel):
    code: str

@mcp.tool()
async def execute_code(args: ExecuteCodeArguments) -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "python", "-c", args.code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return {
            "status": "success" if process.returncode == 0 else "error",
            "output": stdout.decode(),
            "error": stderr.decode()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
def create_starlette_app(
    mcp_server: Server, # the mcp server to serve
    *,
    debug: bool = False, # whether to enable debug mode
) -> Starlette: # ép kiểu tạo thành 1 Starlette application
    sse = SseServerTransport("/message/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send, # noqa: SLF001 -->  bỏ qua cảnh báo từ công cụ lint (như Flake8) và Cảnh báo về truy cập thuộc tính private (_send), vì _send là phương thức nội bộ của Starlette.
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/message/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server # noqa: WPS43 --> Bỏ qua cảnh báo từ Flake8 về sử dụng thuộc tính không rõ ràng hoặc không chuẩn.
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8081, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(starlette_app, host=args.host, port=args.port)