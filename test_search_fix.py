#!/usr/bin/env python3
"""
测试搜索功能修复
"""

import sys
import os
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入搜索函数
from local_filesystem_mcp_simple import _search_in_file, SearchResult

def test_search_function():
    """测试搜索功能"""
    print("测试搜索功能修复...")
    
    # 创建测试文件路径
    test_file = Path("test_search.md")
    
    if not test_file.exists():
        print(f"测试文件 {test_file} 不存在")
        return
    
    # 测试搜索多个关键词
    search_terms = ["python", "MCP", "文件系统"]
    print(f"搜索关键词: {search_terms}")
    
    # 执行搜索
    results = _search_in_file(test_file, search_terms)
    
    print(f"找到 {len(results)} 个匹配结果:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. 文件: {result.file_path}")
        print(f"     行号: {result.line_number}")
        print(f"     内容: {result.content}")
        print()
    
    # 验证结果
    if len(results) > 1:
        print("✅ 成功：搜索功能现在可以返回多个结果了！")
        print(f"   找到了 {len(results)} 个匹配项")
    else:
        print("❌ 失败：搜索功能仍然只返回一个结果")
    
    return results

if __name__ == "__main__":
    test_search_function()
