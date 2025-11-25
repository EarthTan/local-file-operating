"""
重构后的搜索工具代码 - 支持布尔搜索
"""

from pathlib import Path
from typing import List, Optional, Union
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
    matched_terms: List[str]

# 请求参数模型
class SearchArgs(BaseModel):
    search_term: str
    directory_path: Optional[str] = None
    file_pattern: str = "*.md"
    limit: int = SEARCH_DEFAULT_LIMIT
    search_logic: str = "OR"  # OR 或 AND

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

# 核心搜索函数
def _search_in_file(file_path: Path, search_groups: List[List[str]]) -> List[SearchResult]:
    """在单个文件中搜索，支持布尔逻辑"""
    results: List[SearchResult] = []
    try:
        # 检查文件名是否匹配
        file_name = file_path.name.lower()
        for group in search_groups:
            if all(term.lower() in file_name for term in group):
                results.append(SearchResult(
                    file_path=str(file_path),
                    line_number=0,
                    content=f"文件名匹配: {file_path.name}",
                    matched_terms=group
                ))
                break  # 文件名匹配一个组就足够
        
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
                        file_path=str(file_path),
                        line_number=i,
                        content=line.strip(),
                        matched_terms=group
                    ))
                    break  # 一行匹配一个组就足够
    
    except Exception:
        pass
    
    return results

# 主搜索工具函数
async def search_files(args: SearchArgs) -> List[SearchResult]:
    """搜索文件内容，支持布尔逻辑"""
    directory_path = args.directory_path or "."
    dir_path = Path(directory_path).resolve()
    
    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在：{dir_path}")

    # 解析搜索表达式
    parser = BooleanSearchParser()
    search_groups = parser.parse_expression(args.search_term, args.search_logic)
    
    if not search_groups:
        return []

    pattern = str(dir_path / "**" / args.file_pattern)
    matched_files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    matched_files = [p for p in matched_files if p.is_file()]

    results: List[SearchResult] = []
    limit = max(1, min(args.limit, 5000))

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_THREADPOOL_WORKERS) as ex:
        tasks = [loop.run_in_executor(ex, _search_in_file, p, search_groups) for p in matched_files]
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

    print(f"搜索完成：在 {dir_path} 中找到 {len(results)} 个匹配（limit={limit}，逻辑：{args.search_logic}）")
    return results

# 使用示例
if __name__ == "__main__":
    async def test_search():
        """测试搜索功能"""
        # 测试 OR 逻辑
        args_or = SearchArgs(
            search_term="python MCP 文件系统",
            directory_path=".",
            file_pattern="*.md",
            limit=20,
            search_logic="OR"
        )
        results_or = await search_files(args_or)
        
        print(f"OR 逻辑找到 {len(results_or)} 个匹配结果:")
        for i, result in enumerate(results_or, 1):
            print(f"  {i}. 文件: {result.file_path}")
            print(f"     行号: {result.line_number}")
            print(f"     内容: {result.content}")
            print(f"     匹配词: {result.matched_terms}")
            print()
        
        # 测试 AND 逻辑
        args_and = SearchArgs(
            search_term="python MCP",
            directory_path=".",
            file_pattern="*.md",
            limit=20,
            search_logic="AND"
        )
        results_and = await search_files(args_and)
        
        print(f"AND 逻辑找到 {len(results_and)} 个匹配结果:")
        for i, result in enumerate(results_and, 1):
            print(f"  {i}. 文件: {result.file_path}")
            print(f"     行号: {result.line_number}")
            print(f"     内容: {result.content}")
            print(f"     匹配词: {result.matched_terms}")
            print()
    
    # 运行测试
    asyncio.run(test_search())
