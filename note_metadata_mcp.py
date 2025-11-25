"""
笔记元数据 MCP 服务器
专注于笔记的标签管理和时间范围搜索功能
"""

import glob
import re
import yaml
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

# 导入配置
from config import config, ROOT

# -----------------------------
# 配置项
# -----------------------------
ALLOWED_EXTENSIONS = {".md"}
SEARCH_THREADPOOL_WORKERS = 4
SEARCH_DEFAULT_LIMIT = 100
MAX_FILE_READ_SIZE = 5 * 1024 * 1024  # 5 MB

# 搜索结果限制配置
RECENT_NOTES_MAX_LIMIT = 100
RECENT_NOTES_DEFAULT_LIMIT = 10
TAG_SEARCH_MAX_LIMIT = 100
TAG_SEARCH_DEFAULT_LIMIT = 50

# -----------------------------
# MCP 实例
# -----------------------------
mcp = FastMCP(
    "Note Metadata Manager",
    instructions="笔记元数据管理服务器，专注于标签搜索和时间范围搜索功能。",
    json_response=True
)

# -----------------------------
# 动态路径管理参数模型
# -----------------------------
class SetWorkingDirectoryArgs(BaseModel):
    path: str = Field(
        ...,
        description="要设置为工作目录的路径"
    )

# -----------------------------
# 数据模型
# -----------------------------
class TagInfo(BaseModel):
    """标签信息"""
    tag: str
    count: int
    files: List[str]

class TagSearchResult(BaseModel):
    """标签搜索结果"""
    file_path: str
    matched_tags: List[str]
    frontmatter_tags: List[str] = []
    content_tags: List[str] = []

class TagSearchResults(BaseModel):
    """标签搜索结果集合"""
    total_matches: int
    results: List[TagSearchResult]
    limit: int

class TimeRangeType(str, Enum):
    """时间范围类型"""
    CREATED = "created"
    MODIFIED = "modified"

class RecentNoteResult(BaseModel):
    """最近笔记结果"""
    file_path: str
    file_name: str
    created_time: str
    modified_time: str
    size: int
    time_type: TimeRangeType
    time_value: str

class RecentNotesResults(BaseModel):
    """最近笔记搜索结果集合"""
    total_matches: int
    results: List[RecentNoteResult]
    time_range: str
    time_type: TimeRangeType

# 请求参数模型
class ListTagsArgs(BaseModel):
    """列出所有标签参数"""
    
    directory_path: Optional[str] = Field(
        None,
        description="搜索目录路径，默认为当前工作目录"
    )
    
    file_pattern: str = Field(
        "*.md",
        description="文件模式匹配，支持通配符"
    )
    
    min_count: int = Field(
        1,
        description="标签最小出现次数",
        ge=1
    )

class SearchNotesByTagsArgs(BaseModel):
    """按标签搜索笔记参数"""
    
    tags: List[str] = Field(
        ...,
        description="要搜索的标签列表"
    )
    
    directory_path: Optional[str] = Field(
        None,
        description="搜索目录路径，默认为当前工作目录"
    )
    
    file_pattern: str = Field(
        "*.md",
        description="文件模式匹配，支持通配符"
    )
    
    search_logic: str = Field(
        "OR",
        description="搜索逻辑：'OR' 匹配任意标签，'AND' 必须匹配所有标签"
    )
    
    limit: int = Field(
        TAG_SEARCH_DEFAULT_LIMIT,
        description="搜索结果数量限制，最大100，默认50。注意：如果结果超过限制，返回的并非全部结果",
        ge=1,
        le=TAG_SEARCH_MAX_LIMIT
    )
    
    @field_validator("search_logic")
    def validate_search_logic(cls, v: str) -> str:
        """验证搜索逻辑参数"""
        if v.upper() not in ["OR", "AND"]:
            raise ValueError("search_logic 必须是 'OR' 或 'AND'")
        return v.upper()

class SearchRecentNotesArgs(BaseModel):
    """搜索最近笔记参数"""
    
    time_range: str = Field(
        ...,
        description="时间范围，例如：'7d' (7天), '1w' (1周), '30d' (30天), '1m' (1月)"
    )
    
    directory_path: Optional[str] = Field(
        None,
        description="搜索目录路径，默认为当前工作目录"
    )
    
    file_pattern: str = Field(
        "*.md",
        description="文件模式匹配，支持通配符"
    )
    
    time_type: TimeRangeType = Field(
        TimeRangeType.MODIFIED,
        description="时间类型：'created' 创建时间，'modified' 修改时间"
    )
    
    limit: int = Field(
        RECENT_NOTES_DEFAULT_LIMIT,
        description="搜索结果数量限制，最大100，默认10。注意：如果结果超过限制，返回的并非全部结果",
        ge=1,
        le=RECENT_NOTES_MAX_LIMIT
    )
    
    @field_validator("time_range")
    def validate_time_range(cls, v: str) -> str:
        """验证时间范围格式"""
        pattern = r'^(\d+)([dwm])$'
        if not re.match(pattern, v.lower()):
            raise ValueError("time_range 格式错误，应为数字+单位，如 '7d', '1w', '1m'")
        return v.lower()

# -----------------------------
# 辅助函数
# -----------------------------
def _now_iso(ts: Optional[float] = None) -> str:
    """获取ISO格式的时间字符串"""
    if ts is None:
        dt = datetime.now(timezone.utc)
    else:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat()

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

def _has_allowed_extension(path: Path) -> bool:
    """检查文件扩展名是否允许"""
    if path.suffix == "":
        return True
    return path.suffix.lower() in ALLOWED_EXTENSIONS

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

def parse_time_range(time_range: str) -> timedelta:
    """解析时间范围字符串为timedelta"""
    match = re.match(r'^(\d+)([dwm])$', time_range.lower())
    if not match:
        raise ValueError(f"无效的时间范围格式: {time_range}")
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    elif unit == 'm':
        return timedelta(days=value * 30)  # 近似月份
    else:
        raise ValueError(f"未知的时间单位: {unit}")

def extract_tags_from_content(content: str) -> Set[str]:
    """从内容中提取标签"""
    # 匹配 #标签 格式，支持中英文
    # 排除纯数字标签、URL片段、标题格式、颜色代码等误识别情况
    tag_pattern = r'#([\w\u4e00-\u9fa5][\w\u4e00-\u9fa5\-_]*)'
    matches = re.findall(tag_pattern, content)
    
    # 过滤误识别的情况
    filtered_tags = set()
    for tag in matches:
        # 排除纯数字标签（如 #36, #37）
        if tag.isdigit():
            continue
            
        # 排除颜色代码（6位十六进制，如 #ff3b3b）
        if re.match(r'^[a-fA-F0-9]{6}$', tag):
            continue
            
        # 排除URL锚点（包含特殊字符如 +, -, _ 等组合）
        if re.match(r'^[A-Z][a-zA-Z\+]+', tag):
            continue
            
        filtered_tags.add(tag)
    
    return filtered_tags

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """解析YAML frontmatter"""
    lines = content.splitlines()
    
    if not lines or lines[0].strip() != '---':
        return {}, content
    
    frontmatter_lines = []
    body_lines = []
    in_frontmatter = False
    frontmatter_end = False
    
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == '---':
            in_frontmatter = True
            continue
        
        if in_frontmatter and not frontmatter_end:
            if line.strip() == '---':
                frontmatter_end = True
                continue
            frontmatter_lines.append(line)
        else:
            body_lines.append(line)
    
    frontmatter_content = '\n'.join(frontmatter_lines)
    body_content = '\n'.join(body_lines)
    
    try:
        frontmatter = yaml.safe_load(frontmatter_content) or {}
        return frontmatter, body_content
    except yaml.YAMLError:
        return {}, content

def extract_tags_from_frontmatter(frontmatter: Dict[str, Any]) -> Set[str]:
    """从frontmatter中提取标签"""
    tags = set()
    
    # 支持多种标签字段名
    tag_fields = ['tags', 'tag', 'labels', 'label']
    
    for field in tag_fields:
        if field in frontmatter:
            tag_value = frontmatter[field]
            if isinstance(tag_value, list):
                tags.update(str(tag).strip('#') for tag in tag_value)
            elif isinstance(tag_value, str):
                # 处理逗号分隔的标签
                tag_list = [tag.strip().strip('#') for tag in tag_value.split(',')]
                tags.update(tag_list)
    
    return tags

def _search_tags_in_file(file_path: Path) -> Tuple[Set[str], Set[str], Set[str]]:
    """在单个文件中搜索标签"""
    content_tags = set()
    frontmatter_tags = set()
    all_tags = set()
    
    try:
        if not file_path.is_file() or not _has_allowed_extension(file_path):
            return content_tags, frontmatter_tags, all_tags
        
        size = file_path.stat().st_size
        if size > MAX_FILE_READ_SIZE:
            return content_tags, frontmatter_tags, all_tags
        
        raw = file_path.read_bytes()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("utf-8", errors="replace")
        
        # 解析frontmatter和内容
        frontmatter, body_content = parse_frontmatter(content)
        
        # 从frontmatter提取标签
        frontmatter_tags = extract_tags_from_frontmatter(frontmatter)
        
        # 从内容中提取标签
        content_tags = extract_tags_from_content(body_content)
        
        # 合并所有标签
        all_tags = frontmatter_tags.union(content_tags)
        
    except Exception:
        pass
    
    return content_tags, frontmatter_tags, all_tags

def _search_recent_files_in_directory(directory_path: Path, file_pattern: str, 
                                    time_delta: timedelta, time_type: TimeRangeType) -> List[Path]:
    """在目录中搜索最近的文件"""
    pattern = str(directory_path / "**" / file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    
    # 过滤文件
    recent_files = []
    cutoff_time = datetime.now(timezone.utc) - time_delta
    
    for file_path in matched_files:
        if not file_path.is_file() or not _has_allowed_extension(file_path):
            continue
        
        try:
            stat = file_path.stat()
            if time_type == TimeRangeType.CREATED:
                file_time = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
            else:  # MODIFIED
                file_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            
            if file_time >= cutoff_time:
                recent_files.append(file_path)
        except Exception:
            continue
    
    return recent_files

# -----------------------------
# 工具实现
# -----------------------------

# -----------------------------
# 动态路径管理工具
# -----------------------------
@mcp.tool()
def set_working_directory(ctx: Context[ServerSession, None], args: SetWorkingDirectoryArgs) -> str:
    """设置当前工作目录"""
    try:
        new_root = config.set_root(args.path)
        ctx.info(f"工作目录已设置为：{new_root}")
        return f"工作目录已设置为：{new_root}"
    except Exception as e:
        ctx.error(f"设置工作目录失败：{str(e)}")
        raise

@mcp.tool()
def get_working_directory(ctx: Context[ServerSession, None]) -> Dict[str, str]:
    """获取当前工作目录信息"""
    current = str(config.get_root())
    ctx.info(f"当前工作目录：{current}")
    return {
        "current_directory": current,
        "is_dynamic": "true"
    }

@mcp.tool()
def reset_working_directory(ctx: Context[ServerSession, None]) -> str:
    """重置工作目录到默认"""
    try:
        default_root = config.reset_to_default()
        ctx.info(f"工作目录已重置为默认：{default_root}")
        return f"工作目录已重置为默认：{default_root}"
    except Exception as e:
        ctx.error(f"重置工作目录失败：{str(e)}")
        raise

# -----------------------------
# 主要工具实现（完全同步版本）
# -----------------------------
@mcp.tool()
def list_tags(ctx: Context[ServerSession, None], args: ListTagsArgs) -> Dict[str, Any]:
    """
    列出所有标签
    
    搜索所有包含"#标签"格式的标签，支持文本文件和YAML frontmatter。
    注意：此函数返回所有标签，不受数量限制。
    
    参数:
    - directory_path: 搜索目录路径，默认为当前工作目录
    - file_pattern: 文件模式匹配，支持通配符，默认 "*.md"
    - min_count: 标签最小出现次数，默认 1
    
    返回: 包含所有标签及其统计信息的字典
    """
    directory_path = args.directory_path or str(ROOT())
    dir_path = resolve_path(directory_path, must_exist=True)

    pattern = str(dir_path / "**" / args.file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    matched_files = [p for p in matched_files if p.is_file() and _has_allowed_extension(p)]

    tag_counter: Dict[str, int] = {}

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_THREADPOOL_WORKERS) as ex:
        results = list(ex.map(_search_tags_in_file, matched_files))

    for idx, file_result in enumerate(results):
        content_tags, frontmatter_tags, all_tags = file_result
        for tag in all_tags:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1

    # 过滤和排序标签
    filtered_tags = {tag: count for tag, count in tag_counter.items() if count >= args.min_count}
    sorted_tags = sorted(filtered_tags.items(), key=lambda x: (-x[1], x[0]))

    tags_info = []
    for tag, count in sorted_tags:
        tag_info = {"name": tag, "count": count}
        tags_info.append(tag_info)

    # 使用同步上下文记录日志
    ctx.info(f"标签搜索完成：在 {dir_path} 中找到 {len(tags_info)} 个标签（min_count={args.min_count}）")
    return {
        "tags": tags_info,
        "total_count": len(tags_info)
    }


@mcp.tool()
def search_notes_by_tags(ctx: Context[ServerSession, None], args: SearchNotesByTagsArgs) -> TagSearchResults:
    """
    搜索包含特定标签的笔记
    
    支持单个标签搜索、多个标签的AND/OR逻辑搜索。
    
    参数:
    - tags: 要搜索的标签列表
    - directory_path: 搜索目录路径，默认为当前工作目录
    - file_pattern: 文件模式匹配，支持通配符，默认 "*.md"
    - search_logic: 搜索逻辑："OR" 匹配任意标签，"AND" 必须匹配所有标签
    - limit: 搜索结果数量限制，默认 100，最大 1000
    
    返回: 包含匹配笔记的搜索结果
    """
    directory_path = args.directory_path or str(ROOT())
    dir_path = resolve_path(directory_path, must_exist=True)

    if not args.tags:
        ctx.warning("标签列表为空，请提供有效的标签")
        return TagSearchResults(total_matches=0, results=[], limit=args.limit)

    pattern = str(dir_path / "**" / args.file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    matched_files = [p for p in matched_files if p.is_file() and _has_allowed_extension(p)]

    results: List[TagSearchResult] = []
    limit = max(1, min(args.limit, TAG_SEARCH_MAX_LIMIT))

    with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_THREADPOOL_WORKERS) as ex:
        tag_results = list(ex.map(_search_tags_in_file, matched_files))

    for idx, file_result in enumerate(tag_results):
        content_tags, frontmatter_tags, all_tags = file_result
        file_path = matched_files[idx]

        matched = False
        matched_tags = []

        if args.search_logic == "AND":
            if all(tag in all_tags for tag in args.tags):
                matched = True
                matched_tags = args.tags
        else:  # OR
            found_tags = [tag for tag in args.tags if tag in all_tags]
            if found_tags:
                matched = True
                matched_tags = found_tags

        if matched:
            result = TagSearchResult(
                file_path=_get_relative_path(file_path),
                matched_tags=matched_tags,
                frontmatter_tags=list(frontmatter_tags),
                content_tags=list(content_tags)
            )
            results.append(result)
            if len(results) >= limit:
                break

    total_matches = len(results)
    ctx.info(f"标签搜索完成：在 {dir_path} 中找到 {total_matches} 个匹配（逻辑：{args.search_logic}，限制：{args.limit}）")
    return TagSearchResults(total_matches=total_matches, results=results, limit=args.limit)


@mcp.tool()
def search_recent_notes(ctx: Context[ServerSession, None], args: SearchRecentNotesArgs) -> RecentNotesResults:
    """
    搜索最近特定时间范围内改动过或创建过的笔记
    
    根据文件元数据搜索最近特定时间范围内的笔记。
    
    参数:
    - time_range: 时间范围，例如：'7d' (7天), '1w' (1周), '30d' (30天), '1m' (1月)
    - directory_path: 搜索目录路径，默认为当前工作目录
    - file_pattern: 文件模式匹配，支持通配符，默认 "*.md"
    - time_type: 时间类型：'created' 创建时间，'modified' 修改时间
    - limit: 搜索结果数量限制，默认 100，最大 1000
    
    返回: 包含最近笔记的搜索结果
    """
    directory_path = args.directory_path or str(ROOT())
    dir_path = resolve_path(directory_path, must_exist=True)

    time_delta = parse_time_range(args.time_range)
    recent_files = _search_recent_files_in_directory(dir_path, args.file_pattern, time_delta, args.time_type)

    results: List[RecentNoteResult] = []
    limit = max(1, min(args.limit, RECENT_NOTES_MAX_LIMIT))

    for file_path in recent_files[:limit]:
        try:
            stat = file_path.stat()
            if args.time_type == TimeRangeType.CREATED:
                time_value = _now_iso(stat.st_ctime)
            else:
                time_value = _now_iso(stat.st_mtime)

            result = RecentNoteResult(
                file_path=_get_relative_path(file_path),
                file_name=file_path.name,
                created_time=_now_iso(stat.st_ctime),
                modified_time=_now_iso(stat.st_mtime),
                size=stat.st_size,
                time_type=args.time_type,
                time_value=time_value
            )
            results.append(result)
        except Exception:
            continue

    results.sort(key=lambda x: x.time_value, reverse=True)
    total_matches = len(results)
    ctx.info(f"最近笔记搜索完成：在 {dir_path} 中找到 {total_matches} 个匹配（时间范围：{args.time_range}，类型：{args.time_type}）")
    return RecentNotesResults(total_matches=total_matches, results=results, time_range=args.time_range, time_type=args.time_type)


# -----------------------------
# 启动
# -----------------------------
if __name__ == "__main__":
    print("启动笔记元数据 MCP 服务器...")
    print(f"根目录：{ROOT()}")
    print("支持环境变量 MCP_FILESYSTEM_ROOT 设置默认目录")
    print("支持动态路径管理工具：set_working_directory, get_working_directory, reset_working_directory")
    print("支持标签和时间搜索工具：list_tags, search_notes_by_tags, search_recent_notes")
    print("按 Ctrl+C 停止服务器")
    mcp.run(transport="stdio")
