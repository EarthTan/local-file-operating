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
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import quote


from pydantic import BaseModel, Field, field_validator

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
    matched_terms: List[str]

class SearchResults(BaseModel):
    total_matches: int
    results: List[SearchResult]
    limit: int
    search_logic: str

# 请求参数模型
class WriteFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要写入的文件路径"
    )
    content: str = Field(
        ...,
        description="要写入的文件内容"
    )
    create_dirs: bool = Field(
        True,
        description="如果父目录不存在，是否自动创建目录"
    )
    open_after_write: bool = Field(
        False,
        description="写入后是否在 Obsidian 中打开文件"
    )

class OpenNoteArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要打开的笔记文件路径"
    )

class ReadFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要读取的文件路径"
    )
    open_after_read: bool = Field(
        False,
        description="读取后是否在 Obsidian 中打开文件"
    )

class ListDirArgs(BaseModel):
    directory_path: Optional[str] = Field(
        None,
        description="要列出的目录路径，默认为当前工作目录"
    )
    limit: Optional[int] = Field(
        50,
        description="文件数量限制，默认50，超过50会自动设置为50",
        ge=1,
        le=50
    )

class SearchArgs(BaseModel):
    """搜索文件参数模型"""
    
    search_term: str = Field(
        ...,
        description="搜索关键词，支持多关键词布尔搜索"
    )
    
    directory_path: Optional[str] = Field(
        None,
        description="搜索目录路径，默认为当前工作目录"
    )
    
    file_pattern: str = Field(
        "*.md",
        description="文件模式匹配，支持通配符"
    )
    
    limit: int = Field(
        SEARCH_DEFAULT_LIMIT,
        description="搜索结果数量限制",
        ge=1,
        le=5000
    )
    
    search_logic: str = Field(
        "OR",
        description="搜索逻辑：'OR' 匹配任意关键词，'AND' 必须匹配所有关键词"
    )
    
    search_mode: str = Field(
        "both",
        description="""搜索模式：
        - 'both': 同时搜索文件名和文件内容（默认）
        - 'filename_only': 只搜索文件名
        - 'content_only': 只搜索文件内容
        """
    )
    
    @field_validator("search_logic")
    def validate_search_logic(cls, v: str) -> str:
        """验证搜索逻辑参数"""
        if v.upper() not in ["OR", "AND"]:
            raise ValueError("search_logic 必须是 'OR' 或 'AND'")
        return v.upper()
    
    @field_validator("search_mode")
    def validate_search_mode(cls, v: str) -> str:
        """验证搜索模式参数，支持别名"""
        valid_modes = {
            "both": "both",
            "filename_only": "filename_only",
            "filename": "filename_only",  # 支持别名
            "content_only": "content_only",
            "content": "content_only"     # 支持别名
        }
        
        normalized = valid_modes.get(v.lower())
        if normalized is None:
            raise ValueError(f"search_mode 必须是 {list(valid_modes.keys())} 之一")
        
        return normalized

class SetWorkingDirectoryArgs(BaseModel):
    path: str = Field(
        ...,
        description="要设置为工作目录的路径"
    )

# 部分编辑参数模型
class AppendFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要追加内容的文件路径"
    )
    content: str = Field(
        ...,
        description="要追加的内容"
    )
    open_after_append: bool = Field(
        False,
        description="追加后是否在 Obsidian 中打开文件"
    )

class InsertFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要插入内容的文件路径"
    )
    line_number: int = Field(
        ...,
        description="要插入内容的行号（从1开始）",
        ge=1
    )
    content: str = Field(
        ...,
        description="要插入的内容"
    )
    open_after_insert: bool = Field(
        False,
        description="插入后是否在 Obsidian 中打开文件"
    )

class ReplaceFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要替换内容的文件路径"
    )
    search_text: str = Field(
        ...,
        description="要搜索并替换的文本"
    )
    replace_text: str = Field(
        ...,
        description="替换后的文本"
    )
    open_after_replace: bool = Field(
        False,
        description="替换后是否在 Obsidian 中打开文件"
    )

class DeleteFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要删除内容的文件路径"
    )
    line_start: int = Field(
        ...,
        description="要删除的起始行号（从1开始）",
        ge=1
    )
    line_end: int = Field(
        ...,
        description="要删除的结束行号（从1开始）",
        ge=1
    )
    open_after_delete: bool = Field(
        False,
        description="删除后是否在 Obsidian 中打开文件"
    )

class PatchFileArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="要应用补丁的文件路径"
    )
    patch_content: str = Field(
        ...,
        description="统一差异格式的补丁内容"
    )
    open_after_patch: bool = Field(
        False,
        description="应用补丁后是否在 Obsidian 中打开文件"
    )

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

def generate_obsidian_uri(file_path: Path) -> str:
    """
    生成符合 Obsidian 官方规范的 URI
    obsidian://open?vault=<encoded vault>&file=<encoded path>
    """
    try:
        relative_path = _get_relative_path(file_path)

        # 统一为正斜杠
        relative_path = str(relative_path).replace("\\", "/")

        vault_name = ROOT().name

        # 对 vault 和 file 进行 URL 编码
        vault_encoded = quote(vault_name, safe="")
        file_encoded = quote(relative_path, safe="/")  # 保留目录结构

        uri = f"obsidian://open?vault={vault_encoded}&file={file_encoded}"
        return uri

    except Exception as e:
        raise ValueError(f"生成 Obsidian URI 失败: {str(e)}")

def open_file_with_obsidian(file_path: Path) -> bool:
    """使用 Obsidian URI 打开文件"""
    try:
        uri = generate_obsidian_uri(file_path)
        
        # 根据操作系统使用不同的命令打开 URI
        system = platform.system().lower()
        
        if system == "windows":
            # Windows 使用 start 命令
            subprocess.run(f'start "" "{uri}"', shell=True, check=True)
        elif system == "darwin":
            # macOS 使用 open 命令
            subprocess.run(["open", uri], check=True)
        elif system == "linux":
            # Linux 使用 xdg-open 命令
            subprocess.run(["xdg-open", uri], check=True)
        else:
            raise OSError(f"不支持的操作系统: {system}")
        
        return True
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"打开文件失败: Obsidian 可能未安装或无法启动 - {str(e)}")
    except Exception as e:
        raise RuntimeError(f"打开文件失败: {str(e)}")

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

        # 如果设置了读取后打开，则尝试打开文件
        if args.open_after_read:
            try:
                open_file_with_obsidian(path)
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                await ctx.warning(f"读取文件成功，但打开失败：{str(open_error)}")

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
        
        result_message = f"文件已写入：{_norm_path_str(path)}"
        
        # 如果设置了写入后打开，则尝试打开文件
        if args.open_after_write:
            try:
                open_file_with_obsidian(path)
                result_message += " (文件已在 Obsidian 中打开)"
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                error_msg = f"无法打开文件：{str(open_error)}"
                result_message += f" ({error_msg})"
                await ctx.warning(f"写入文件成功，但打开失败：{error_msg}")
        
        return result_message
        
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

    # 处理限制逻辑
    limit = args.limit
    if limit is not None and limit > 50:
        await ctx.warning(f"限制值 {limit} 超过最大允许值 50，已自动设置为 50")
        limit = 50

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

    # 应用文件数量限制
    if limit is not None and len(files_meta) > limit:
        files_meta = files_meta[:limit]
        await ctx.warning(f"文件数量超过限制 {limit}，只显示前 {limit} 个文件")
        # 在返回结果中添加提示信息
        await ctx.info(f"注意：由于目录内容过多，只返回了前 {limit} 个文件。如需查看更多文件，请使用更小的限制值。")

    listing = DirectoryListing(
        path=_norm_path_str(dir_path),
        files=sorted(files_meta, key=lambda x: x.name.lower()),
        directories=sorted(directories, key=lambda x: x.lower())
    )

    await ctx.info(f"列出目录：{dir_path} (files={len(files_meta)}, directories={len(directories)}, limit={limit})")
    return listing

def _get_relative_path(file_path: Path) -> str:
    """获取相对于根目录的相对路径"""
    try:
        root_path = ROOT().resolve()
        file_abs_path = file_path.resolve()
        if file_abs_path == root_path:
            return file_path.name
        elif root_path in file_abs_path.parents:
            return str(file_abs_path.relative_to(root_path))
        else:
            return str(file_path)
    except Exception:
        return str(file_path)

# 布尔搜索解析器
class BooleanSearchParser:
    """解析布尔搜索表达式"""
    
    @staticmethod
    def parse_expression(expression: str, logic: str = "OR") -> List[List[str]]:
        """
        解析搜索表达式
        返回: 列表的列表，每个子列表表示一个AND组
        """
        if logic.upper() == "AND":
            # AND 逻辑：所有关键词都必须匹配
            terms = [term.strip() for term in expression.split() if term.strip()]
            return [terms] if terms else []
        else:
            # OR 逻辑：每个关键词单独匹配
            terms = [term.strip() for term in expression.split() if term.strip()]
            return [[term] for term in terms] if terms else []

def _search_in_file(file_path: Path, search_groups: List[List[str]], search_mode: str = "both") -> List[SearchResult]:
    """在单个文件中搜索，支持布尔逻辑和搜索模式"""
    results: List[SearchResult] = []
    try:
        # 根据搜索模式决定搜索范围
        if search_mode in ["both", "filename_only"]:
            # 检查文件名是否匹配
            file_name = file_path.name.lower()
            for group in search_groups:
                if all(term.lower() in file_name for term in group):
                    results.append(SearchResult(
                        file_path=_get_relative_path(file_path),
                        line_number=0,
                        content=f"文件名匹配: {file_path.name}",
                        matched_terms=group
                    ))
                    break  # 文件名匹配一个组就足够
        
        if search_mode in ["both", "content_only"]:
            # 检查文件内容
            raw = file_path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
            
            lines = text.splitlines()
            for i, line in enumerate(lines, start=1):
                line_lower = line.lower()
                
                for group in search_groups:
                    # 检查该组中的所有关键词是否都在当前行中
                    if all(term.lower() in line_lower for term in group):
                        results.append(SearchResult(
                            file_path=_get_relative_path(file_path),
                            line_number=i,
                            content=line.strip(),
                            matched_terms=group
                        ))
                        break  # 一行匹配一个组就足够
    
    except Exception:
        pass
    
    return results

@mcp.tool()
async def search_files(ctx: Context[ServerSession, None], args: SearchArgs) -> SearchResults:
    """
    搜索文件内容，支持布尔逻辑和搜索模式
    
    参数:
    - search_term: 搜索关键词，支持多关键词布尔搜索
    - directory_path: 搜索目录路径，默认为当前工作目录
    - file_pattern: 文件模式匹配，支持通配符，默认 "*.md"
    - limit: 搜索结果数量限制，默认 200，最大 5000
    - search_logic: 搜索逻辑："OR" 匹配任意关键词，"AND" 必须匹配所有关键词
    - search_mode: 搜索模式：
        - "both": 同时搜索文件名和文件内容（默认）
        - "filename_only" 或 "filename": 只搜索文件名
        - "content_only" 或 "content": 只搜索文件内容
    
    示例:
    - 搜索文件名包含 "python" 的文件: search_mode="filename", search_term="python"
    - 搜索内容包含 "MCP" 的文件: search_mode="content", search_term="MCP"
    - 同时搜索文件名和内容: search_mode="both", search_term="python MCP"
    - 布尔搜索 (AND 逻辑): search_logic="AND", search_term="python MCP"
    - 布尔搜索 (OR 逻辑): search_logic="OR", search_term="python MCP"
    """
    directory_path = args.directory_path or str(ROOT())
    dir_path = resolve_path(directory_path, must_exist=True)

    # 解析搜索表达式
    parser = BooleanSearchParser()
    search_groups = parser.parse_expression(args.search_term, args.search_logic)
    
    if not search_groups:
        await ctx.warning("搜索表达式为空，请提供有效的搜索关键词")
        return SearchResults(
            total_matches=0,
            results=[],
            limit=args.limit,
            search_logic=args.search_logic
        )

    pattern = str(dir_path / "**" / args.file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    matched_files = [p for p in matched_files if p.is_file() and _has_allowed_extension(p)]

    results: List[SearchResult] = []
    limit = max(1, min(args.limit, 5000))

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_THREADPOOL_WORKERS) as ex:
        tasks = [loop.run_in_executor(ex, _search_in_file, p, search_groups, args.search_mode) for p in matched_files]
        for fut in asyncio.as_completed(tasks):
            file_results: List[SearchResult] = await fut
            if file_results:
                # 如果添加这些结果会超过限制，只添加部分结果
                remaining_space = limit - len(results)
                if remaining_space > 0:
                    if len(file_results) <= remaining_space:
                        results.extend(file_results)
                    else:
                        results.extend(file_results[:remaining_space])
                # 如果已经达到限制，就停止处理更多文件
                if len(results) >= limit:
                    break
    
    total_matches = len(results)
    await ctx.info(f"搜索完成：在 {dir_path} 中找到 {total_matches} 个匹配（limit={limit}，逻辑：{args.search_logic}，模式：{args.search_mode}）")
    
    return SearchResults(
        total_matches=total_matches,
        results=results,
        limit=limit,
        search_logic=args.search_logic
    )

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
# 部分文件编辑工具
# -----------------------------
@mcp.tool()
async def append_to_file(ctx: Context[ServerSession, None], args: AppendFileArgs) -> str:
    """在文件末尾追加内容"""
    try:
        path = resolve_path(args.file_path, must_exist=True)
        
        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")
            
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

        # 读取现有内容
        existing_content = path.read_text(encoding="utf-8")
        
        # 追加新内容
        new_content = existing_content + args.content
        path.write_text(new_content, encoding="utf-8")
        
        result_message = f"内容已追加到文件：{_norm_path_str(path)}"
        
        # 如果设置了追加后打开，则尝试打开文件
        if args.open_after_append:
            try:
                open_file_with_obsidian(path)
                result_message += " (文件已在 Obsidian 中打开)"
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                error_msg = f"无法打开文件：{str(open_error)}"
                result_message += f" ({error_msg})"
                await ctx.warning(f"追加文件成功，但打开失败：{error_msg}")
        
        await ctx.info(f"在文件末尾追加内容：{path} (追加了 {len(args.content)} 字符)")
        return result_message
        
    except Exception as e:
        await ctx.error(f"追加文件内容失败：{str(e)}")
        raise

@mcp.tool()
async def insert_into_file(ctx: Context[ServerSession, None], args: InsertFileArgs) -> str:
    """在指定行号插入内容"""
    try:
        path = resolve_path(args.file_path, must_exist=True)
        
        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")
            
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

        # 读取现有内容
        lines = path.read_text(encoding="utf-8").splitlines()
        
        # 验证行号
        if args.line_number < 1 or args.line_number > len(lines) + 1:
            raise ValueError(f"行号超出范围：{args.line_number} (文件有 {len(lines)} 行)")
        
        # 插入新内容
        lines.insert(args.line_number - 1, args.content)
        new_content = "\n".join(lines)
        path.write_text(new_content, encoding="utf-8")
        
        result_message = f"内容已插入到文件第 {args.line_number} 行：{_norm_path_str(path)}"
        
        # 如果设置了插入后打开，则尝试打开文件
        if args.open_after_insert:
            try:
                open_file_with_obsidian(path)
                result_message += " (文件已在 Obsidian 中打开)"
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                error_msg = f"无法打开文件：{str(open_error)}"
                result_message += f" ({error_msg})"
                await ctx.warning(f"插入文件成功，但打开失败：{error_msg}")
        
        await ctx.info(f"在文件第 {args.line_number} 行插入内容：{path}")
        return result_message
        
    except Exception as e:
        await ctx.error(f"插入文件内容失败：{str(e)}")
        raise

@mcp.tool()
async def replace_in_file(ctx: Context[ServerSession, None], args: ReplaceFileArgs) -> str:
    """搜索并替换文件中的文本"""
    try:
        path = resolve_path(args.file_path, must_exist=True)
        
        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")
            
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

        # 读取现有内容
        content = path.read_text(encoding="utf-8")
        
        # 执行替换
        if args.search_text not in content:
            raise ValueError(f"未找到要替换的文本：{args.search_text}")
            
        new_content = content.replace(args.search_text, args.replace_text)
        path.write_text(new_content, encoding="utf-8")
        
        replacements = content.count(args.search_text)
        result_message = f"文本替换完成：{_norm_path_str(path)} (替换了 {replacements} 处)"
        
        # 如果设置了替换后打开，则尝试打开文件
        if args.open_after_replace:
            try:
                open_file_with_obsidian(path)
                result_message += " (文件已在 Obsidian 中打开)"
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                error_msg = f"无法打开文件：{str(open_error)}"
                result_message += f" ({error_msg})"
                await ctx.warning(f"替换文件成功，但打开失败：{error_msg}")
        
        await ctx.info(f"在文件中替换文本：{path} (替换了 {replacements} 处)")
        return result_message
        
    except Exception as e:
        await ctx.error(f"替换文件内容失败：{str(e)}")
        raise

@mcp.tool()
async def delete_from_file(ctx: Context[ServerSession, None], args: DeleteFileArgs) -> str:
    """删除指定行范围的内容"""
    try:
        path = resolve_path(args.file_path, must_exist=True)
        
        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")
            
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

        # 读取现有内容
        lines = path.read_text(encoding="utf-8").splitlines()
        
        # 验证行号范围
        if args.line_start < 1 or args.line_end > len(lines) or args.line_start > args.line_end:
            raise ValueError(f"行号范围无效：{args.line_start}-{args.line_end} (文件有 {len(lines)} 行)")
        
        # 删除指定行范围
        del lines[args.line_start - 1:args.line_end]
        new_content = "\n".join(lines)
        path.write_text(new_content, encoding="utf-8")
        
        deleted_lines = args.line_end - args.line_start + 1
        result_message = f"已删除文件第 {args.line_start}-{args.line_end} 行：{_norm_path_str(path)} (共 {deleted_lines} 行)"
        
        # 如果设置了删除后打开，则尝试打开文件
        if args.open_after_delete:
            try:
                open_file_with_obsidian(path)
                result_message += " (文件已在 Obsidian 中打开)"
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                error_msg = f"无法打开文件：{str(open_error)}"
                result_message += f" ({error_msg})"
                await ctx.warning(f"删除文件成功，但打开失败：{error_msg}")
        
        await ctx.info(f"从文件中删除行 {args.line_start}-{args.line_end}：{path}")
        return result_message
        
    except Exception as e:
        await ctx.error(f"删除文件内容失败：{str(e)}")
        raise

@mcp.tool()
async def patch_file(ctx: Context[ServerSession, None], args: PatchFileArgs) -> str:
    """应用统一差异格式的补丁"""
    try:
        path = resolve_path(args.file_path, must_exist=True)
        
        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")
            
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许写入该文件类型：{path.suffix}")

        # 读取现有内容
        original_content = path.read_text(encoding="utf-8")
        original_lines = original_content.splitlines()
        
        # 解析补丁内容
        patch_lines = args.patch_content.splitlines()
        new_lines = original_lines.copy()
        
        # 简单的补丁应用逻辑（简化版）
        # 在实际应用中，应该使用更完整的diff解析库
        line_offset = 0
        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]
            if line.startswith('@@'):
                # 解析补丁头部
                parts = line.split(' ')
                if len(parts) >= 3:
                    old_range = parts[1]
                    # 解析旧文件行范围
                    old_parts = old_range[1:].split(',')  # 去掉开头的'-'
                    if len(old_parts) == 2:
                        old_start = int(old_parts[0])
                    else:
                        old_start = int(old_parts[0])
                    
                    # 计算在new_lines中的位置
                    current_pos = old_start - 1 + line_offset
                    
                    # 应用补丁块
                    j = i + 1
                    while j < len(patch_lines) and not patch_lines[j].startswith('@@'):
                        patch_line = patch_lines[j]
                        if patch_line.startswith('-'):
                            # 删除行
                            if current_pos < len(new_lines):
                                del new_lines[current_pos]
                                line_offset -= 1
                        elif patch_line.startswith('+'):
                            # 添加行
                            new_lines.insert(current_pos, patch_line[1:])
                            current_pos += 1
                            line_offset += 1
                        else:
                            # 保留行
                            current_pos += 1
                        j += 1
                    i = j  # 跳过已处理的补丁块
                else:
                    i += 1
            else:
                i += 1
        
        # 写入修改后的内容
        new_content = "\n".join(new_lines)
        path.write_text(new_content, encoding="utf-8")
        
        result_message = f"补丁已应用到文件：{_norm_path_str(path)}"
        
        # 如果设置了应用补丁后打开，则尝试打开文件
        if args.open_after_patch:
            try:
                open_file_with_obsidian(path)
                result_message += " (文件已在 Obsidian 中打开)"
                await ctx.info(f"文件已在 Obsidian 中打开：{path}")
            except Exception as open_error:
                error_msg = f"无法打开文件：{str(open_error)}"
                result_message += f" ({error_msg})"
                await ctx.warning(f"应用补丁成功，但打开失败：{error_msg}")
        
        await ctx.info(f"应用补丁到文件：{path}")
        return result_message
        
    except Exception as e:
        await ctx.error(f"应用补丁失败：{str(e)}")
        raise

@mcp.tool()
async def open_note(ctx: Context[ServerSession, None], args: OpenNoteArgs) -> str:
    """打开笔记文件（在 Obsidian 中）"""
    try:
        path = resolve_path(args.file_path, must_exist=True)
        
        if not path.is_file():
            raise ValueError(f"路径不是文件：{path}")
            
        if not _has_allowed_extension(path):
            raise PermissionError(f"不允许打开该文件类型：{path.suffix}")

        # 尝试在 Obsidian 中打开文件
        open_file_with_obsidian(path)
        
        await ctx.info(f"文件已在 Obsidian 中打开：{path}")
        return f"文件已在 Obsidian 中打开：{_norm_path_str(path)}"
        
    except (ValueError, PermissionError) as e:
        await ctx.error(f"打开文件失败：{str(e)}")
        raise
    except Exception as e:
        await ctx.error(f"打开文件失败：{str(e)}")
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
