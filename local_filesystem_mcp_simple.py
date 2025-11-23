"""
简化版 本地文件系统 MCP 服务器
支持动态路径配置和环境变量
"""

import os
import glob
import json
import shutil
import time
import asyncio
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

# 导入配置
from config import config, ROOT

# -----------------------------
# 配置项
# -----------------------------
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
CACHE_TTL_SECONDS = 30
SEARCH_THREADPOOL_WORKERS = 8
SEARCH_DEFAULT_LIMIT = 200
MAX_FILE_READ_SIZE = 10 * 1024 * 1024  # 10 MB

# -----------------------------
# MCP 实例
# -----------------------------
mcp = FastMCP(
    "Local File System (Dynamic)",
    instructions="本地文件系统操作服务器，支持动态路径配置和环境变量。",
    json_response=True
)

# -----------------------------
# 数据模型
# -----------------------------
class FileContent(BaseModel):
    path: str
    content: str
    size: int

class FileMeta(BaseModel):
    name: str
    path: str
    size: int
    modified: str

class DirectoryListing(BaseModel):
    path: str
    files: List[FileMeta]
    directories: List[str]

class SearchResult(BaseModel):
    file_path: str
    line_number: int
    content: str

# 请求参数模型
class WriteFileArgs(BaseModel):
    file_path: str
    content: str
    create_dirs: bool = True

class ReadFileArgs(BaseModel):
    file_path: str

class ListDirArgs(BaseModel):
    directory_path: Optional[str] = None

class SearchArgs(BaseModel):
    search_term: str
    directory_path: Optional[str] = None
    file_pattern: str = "*.md"
    limit: int = SEARCH_DEFAULT_LIMIT

class SetWorkingDirectoryArgs(BaseModel):
    path: str

# -----------------------------
# 辅助函数
# -----------------------------
def _now_iso(ts: Optional[float] = None) -> str:
    if ts is None:
        dt = datetime.now(timezone.utc)
    else:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat()

def _norm_path_str(path: Path) -> str:
    return str(path)

def _has_allowed_extension(path: Path) -> bool:
    if path.suffix == "":
        return True
    return path.suffix.lower() in ALLOWED_EXTENSIONS

def resolve_path(input_path: str, must_exist: bool = False) -> Path:
    """解析路径并检查是否在根目录内"""
    p = Path(input_path)
    if not p.is_absolute():
        # 相对路径相对于当前根目录
        p = (ROOT() / p).expanduser()
    p = p.resolve()

    # 检查是否在根目录内
    root_resolved = ROOT().resolve()
    if not (p == root_resolved or root_resolved in p.parents):
        raise PermissionError(f"路径越界：{p} (已限制在 {ROOT()})")

    if must_exist and not p.exists():
        raise FileNotFoundError(f"路径不存在：{p}")

    return p

# -----------------------------
# 工具实现
# -----------------------------
@mcp.tool()
async def read_file(ctx: Context[ServerSession, None], args: ReadFileArgs) -> FileContent:
    """读取文件内容"""
    try:
        path = resolve_path(args.file_path, must_exist=True)

        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")

        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许读取该文件类型：{path.suffix}")

        size = path.stat().st_size
        if size > MAX_FILE_READ_SIZE:
            raise PermissionError(f"文件过大，拒绝读取（>{MAX_FILE_READ_SIZE} 字节）: {path}")

        raw = path.read_bytes()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("utf-8", errors="replace")

        await ctx.info(f"读取文件：{path} ({size} 字节)")
        return FileContent(path=_norm_path_str(path), content=content, size=size)
        
    except Exception as e:
        await ctx.error(f"读取文件失败：{str(e)}")
        raise

@mcp.tool()
async def write_file(ctx: Context[ServerSession, None], args: WriteFileArgs) -> str:
    """写入文件"""
    try:
        path = resolve_path(args.file_path)
        
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

        if args.create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            if not path.parent.exists():
                raise FileNotFoundError(f"父目录不存在：{path.parent}")

        path.write_text(args.content, encoding="utf-8")
        await ctx.info(f"写入文件：{path}")
        return f"文件已写入：{_norm_path_str(path)}"
        
    except Exception as e:
        await ctx.error(f"写入文件失败：{str(e)}")
        raise

@mcp.tool()
async def list_directory(ctx: Context[ServerSession, None], args: ListDirArgs) -> DirectoryListing:
    """列出目录内容"""
    target = args.directory_path or str(ROOT())
    dir_path = resolve_path(target, must_exist=True)

    files_meta: List[FileMeta] = []
    directories: List[str] = []

    for item in dir_path.iterdir():
        try:
            if item.is_file():
                if not _has_allowed_extension(item):
                    continue
                st = item.stat()
                files_meta.append(FileMeta(
                    name=item.name,
                    path=_norm_path_str(item),
                    size=st.st_size,
                    modified=_now_iso(st.st_mtime)
                ))
            elif item.is_dir():
                directories.append(item.name)
        except PermissionError:
            continue

    listing = DirectoryListing(
        path=_norm_path_str(dir_path),
        files=sorted(files_meta, key=lambda x: x.name.lower()),
        directories=sorted(directories, key=lambda x: x.lower())
    )

    await ctx.info(f"列出目录：{dir_path} (files={len(files_meta)}, directories={len(directories)})")
    return listing

def _search_in_file(file_path: Path, search_term: str) -> List[SearchResult]:
    """在单个文件中搜索"""
    results: List[SearchResult] = []
    try:
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        st_lower = search_term.lower()
        for i, line in enumerate(lines, start=1):
            if st_lower in line.lower():
                results.append(SearchResult(
                    file_path=_norm_path_str(file_path),
                    line_number=i,
                    content=line.strip()
                ))
    except Exception:
        pass
    return results

@mcp.tool()
async def search_files(ctx: Context[ServerSession, None], args: SearchArgs) -> List[SearchResult]:
    """搜索文件内容"""
    directory_path = args.directory_path or str(ROOT())
    dir_path = resolve_path(directory_path, must_exist=True)

    pattern = str(dir_path / "**" / args.file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    matched_files = [p for p in matched_files if p.is_file() and _has_allowed_extension(p)]

    results: List[SearchResult] = []
    limit = max(1, min(args.limit, 5000))

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_THREADPOOL_WORKERS) as ex:
        tasks = [loop.run_in_executor(ex, _search_in_file, p, args.search_term) for p in matched_files]
        for fut in asyncio.as_completed(tasks):
            chunk: List[SearchResult] = await fut
            if chunk:
                results.extend(chunk)
            if len(results) >= limit:
                break

    results = results[:limit]
    await ctx.info(f"搜索完成：在 {dir_path} 中找到 {len(results)} 个匹配（limit={limit}）")
    return results

# -----------------------------
# 动态路径管理工具
# -----------------------------
@mcp.tool()
async def set_working_directory(ctx: Context[ServerSession, None], args: SetWorkingDirectoryArgs) -> str:
    """设置当前工作目录"""
    try:
        new_root = config.set_root(args.path)
        await ctx.info(f"工作目录已设置为：{new_root}")
        return f"工作目录已设置为：{new_root}"
    except Exception as e:
        await ctx.error(f"设置工作目录失败：{str(e)}")
        raise

@mcp.tool()
async def get_working_directory(ctx: Context[ServerSession, None]) -> Dict[str, str]:
    """获取当前工作目录信息"""
    current = str(config.get_root())
    await ctx.info(f"当前工作目录：{current}")
    return {
        "current_directory": current,
        "is_dynamic": "true"
    }

@mcp.tool()
async def reset_working_directory(ctx: Context[ServerSession, None]) -> str:
    """重置工作目录到默认"""
    try:
        default_root = config.reset_to_default()
        await ctx.info(f"工作目录已重置为默认：{default_root}")
        return f"工作目录已重置为默认：{default_root}"
    except Exception as e:
        await ctx.error(f"重置工作目录失败：{str(e)}")
        raise

# -----------------------------
# 资源定义
# -----------------------------
@mcp.resource("file://{path}")
def get_file_resource(path: str) -> str:
    try:
        p = resolve_path(path, must_exist=True)
        if not p.is_file():
            return f"不是文件: {path}"
        if not _has_allowed_extension(p):
            return "不允许读取该文件类型"
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {str(e)}"

@mcp.resource("dir://{path}")
def get_directory_resource(path: str) -> str:
    try:
        p = resolve_path(path, must_exist=True)
        if not p.is_dir():
            return f"不是目录: {path}"
        files = [i.name for i in p.iterdir() if i.is_file() and _has_allowed_extension(i)]
        dirs = [i.name for i in p.iterdir() if i.is_dir()]
        result = {"path": str(p), "files": sorted(files), "directories": sorted(dirs)}
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"ERROR: {str(e)}"

# -----------------------------
# 启动
# -----------------------------
if __name__ == "__main__":
    print("启动本地文件系统 MCP 服务器（动态路径版）...")
    print(f"根目录：{ROOT()}")
    print("支持环境变量 MCP_FILESYSTEM_ROOT 设置默认目录")
    print("按 Ctrl+C 停止服务器")
    mcp.run(transport="stdio")
