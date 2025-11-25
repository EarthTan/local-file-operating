#!/usr/bin/env python3
"""
测试搜索模式功能
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from local_filesystem_mcp_simple import BooleanSearchParser, SearchArgs, SearchResult

def test_search_modes():
    """测试搜索模式功能"""
    print("=== 测试搜索模式功能 ===")
    
    parser = BooleanSearchParser()
    
    # 测试搜索模式逻辑
    print("\n=== 测试搜索模式逻辑 ===")
    
    # 测试 both 模式
    print("\n--- both 模式测试 ---")
    search_groups = parser.parse_expression("python", "OR")
    print(f"搜索组: {search_groups}")
    print("both 模式应该搜索文件名和文件内容")
    
    # 测试 filename_only 模式
    print("\n--- filename_only 模式测试 ---")
    print("filename_only 模式应该只搜索文件名")
    
    # 测试 content_only 模式
    print("\n--- content_only 模式测试 ---")
    print("content_only 模式应该只搜索文件内容")
    
    # 测试 SearchArgs 模型
    print("\n=== 测试 SearchArgs 模型 ===")
    
    # both 模式
    args_both = SearchArgs(
        search_term="python MCP",
        directory_path=".",
        file_pattern="*.md",
        limit=10,
        search_logic="OR",
        search_mode="both"
    )
    print(f"both 模式参数: search_mode={args_both.search_mode}")
    
    # filename_only 模式
    args_filename = SearchArgs(
        search_term="python",
        directory_path=".",
        file_pattern="*.md",
        limit=5,
        search_logic="OR",
        search_mode="filename_only"
    )
    print(f"filename_only 模式参数: search_mode={args_filename.search_mode}")
    
    # content_only 模式
    args_content = SearchArgs(
        search_term="MCP",
        directory_path=".",
        file_pattern="*.md",
        limit=5,
        search_logic="OR",
        search_mode="content_only"
    )
    print(f"content_only 模式参数: search_mode={args_content.search_mode}")
    
    # 默认模式
    args_default = SearchArgs(
        search_term="test",
        directory_path=".",
        file_pattern="*.md",
        limit=5,
        search_logic="OR"
    )
    print(f"默认模式参数: search_mode={args_default.search_mode} (应该为 'both')")
    
    # 测试搜索模式验证
    print("\n=== 搜索模式验证 ===")
    valid_modes = ["both", "filename_only", "content_only"]
    for mode in valid_modes:
        try:
            args = SearchArgs(
                search_term="test",
                search_mode=mode
            )
            print(f"✓ 有效模式: {mode}")
        except Exception as e:
            print(f"✗ 无效模式: {mode} - {e}")
    
    print("\n=== 搜索模式使用示例 ===")
    print("1. 搜索文件名包含 'python' 的文件:")
    print("   search_mode='filename_only', search_term='python'")
    print("")
    print("2. 搜索内容包含 'MCP' 的文件:")
    print("   search_mode='content_only', search_term='MCP'")
    print("")
    print("3. 同时搜索文件名和内容:")
    print("   search_mode='both', search_term='python MCP'")
    print("")
    print("4. 默认行为（向后兼容）:")
    print("   search_mode='both' (默认值)")

if __name__ == "__main__":
    test_search_modes()
    input("\n按回车键退出...")  # 防止测试窗口立即关闭
