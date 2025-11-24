#!/usr/bin/env python3
"""
测试搜索功能优化后的效果
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from local_filesystem_mcp_simple import _search_in_file, _get_relative_path
from pathlib import Path

def test_search_functionality():
    """测试搜索功能"""
    print("=== 测试搜索功能优化 ===")
    
    # 测试相对路径函数
    test_file = Path("test_search.md")
    relative_path = _get_relative_path(test_file)
    print(f"相对路径测试: {relative_path}")
    
    # 测试单关键词搜索
    print("\n=== 测试单关键词搜索 ===")
    result = _search_in_file(test_file, ["MCP"])
    if result:
        print(f"找到匹配: {result.file_path} (行号: {result.line_number})")
        print(f"内容: {result.content}")
    else:
        print("未找到匹配")
    
    # 测试多关键词 OR 搜索
    print("\n=== 测试多关键词 OR 搜索 ===")
    result = _search_in_file(test_file, ["MCP", "文件系统", "搜索"])
    if result:
        print(f"找到匹配: {result.file_path} (行号: {result.line_number})")
        print(f"内容: {result.content}")
    else:
        print("未找到匹配")
    
    # 测试文件名搜索
    print("\n=== 测试文件名搜索 ===")
    result = _search_in_file(test_file, ["search"])
    if result:
        print(f"找到匹配: {result.file_path} (行号: {result.line_number})")
        print(f"内容: {result.content}")
    else:
        print("未找到匹配")
    
    # 测试不存在的关键词
    print("\n=== 测试不存在的关键词 ===")
    result = _search_in_file(test_file, ["不存在"])
    if result:
        print(f"找到匹配: {result.file_path} (行号: {result.line_number})")
        print(f"内容: {result.content}")
    else:
        print("未找到匹配 - 正确")

if __name__ == "__main__":
    test_search_functionality()
