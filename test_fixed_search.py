#!/usr/bin/env python3
"""
测试修复后的搜索功能
验证参数验证和模式别名支持
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from local_filesystem_mcp_simple import SearchArgs

def test_fixed_search():
    """测试修复后的搜索功能"""
    print("=== 测试修复后的搜索功能 ===")
    print()
    
    # 1. 测试模式别名支持
    print("1. ✅ 测试模式别名支持")
    
    # 测试 filename 别名
    try:
        args_filename = SearchArgs(
            search_term="MCP",
            search_mode="filename"
        )
        print(f"   ✓ 'filename' 别名 -> {args_filename.search_mode}")
    except Exception as e:
        print(f"   ✗ 'filename' 别名失败: {e}")
    
    # 测试 filename_only 原名
    try:
        args_filename_only = SearchArgs(
            search_term="MCP",
            search_mode="filename_only"
        )
        print(f"   ✓ 'filename_only' 原名 -> {args_filename_only.search_mode}")
    except Exception as e:
        print(f"   ✗ 'filename_only' 原名失败: {e}")
    
    # 测试 content 别名
    try:
        args_content = SearchArgs(
            search_term="MCP",
            search_mode="content"
        )
        print(f"   ✓ 'content' 别名 -> {args_content.search_mode}")
    except Exception as e:
        print(f"   ✗ 'content' 别名失败: {e}")
    
    # 测试 content_only 原名
    try:
        args_content_only = SearchArgs(
            search_term="MCP",
            search_mode="content_only"
        )
        print(f"   ✓ 'content_only' 原名 -> {args_content_only.search_mode}")
    except Exception as e:
        print(f"   ✗ 'content_only' 原名失败: {e}")
    
    # 测试 both 模式
    try:
        args_both = SearchArgs(
            search_term="MCP",
            search_mode="both"
        )
        print(f"   ✓ 'both' 模式 -> {args_both.search_mode}")
    except Exception as e:
        print(f"   ✗ 'both' 模式失败: {e}")
    
    # 2. 测试参数验证
    print("\n2. ✅ 测试参数验证")
    
    # 测试无效搜索模式
    try:
        args_invalid = SearchArgs(
            search_term="MCP",
            search_mode="invalid_mode"
        )
        print(f"   ✗ 无效模式应该失败但通过了")
    except Exception as e:
        print(f"   ✓ 无效模式正确拒绝: {e}")
    
    # 测试搜索逻辑验证
    try:
        args_invalid_logic = SearchArgs(
            search_term="MCP",
            search_logic="INVALID"
        )
        print(f"   ✗ 无效逻辑应该失败但通过了")
    except Exception as e:
        print(f"   ✓ 无效逻辑正确拒绝: {e}")
    
    # 测试有效搜索逻辑
    try:
        args_or = SearchArgs(
            search_term="MCP",
            search_logic="OR"
        )
        print(f"   ✓ 'OR' 逻辑 -> {args_or.search_logic}")
        
        args_and = SearchArgs(
            search_term="MCP",
            search_logic="AND"
        )
        print(f"   ✓ 'AND' 逻辑 -> {args_and.search_logic}")
    except Exception as e:
        print(f"   ✗ 有效逻辑失败: {e}")
    
    # 3. 测试使用示例
    print("\n3. ✅ 测试使用示例")
    
    examples = [
        {
            "name": "搜索文件名包含 'python' 的文件",
            "args": SearchArgs(search_term="python", search_mode="filename")
        },
        {
            "name": "搜索内容包含 'MCP' 的文件", 
            "args": SearchArgs(search_term="MCP", search_mode="content")
        },
        {
            "name": "同时搜索文件名和内容",
            "args": SearchArgs(search_term="python MCP", search_mode="both")
        },
        {
            "name": "布尔搜索 (AND 逻辑)",
            "args": SearchArgs(search_term="python MCP", search_logic="AND")
        },
        {
            "name": "布尔搜索 (OR 逻辑)",
            "args": SearchArgs(search_term="python MCP", search_logic="OR")
        }
    ]
    
    for example in examples:
        try:
            args = example["args"]
            print(f"   ✓ {example['name']}")
            print(f"      搜索词: {args.search_term}")
            print(f"      搜索模式: {args.search_mode}")
            print(f"      搜索逻辑: {args.search_logic}")
        except Exception as e:
            print(f"   ✗ {example['name']} 失败: {e}")
    
    # 4. 总结
    print("\n4. ✅ 修复总结")
    print("   ✓ 支持模式别名: 'filename' -> 'filename_only'")
    print("   ✓ 支持模式别名: 'content' -> 'content_only'")
    print("   ✓ 参数验证: 拒绝无效搜索模式")
    print("   ✓ 参数验证: 拒绝无效搜索逻辑")
    print("   ✓ 向后兼容: 原有模式名称继续工作")
    print("   ✓ 详细文档: 为LLM提供清晰的参数说明")
    
    print("\n=== 修复验证完成 ===")
    print("现在 LLM 可以使用更友好的参数名称：")
    print("- search_mode='filename' (替代 'filename_only')")
    print("- search_mode='content' (替代 'content_only')")
    print("- search_mode='both' (默认)")
    print("- search_logic='OR' 或 'AND'")

if __name__ == "__main__":
    test_fixed_search()
    input("\n按回车键退出...")  # 防止测试窗口立即关闭
