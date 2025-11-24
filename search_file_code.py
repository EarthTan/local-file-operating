"""
从 local_filesystem_mcp_simple.py 中提取的 search_file 工具相关代码
"""

from pathlib import Path
from typing import List, Optional
import glob
import asyncio
import concurrent.futures
from pydantic import BaseModel

# 配置项
SEARCH_THREADPOOL_WORKERS = 8
SEARCH_DEFAULT_LIMIT = 200

# 数据模型
class SearchResult(BaseModel):
    file_path: str
    line_number: int
    content: str

# 请求参数模型
class SearchArgs(BaseModel):
    search_term: str
    directory_path: Optional[str] = None
    file_pattern: str = "*.md"
    limit: int = SEARCH_DEFAULT_LIMIT

# 辅助函数
def _get_relative_path(file_path: Path) -> str:
    """获取相对于根目录的相对路径"""
    try:
        root_path = Path(".").resolve()  # 简化版本，实际使用 ROOT()
        file_abs_path = file_path.resolve()
        if file_abs_path == root_path:
            return file_path.name
        elif root_path in file_abs_path.parents:
            return str(file_abs_path.relative_to(root_path))
        else:
            return str(file_path)
    except Exception:
        return str(file_path)

def _has_allowed_extension(path: Path) -> bool:
    """检查文件扩展名是否允许"""
    ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
    if path.suffix == "":
        return True
    return path.suffix.lower() in ALLOWED_EXTENSIONS

def resolve_path(input_path: str, must_exist: bool = False) -> Path:
    """解析路径（简化版本）"""
    p = Path(input_path)
    if not p.is_absolute():
        p = Path(".") / p  # 简化版本，实际使用 ROOT()
    p = p.resolve()
    
    if must_exist and not p.exists():
        raise FileNotFoundError(f"路径不存在：{p}")
    
    return p

# 核心搜索函数
def _search_in_file(file_path: Path, search_terms: List[str]) -> List[SearchResult]:
    """在单个文件中搜索，返回所有匹配结果"""
    results: List[SearchResult] = []
    try:
        # 首先检查文件名是否匹配
        file_name = file_path.name.lower()
        for term in search_terms:
            if term.lower() in file_name:
                results.append(SearchResult(
                    file_path=_get_relative_path(file_path),
                    line_number=0,
                    content=f"文件名匹配: {file_path.name}"
                ))
        
        # 然后检查文件内容
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            line_lower = line.lower()
            for term in search_terms:
                if term.lower() in line_lower:
                    results.append(SearchResult(
                        file_path=_get_relative_path(file_path),
                        line_number=i,
                        content=line.strip()
                    ))
    except Exception:
        pass
    return results

# 主搜索工具函数
async def search_files(args: SearchArgs) -> List[SearchResult]:
    """搜索文件内容"""
    directory_path = args.directory_path or "."
    dir_path = resolve_path(directory_path, must_exist=True)

    # 解析多关键词 OR 搜索（使用 | 分隔符）
    search_terms = [term.strip() for term in args.search_term.split('|') if term.strip()]
    if not search_terms:
        search_terms = [args.search_term]

    pattern = str(dir_path / "**" / args.file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    matched_files = [p for p in matched_files if p.is_file() and _has_allowed_extension(p)]

    results: List[SearchResult] = []
    limit = max(1, min(args.limit, 5000))

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_THREADPOOL_WORKERS) as ex:
        tasks = [loop.run_in_executor(ex, _search_in_file, p, search_terms) for p in matched_files]
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

    print(f"搜索完成：在 {dir_path} 中找到 {len(results)} 个匹配（limit={limit}，关键词：{search_terms}）")
    return results

# 使用示例
if __name__ == "__main__":
    async def test_search():
        """测试搜索功能"""
        args = SearchArgs(
            search_term="python|MCP|文件系统",
            directory_path=".",
            file_pattern="*.md",
            limit=20
        )
        results = await search_files(args)
        
        print(f"找到 {len(results)} 个匹配结果:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. 文件: {result.file_path}")
            print(f"     行号: {result.line_number}")
            print(f"     内容: {result.content}")
            print()
    
    # 运行测试
    asyncio.run(test_search())
