# *This server is built using an SSE-based MCP server since we aim to build multiple local MCP servers*
# Another approach is that it can be built using stdio mcp server --> ideal for a single local MCP server

import json
import os
import pathlib
import uvicorn
import argparse
from pydantic import BaseModel, ValidationError
from pathlib import Path
from datetime import datetime
from mcp.server.sse import SseServerTransport
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
from typing import List, Dict, Optional
from diff_match_patch import diff_match_patch

base_dir = pathlib.Path(__file__).resolve().parent
config_path = base_dir / "config.json"

with open(config_path, 'r') as f:
    config = json.load(f)

mcp = FastMCP("File System Server")

# Valication class --> make sure the type of data push into the function is valid
class ReadFileArguments(BaseModel):
    path: str

class CreateFileArguments(BaseModel):
    path: str
    content: str = ""

class WriteFileArguments(BaseModel):
    path: str
    content: str

class DeleteFileArguments(BaseModel):
    path: str

class CreateDirectoryArguments(BaseModel):
    path: str

class MoveFileArguments(BaseModel):
    source: str
    destination: str

class EditOperation(BaseModel):
    oldText: str
    newText: str

class EditFileArguments(BaseModel):
    path: str
    edits: List[EditOperation]
    dryRun: bool = False # dryRun for previewing changes before they are applied.

class ListDirectoryArguments(BaseModel):
    path: str

class SearchFilesArguments(BaseModel):
    path: str
    pattern: str
    excludePatterns: List[str] = []

class GetFileInfoArguments(BaseModel):
    path: str


# Security functions
def normalize_path(path: str) -> str: # remove "..", "." or "/" from the path.
    return os.path.normpath(path)

def expand_home(filepath: str) -> str: # Mở rộng dấu ~ thành thư mục home thật của người dùng (ví dụ ~/test.txt → /home/aggin/test.txt)
    if filepath.startswith("~/") or filepath == "~":
        return os.path.join(os.path.expanduser("~"), filepath[1:])
    return filepath

async def validate_path(requested_path: str, check_existence: bool = False) -> str:
    expanded_path = expand_home(requested_path)
    absolute = os.path.abspath(expanded_path) if not os.path.isabs(expanded_path) else os.path.abspath(expanded_path)
    normalized = normalize_path(absolute)

    allowed_directories = any(normalized.startswith(normalize_path(os.path.abspath(dir))) for dir in config["allowed_directories"]) # CHANGE THIS CONFIG LATER
    if not allowed_directories:
        raise ValueError(f"Truy cập bị từ chối: Đường dẫn {absolute} không nằm trong {', '.join(config['allowed_directories'])}") # CHANGE THIS CONFIG LATER

    extended = pathlib.Path(normalized).suffix.lower()
    if extended and extended not in config['restrictions']['allowed_extensions']:
        raise ValueError(f"Phần mở rộng {extended} không được phép")

    # handle symlinks 
    try:
        real_path = os.path.realpath(absolute)
        normalized_real = normalize_path(real_path)
        real_allowed_directories = any(normalized_real.startswith(normalize_path(os.path.abspath(dir))) for dir in config['allowed_directories'])
        if not real_allowed_directories:
            raise ValueError("Truy cập bị từ chối: Symlink trỏ ra ngoài thư mục được phép")
        if check_existence and not os.path.exists(real_path):
            raise ValueError(f"Đường dẫn không tồn tại: {real_path}")
        return real_path
    except FileNotFoundError:
        parent_dir = os.path.dirname(absolute)
        try:
            real_parent = os.path.realpath(parent_dir)
            normalized_real_parent = normalize_path(real_parent)
            real_parent_allowed = any(normalized_real_parent.startswith(normalize_path(os.path.abspath(dir))) for dir in config['allowed_directories'])
            if not real_parent_allowed:
                raise ValueError("Truy cập bị từ chối: Thư mục cha ngoài vùng cho phép")
            if check_existence:
                raise ValueError(f"Đường dẫn không tồn tại: {absolute}")
            return absolute
        except FileNotFoundError:
            raise ValueError(f"Thư mục cha không tồn tại: {parent_dir}")

# --- End Security functions ---

async def get_file_stats(file_path: str) -> Dict:
    stats = os.stat(file_path)
    size_mb = stats.st_size / (1024 * 1024)
    if size_mb > config['restrictions']['max_file_size_mb']:
        raise ValueError(f"File size exceeds the limit of {config['restrictions']['max_file_size_mb']} MB")
    return {
        "size": stats.st_size,
        "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stats.st_atime).isoformat(),
        "isDirectory": os.path.isdir(file_path),
        "isFile": os.path.isfile(file_path),
        "permissions": oct(stats.st_mode)[-3:]
    }

async def search_files(root_path: str, pattern: str, exclude_patterns: List[str] = []) -> List[str]:
    results = []

    async def search(current_path: str):
        try:
            entries = os.listdir(current_path)
            for entry in entries:
                full_path = os.path.join(current_path, entry)
                try:
                    await validate_path(full_path)
                    relative_path = os.path.relpath(full_path, root_path)
                    should_exclude = any(Path(relative_path).match(pat) for pat in exclude_patterns)
                    if should_exclude:
                        pass
                    if pattern.lower() in entry.lower():
                        results.append(full_path)
                    if os.path.isdir(full_path):
                        await search(full_path)
                except ValueError:
                    continue
        except OSError:
            pass
    await search(root_path)
    return results

def normalize_line_endings(text: str) -> str:
    return text.replace('\r\n', '\n')

async def apply_file_edits(file_path: str, edits: List[EditOperation], dry_run: bool = False) -> str:
    content = normalize_line_endings(open(file_path, 'r', encoding='utf-8').read())
    modified_content = content
    dmp = diff_match_patch()
    for edit in edits:
        normalized_old = normalize_line_endings(edit.oldText)
        normalized_new = normalize_line_endings(edit.newText)
        if normalized_old in modified_content:
            modified_content = modified_content.replace(normalized_old, normalized_new)
        else:
            patches = dmp.patch_make(modified_content, normalized_old, normalized_new) # can be wrong
            if not patches:
                raise ValueError(f"Không tìm thấy đoạn văn bản để chỉnh sửa:\n{edit.oldText}")
            modified_content, _ = dmp.patch_apply(patches, modified_content)
    diff = dmp.diff_main(content, modified_content)
    dmp.diff_cleanupSemantic(diff)
    diff_text = ''.join([f"+{t[1]}" if t[0] == 1 else f"-{t[1]}" if t[0] == -1 else t[1] for t in diff])
    formatted_diff = f"```diff\n{diff_text}\n```"

    if not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
    return formatted_diff

# TOOLS
@mcp.tool()
async def read_file(args: ReadFileArguments) -> str:
    valid_path = await validate_path(args.path, check_existence=True)
    return open(valid_path, 'r', encoding='utf-8').read()

@mcp.tool()
async def create_file(args: CreateFileArguments) -> str:
    valid_path = await validate_path(args.path)
    if os.path.exists(valid_path):
        raise ValueError(f"Tệp đã tồn tại: {args.path}")
    with open(valid_path, 'w', encoding='utf-8') as f:
        f.write(args.content)
    return f"Đã tạo thành công tệp {args.path}"

@mcp.tool()
async def write_file(args: WriteFileArguments) -> str:
    valid_path = await validate_path(args.path)
    with open(valid_path, 'w', encoding='utf-8') as f:
        f.write(args.content)
    return f"Đã ghi thành công vào {args.path}"

@mcp.tool()
async def delete_file(args: DeleteFileArguments) -> str:
    valid_path = await validate_path(args.path)
    if os.path.isdir(valid_path):
        raise ValueError(f"Đường dẫn là thư mục, không phải tệp: {args.path}")
    os.remove(valid_path)
    return f"Đã xóa thành công tệp {args.path}"

@mcp.tool()
async def create_directory(args: CreateDirectoryArguments) -> str:
    valid_path = await validate_path(args.path)
    os.makedirs(valid_path, exist_ok=True)
    return f"Đã tạo thành công thư mục {args.path}"

@mcp.tool()
async def move_file(args: MoveFileArguments) -> str:
    valid_source = await validate_path(args.source, check_exists=True)
    valid_destination = await validate_path(args.destination)
    if os.path.exists(valid_destination):
        raise ValueError(f"Đích đến đã tồn tại: {args.destination}")
    os.rename(valid_source, valid_destination)
    return f"Đã di chuyển thành công từ {args.source} đến {args.destination}"

@mcp.tool()
async def edit_file(args: EditFileArguments) -> str:
    valid_path = await validate_path(args.path, check_exists=True)
    return await apply_file_edits(valid_path, args.edits, args.dryRun)

@mcp.tool()
async def list_directory(args: ListDirectoryArguments) -> str:
    valid_path = await validate_path(args.path, check_exists=True)
    entries = os.listdir(valid_path)
    formatted = [f"[DIR] {e}" if os.path.isdir(os.path.join(valid_path, e)) else f"[FILE] {e}" for e in entries]
    return '\n'.join(formatted)

@mcp.tool()
async def search_files(args: SearchFilesArguments) -> str:
    valid_path = await validate_path(args.path, check_exists=True)
    results = await search_files(valid_path, args.pattern, args.excludePatterns)
    return '\n'.join(results) if results else "Không tìm thấy kết quả"

@mcp.tool()
async def get_file_info(args: GetFileInfoArguments) -> str:
    valid_path = await validate_path(args.path, check_exists=True)
    info = await get_file_stats(valid_path)
    return '\n'.join(f"{k}: {v}" for k, v in info.items())

# Create a Starlette application that can server the provied mcp server with SSE.
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
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(starlette_app, host=args.host, port=args.port)