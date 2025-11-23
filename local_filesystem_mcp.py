"""
优化版 本地文件系统 MCP 服务器
特性：
- 根目录强制限制（防止越界访问）
- 文件扩展名白名单
- 系统目录与敏感模式检查（Windows / Unix）
- 统一路径解析函数 resolve_path()
- 统一错误处理装饰器 with_fs_errors
- Pydantic 参数模型（便于文档/自动化）
- 并发搜索（ThreadPoolExecutor）与返回 limit
- 目录列表与文件列表缓存（TTL）
- 更丰富的 DirectoryListing（size, modified）
- 时间用 ISO8601 格式输出
- 常见操作：read/write/list/search/create/rename/move/copy/get_info/diff
"""

from __future__ import annotations
import os
import sys
import glob
import json
import shutil
import time
import asyncio
import concurrent.futures
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import List, Optional, Dict, Any
import difflib

from pydantic import BaseModel, Field

# 下面的两个 import 假定你的 mcp 包结构与原来一致
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

# -----------------------------
# 配置项（可改为从文件/环境加载）
# -----------------------------
import threading

# 线程安全的配置管理
class ConfigManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._current_root: Optional[Path] = None
        self._default_root: Optional[Path] = None
        self._load_default_config()
    
    def _load_default_config(self):
        """从环境变量加载默认配置"""
        with self._lock:
            # 优先使用环境变量，如果没有则使用默认路径
            env_root = os.getenv("MCP_FILESYSTEM_ROOT")
            if env_root:
                self._default_root = Path(env_root).expanduser().resolve()
            else:
                # 保持向后兼容性，使用原来的默认路径
                self._default_root = Path("D:/爱瑞安故事集").expanduser().resolve()
            
            self._current_root = self._default_root
    
    def get_root(self) -> Path:
        with self._lock:
            if self._current_root is None:
                raise RuntimeError("配置管理器未正确初始化")
            return self._current_root
    
    def set_root(self, new_root: str) -> str:
        with self._lock:
            new_path = Path(new_root).expanduser().resolve()
            # 验证路径存在且是目录
            if not new_path.exists():
                raise FileNotFoundError(f"路径不存在：{new_path}")
            if not new_path.is_dir():
                raise ValueError(f"路径不是目录：{new_path}")
            self._current_root = new_path
            return str(new_path)
    
    def reset_to_default(self) -> str:
        with self._lock:
            if self._default_root is None:
                raise RuntimeError("默认根目录未设置")
            self._current_root = self._default_root
            return str(self._current_root)
    
    def get_default_root(self) -> Path:
        with self._lock:
            if self._default_root is None:
                raise RuntimeError("默认根目录未设置")
            return self._default_root

# 全局配置管理器
config_manager = ConfigManager()

# 向后兼容的ROOT变量（使用函数包装，避免常量重定义问题）
def get_root() -> Path:
    return config_manager.get_root()

# 兼容性包装函数，替换原来的ROOT常量
def ROOT() -> Path:
    return config_manager.get_root()
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}  # 白名单
CACHE_TTL_SECONDS = 30  # 目录列表缓存 TTL
SEARCH_THREADPOOL_WORKERS = 8
SEARCH_DEFAULT_LIMIT = 200
MAX_FILE_READ_SIZE = 10 * 1024 * 1024  # 10 MB，超过拒绝读取

# 系统目录标识（小写，末尾包含斜杠以便匹配）
WINDOWS_SYSTEM_DIRS = [
    r"\windows\\", r"\program files\\", r"\program files (x86)\\", r"\system32\\"
]
UNIX_SYSTEM_DIRS = ["/etc/", "/var/", "/usr/", "/bin/", "/sbin/"]

# 敏感文件扩展
SENSITIVE_EXTENSIONS = {
    ".pem", ".key", ".ppk", ".db", ".sqlite", ".sqlite3", ".env", ".aws", ".crt"
}

# -----------------------------
# MCP 实例
# -----------------------------
mcp = FastMCP(
    "Local File System (Optimized)",
    instructions="本地文件系统操作服务器，提供受限的文件读写、目录浏览、搜索、笔记管理等功能。所有操作限制在预设根目录下。",
    json_response=True,
    stateless_http=True
)

# -----------------------------
# Pydantic 数据模型
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


class NoteInfo(BaseModel):
    title: str
    path: str
    size: int
    created_time: Optional[str]
    modified_time: Optional[str]


# 请求参数模型（便于工具自动化与文档）
class WriteFileArgs(BaseModel):
    file_path: str
    content: str
    create_dirs: bool = True


class ReadFileArgs(BaseModel):
    file_path: str


class ListDirArgs(BaseModel):
    directory_path: Optional[str] = None  # None 表示默认工作目录


class SearchArgs(BaseModel):
    search_term: str
    directory_path: Optional[str] = None
    file_pattern: str = "*.md"
    limit: int = SEARCH_DEFAULT_LIMIT
    use_regex: bool = False  # 支持扩展（当前仅 substring）


class CreateNoteArgs(BaseModel):
    title: str
    content: str = ""
    directory_path: Optional[str] = None


class RenameArgs(BaseModel):
    src: str
    dst: str


class MoveArgs(BaseModel):
    src: str
    dst_dir: str
    overwrite: bool = False


class SetWorkingDirectoryArgs(BaseModel):
    path: str


# -----------------------------
# 简单缓存实现（目录列表）
# -----------------------------
_dir_cache: Dict[str, Dict[str, Any]] = {}  # path -> {"ts": float, "value": DirectoryListing}


def _cache_get_dir(path: str) -> Optional[DirectoryListing]:
    entry = _dir_cache.get(path)
    if not entry:
        return None
    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        _dir_cache.pop(path, None)
        return None
    return entry["value"]


def _cache_set_dir(path: str, value: DirectoryListing) -> None:
    _dir_cache[path] = {"ts": time.time(), "value": value}


# -----------------------------
# 辅助函数
# -----------------------------
def _now_iso(ts: Optional[float] = None) -> str:
    if ts is None:
        dt = datetime.now(timezone.utc)
    else:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat()


def _is_windows() -> bool:
    return os.name == "nt"


def _norm_path_str(path: Path) -> str:
    # 统一显示路径风格（string）
    return str(path)


def _is_in_root(path: Path) -> bool:
    try:
        # 使两侧都为绝对 resolved path 以便比较
        rp = path.resolve()
        root_resolved = ROOT.resolve()
        # 判断 rp 是否等于 root 或 root 的子路径
        return rp == root_resolved or root_resolved in rp.parents
    except Exception:
        return False


def _has_allowed_extension(path: Path) -> bool:
    if path.suffix == "":
        # 无后缀视为允许（例如笔记名可能没有后缀，但我们通常要求 .md）
        return True
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def _is_sensitive_by_pattern(path: Path) -> bool:
    ap = str(path.absolute()).lower()
    for ext in SENSITIVE_EXTENSIONS:
        if ap.endswith(ext):
            return True
    # 系统目录
    if _is_windows():
        for sd in WINDOWS_SYSTEM_DIRS:
            if sd in ap:
                return True
    else:
        for sd in UNIX_SYSTEM_DIRS:
            if sd in ap:
                return True
    return False


def resolve_path(input_path: str, must_exist: bool = False) -> Path:
    """
    统一解析输入路径，扩展 ~，转换为绝对路径并检查越界与敏感性。
    若 must_exist=True，会检查文件/目录存在性。
    """
    p = Path(input_path)
    if not p.is_absolute():
        # 相对路径相对于 ROOT
        p = (ROOT / p).expanduser()
    p = p.resolve()

    # 强制限定根目录内
    if not _is_in_root(p):
        raise PermissionError(f"路径越界：{p} (已限制在 {ROOT})")

    # 敏感性检查
    if _is_sensitive_by_pattern(p):
        raise PermissionError(f"不允许访问敏感路径或文件类型：{p}")

    if must_exist and not p.exists():
        raise FileNotFoundError(f"路径不存在：{p}")

    return p


# 统一错误处理装饰器
def with_fs_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # ctx 通常是第1个参数（方法签名：ctx, ...）
        ctx: Optional[Context[ServerSession, None]] = None
        if len(args) > 0 and isinstance(args[0], Context):
            ctx = args[0]
        try:
            return await func(*args, **kwargs)
        except PermissionError as e:
            if ctx:
                await ctx.error(f"PermissionError: {str(e)}")
            raise
        except FileNotFoundError as e:
            if ctx:
                await ctx.error(f"FileNotFoundError: {str(e)}")
            raise
        except UnicodeDecodeError as e:
            if ctx:
                await ctx.error(f"Unicode decode error: {str(e)}")
            raise
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error: {str(e)}")
            raise
    return wrapper


# -----------------------------
# 工具实现
# -----------------------------

@mcp.tool()
@with_fs_errors
async def read_file(ctx: Context[ServerSession, None], args: ReadFileArgs | dict) -> FileContent:
    """
    读取文件内容（限制大小），返回 content 与 size。
    """
    if isinstance(args, dict):
        args = ReadFileArgs(**args)

    path = resolve_path(args.file_path, must_exist=True)

    if not path.is_file():
        raise ValueError(f"路径不是文件：{path}")

    # 后缀白名单
    if not _has_allowed_extension(path):
        raise PermissionError(f"不允许读取该文件类型：{path.suffix}")

    size = path.stat().st_size
    if size > MAX_FILE_READ_SIZE:
        raise PermissionError(f"文件过大，拒绝读取（>{MAX_FILE_READ_SIZE} 字节）: {path}")

    # 以二进制读取然后 decode（更稳健）
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        # 尝试带 errors='replace'
        content = raw.decode("utf-8", errors="replace")

    await ctx.info(f"读取文件：{path} ({size} 字节)")

    return FileContent(path=_norm_path_str(path), content=content, size=size)


@mcp.tool()
@with_fs_errors
async def write_file(ctx: Context[ServerSession, None], args: WriteFileArgs | dict) -> str:
    """
    写入或覆盖文件。默认会创建父目录（可通过 create_dirs 控制）。
    """
    if isinstance(args, dict):
        args = WriteFileArgs(**args)

    path = resolve_path(args.file_path)
    if not _has_allowed_extension(path):
        raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

    if args.create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        if not path.parent.exists():
            raise FileNotFoundError(f"父目录不存在：{path.parent}")

    # 写入（utf-8）
    path.write_text(args.content, encoding="utf-8")
    await ctx.info(f"写入文件：{path}")

    # 清理目录缓存（父目录）
    _dir_cache.pop(str(path.parent), None)

    return f"文件已写入：{_norm_path_str(path)}"


@mcp.tool()
@with_fs_errors
async def list_directory(ctx: Context[ServerSession, None], args: ListDirArgs | dict = None) -> DirectoryListing:
    """
    列出目录内容，返回更丰富的文件元数据（name,size,modified）
    支持缓存 ttl
    """
    if args is None:
        args = ListDirArgs()

    if isinstance(args, dict):
        args = ListDirArgs(**args)

    target = args.directory_path or str(ROOT)
    dir_path = resolve_path(target, must_exist=True)

    # 尝试从缓存读取
    cache_key = str(dir_path)
    cached = _cache_get_dir(cache_key)
    if cached:
        await ctx.info(f"从缓存返回目录：{dir_path}")
        return cached

    files_meta: List[FileMeta] = []
    directories: List[str] = []

    for item in dir_path.iterdir():
        try:
            if item.is_file():
                # 只展示允许类型（可根据需求调整）
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
            # 跳过无法访问的文件
            continue

    listing = DirectoryListing(
        path=_norm_path_str(dir_path),
        files=sorted(files_meta, key=lambda x: x.name.lower()),
        directories=sorted(directories, key=lambda x: x.lower())
    )

    _cache_set_dir(cache_key, listing)
    await ctx.info(f"列出目录：{dir_path} (files={len(files_meta)}, directories={len(directories)})")
    return listing


# 内部的 IO 搜索实现（阻塞）——适合放入线程池
def _search_in_file(file_path: Path, search_term: str) -> List[SearchResult]:
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
        # 跳过任何无法读取的文件
        pass
    return results


@mcp.tool()
@with_fs_errors
async def search_files(ctx: Context[ServerSession, None], args: SearchArgs | dict) -> List[SearchResult]:
    """
    并发地在匹配文件中搜索文本（substring，大小写不敏感）。
    支持 limit，默认限制以防返回过多结果。
    """
    if isinstance(args, dict):
        args = SearchArgs(**args)

    directory_path = args.directory_path or str(ROOT)
    dir_path = resolve_path(directory_path, must_exist=True)

    # 生成匹配模式（支持 **）
    pattern = str(dir_path / "**" / args.file_pattern)

    # 收集文件列表（注意使用 glob 而非 Path.rglob 以便 Windows 支持）
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    # 过滤文件
    matched_files = [p for p in matched_files if p.is_file() and _has_allowed_extension(p) and not _is_sensitive_by_pattern(p)]

    results: List[SearchResult] = []
    limit = max(1, min(args.limit, 5000))  # 防止滥用

    # 使用线程池并行化文件读取/搜索
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


@mcp.tool()
@with_fs_errors
async def create_note(ctx: Context[ServerSession, None], args: CreateNoteArgs | dict) -> str:
    """
    创建笔记。title 可以包含子目录，例如 '角色/海伦娜' 或 'folder/note.md'
    如果没有 .md 后缀，会自动添加 .md
    """
    if isinstance(args, dict):
        args = CreateNoteArgs(**args)

    target_dir = args.directory_path or str(ROOT)
    base_dir = resolve_path(target_dir, must_exist=True)

    # 清理并构造文件名
    cleaned = "".join(c for c in args.title if c not in r'<>:"/\|?*')  # 简单清理非法文件名字符
    if not cleaned.lower().endswith(".md"):
        cleaned = cleaned + ".md"

    file_path = (base_dir / cleaned).resolve()
    # 再检查越界
    if not _is_in_root(file_path):
        raise PermissionError(f"创建路径越界：{file_path}")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(args.content, encoding="utf-8")

    # 清缓存
    _dir_cache.pop(str(file_path.parent), None)
    await ctx.info(f"创建笔记：{file_path}")
    return f"笔记已创建：{_norm_path_str(file_path)}"


@mcp.tool()
@with_fs_errors
async def get_note_info(ctx: Context[ServerSession, None], note_path: str) -> NoteInfo:
    """
    获取笔记详细信息，时间使用 ISO8601（UTC）
    """
    path = resolve_path(note_path, must_exist=True)
    if not path.is_file():
        raise ValueError(f"不是文件：{path}")
    st = path.stat()
    return NoteInfo(
        title=path.stem,
        path=_norm_path_str(path),
        size=st.st_size,
        created_time=_now_iso(st.st_ctime),
        modified_time=_now_iso(st.st_mtime)
    )


# 操作：rename, move, copy
@mcp.tool()
@with_fs_errors
async def rename_file(ctx: Context[ServerSession, None], args: RenameArgs | dict) -> str:
    if isinstance(args, dict):
        args = RenameArgs(**args)
    src = resolve_path(args.src, must_exist=True)
    dst = resolve_path(args.dst)  # 目标可以不存在
    if not src.is_file():
        raise ValueError(f"源不是文件：{src}")
    if not _has_allowed_extension(dst):
        raise PermissionError(f"目标文件类型不允许：{dst.suffix}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    # 清缓存
    _dir_cache.pop(str(src.parent), None)
    _dir_cache.pop(str(dst.parent), None)
    await ctx.info(f"重命名 {src} -> {dst}")
    return f"已重命名为：{_norm_path_str(dst)}"


@mcp.tool()
@with_fs_errors
async def move_file(ctx: Context[ServerSession, None], args: MoveArgs | dict) -> str:
    if isinstance(args, dict):
        args = MoveArgs(**args)
    src = resolve_path(args.src, must_exist=True)
    dst_dir = resolve_path(args.dst_dir, must_exist=True)
    if not src.is_file():
        raise ValueError(f"源不是文件：{src}")
    dst = dst_dir / src.name
    if dst.exists() and not args.overwrite:
        raise FileExistsError(f"目标已存在：{dst}")
    shutil.move(str(src), str(dst))
    _dir_cache.pop(str(src.parent), None)
    _dir_cache.pop(str(dst.parent), None)
    await ctx.info(f"移动文件：{src} -> {dst}")
    return f"已移动到：{_norm_path_str(dst)}"


@mcp.tool()
@with_fs_errors
async def copy_file(ctx: Context[ServerSession, None], args: MoveArgs | dict) -> str:
    # reuse MoveArgs: src, dst_dir, overwrite
    if isinstance(args, dict):
        args = MoveArgs(**args)
    src = resolve_path(args.src, must_exist=True)
    dst_dir = resolve_path(args.dst_dir, must_exist=True)
    if not src.is_file():
        raise ValueError(f"源不是文件：{src}")
    dst = dst_dir / src.name
    if dst.exists() and not args.overwrite:
        raise FileExistsError(f"目标已存在：{dst}")
    shutil.copy2(str(src), str(dst))
    _dir_cache.pop(str(dst.parent), None)
    await ctx.info(f"复制文件：{src} -> {dst}")
    return f"已复制到：{_norm_path_str(dst)}"


@mcp.tool()
@with_fs_errors
async def diff_files(ctx: Context[ServerSession, None], src: str, dst: str, max_lines: int = 400) -> str:
    """
    计算两个文件的 unified diff（文本）。如果文件过大或非文本，用错误返回。
    """
    s = resolve_path(src, must_exist=True)
    d = resolve_path(dst, must_exist=True)
    if not s.is_file() or not d.is_file():
        raise ValueError("两个路径都必须是文件")
    # 读取
    try:
        s_text = s.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        raise PermissionError("源文件非 UTF-8 文本或无法解码")
    try:
        d_text = d.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        raise PermissionError("目标文件非 UTF-8 文本或无法解码")

    diff = difflib.unified_diff(s_text, d_text, fromfile=str(s), tofile=str(d), lineterm="")
    lines = list(diff)[:max_lines]
    if not lines:
        return "无差异"
    return "\n".join(lines)


# -----------------------------
# 动态路径管理工具
# -----------------------------
@mcp.tool()
@with_fs_errors
async def set_working_directory(ctx: Context[ServerSession, None], args: SetWorkingDirectoryArgs | dict) -> str:
    """
    设置当前工作目录（根目录）。所有后续操作都将限制在此目录下。
    支持环境变量 MCP_FILESYSTEM_ROOT 设置默认目录。
    """
    if isinstance(args, dict):
        args = SetWorkingDirectoryArgs(**args)

    try:
        new_root = config_manager.set_root(args.path)
        # 更新全局 ROOT 变量
        global ROOT
        ROOT = config_manager.get_root()
        
        # 清空缓存，因为根目录改变了
        _dir_cache.clear()
        
        await ctx.info(f"工作目录已设置为：{new_root}")
        return f"工作目录已设置为：{new_root}"
    except Exception as e:
        await ctx.error(f"设置工作目录失败：{str(e)}")
        raise


@mcp.tool()
@with_fs_errors
async def get_working_directory(ctx: Context[ServerSession, None]) -> Dict[str, str]:
    """
    获取当前工作目录信息，包括当前目录和默认目录。
    """
    current = str(config_manager.get_root())
    default = str(config_manager.get_default_root())
    
    await ctx.info(f"当前工作目录：{current}")
    return {
        "current_directory": current,
        "default_directory": default,
        "is_default": current == default
    }


@mcp.tool()
@with_fs_errors
async def reset_working_directory(ctx: Context[ServerSession, None]) -> str:
    """
    重置工作目录到默认目录（环境变量或原始配置）。
    """
    try:
        default_root = config_manager.reset_to_default()
        # 更新全局 ROOT 变量
        global ROOT
        ROOT = config_manager.get_root()
        
        # 清空缓存
        _dir_cache.clear()
        
        await ctx.info(f"工作目录已重置为默认：{default_root}")
        return f"工作目录已重置为默认：{default_root}"
    except Exception as e:
        await ctx.error(f"重置工作目录失败：{str(e)}")
        raise


# -----------------------------
# 资源定义（file:// dir://）
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
    print("启动本地文件系统 MCP 服务器（优化版）...")
    print(f"根目录：{ROOT}")
    print("按 Ctrl+C 停止服务器")
    mcp.run(transport="stdio")
