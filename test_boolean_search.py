#!/usr/bin/env python3
"""
测试布尔搜索功能
"""

import sys
import os
import asyncio

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from local_filesystem_mcp_simple import BooleanSearchParser, SearchArgs, search_files

async def test_boolean_search():
    """测试布尔搜索功能"""
    print("=== 测试布尔搜索功能 ===")
    
    # 测试布尔搜索解析器
    parser = BooleanSearchParser()
    
    print("\n=== 测试 OR 逻辑解析 ===")
    or_groups = parser.parse_expression("python MCP 文件系统", "OR")
    print(f"OR 逻辑解析结果: {or_groups}")
    
    print("\n=== 测试 AND 逻辑解析 ===")
    and_groups = parser.parse_expression("python MCP", "AND")
    print(f"AND 逻辑解析结果: {and_groups}")
    
    print("\n=== 测试空表达式 ===")
    empty_groups = parser.parse_expression("", "OR")
    print(f"空表达式解析结果: {empty_groups}")
    
    # 测试实际搜索功能
    print("\n=== 测试实际搜索功能 ===")
    
    # 测试 OR 逻辑搜索
    print("\n--- OR 逻辑搜索 ---")
    args_or = SearchArgs(
        search_term="python MCP",
        directory_path=".",
        file_pattern="*.md",
        limit=10,
        search_logic="OR"
    )
    
    try:
        results_or = await search_files(None, args_or)
        print(f"OR 逻辑找到 {results_or.total_matches} 个匹配结果:")
        for i, result in enumerate(results_or.results, 1):
            print(f"  {i}. 文件: {result.file_path}")
            print(f"     行号: {result.line_number}")
            print(f"     内容: {result.content}")
            print(f"     匹配词: {result.matched_terms}")
            print()
    except Exception as e:
        print(f"OR 逻辑搜索失败: {e}")
    
    # 测试 AND 逻辑搜索
    print("\n--- AND 逻辑搜索 ---")
    args_and = SearchArgs(
        search_term="python MCP",
        directory_path=".",
        file_pattern="*.md",
        limit=10,
        search_logic="AND"
    )
    
    try:
        results_and = await search_files(None, args_and)
        print(f"AND 逻辑找到 {results_and.total_matches} 个匹配结果:")
        for i, result in enumerate(results_and.results, 1):
            print(f"  {i}. 文件: {result.file_path}")
            print(f"     行号: {result.line_number}")
            print(f"     内容: {result.content}")
            print(f"     匹配词: {result.matched_terms}")
            print()
    except Exception as e:
        print(f"AND 逻辑搜索失败: {e}")
    
    # 测试单关键词搜索
    print("\n--- 单关键词搜索 ---")
    args_single = SearchArgs(
        search_term="python",
        directory_path=".",
        file_pattern="*.md",
        limit=5,
        search_logic="OR"
    )
    
    try:
        results_single = await search_files(None, args_single)
        print(f"单关键词找到 {results_single.total_matches} 个匹配结果:")
        for i, result in enumerate(results_single.results, 1):
            print(f"  {i}. 文件: {result.file_path}")
            print(f"     行号: {result.line_number}")
            print(f"     内容: {result.content}")
            print(f"     匹配词: {result.matched_terms}")
            print()
    except Exception as e:
        print(f"单关键词搜索失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_boolean_search())
    input("测试完成，按回车键退出...")
