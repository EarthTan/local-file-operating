"""
测试笔记元数据 MCP 服务器的动态路径管理功能
"""

import tempfile
import os
from pathlib import Path

def create_test_files(test_dir: Path):
    """创建测试用的笔记文件"""
    
    # 创建带有标签的笔记
    note1_content = """---
title: Python 学习笔记
tags: [python, programming]
---
# Python 学习笔记

这是一篇关于 Python 学习的笔记。

#python #学习 #编程
"""
    
    note2_content = """---
title: MCP 服务器开发
tags: [mcp, development]
---
# MCP 服务器开发

关于 MCP 服务器开发的笔记。

#mcp #开发 #服务器
"""
    
    # 创建文件
    (test_dir / "python_notes.md").write_text(note1_content, encoding="utf-8")
    (test_dir / "mcp_development.md").write_text(note2_content, encoding="utf-8")
    
    print(f"测试文件已创建在: {test_dir}")

import asyncio

async def test_dynamic_path():
    """测试动态路径管理功能"""
    print("开始测试动态路径管理功能...")
    
    # 创建两个临时测试目录
    with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
        test_dir1 = Path(temp_dir1)
        test_dir2 = Path(temp_dir2)
        
        # 在两个目录中都创建测试文件
        create_test_files(test_dir1)
        create_test_files(test_dir2)
        
        # 设置环境变量以使用第一个测试目录
        os.environ["MCP_FILESYSTEM_ROOT"] = str(test_dir1)
        
        # 重新导入配置以应用新的根目录
        import importlib
        import config
        importlib.reload(config)
        
        # 导入服务器
        from note_metadata_mcp import mcp, config as server_config
        
        print(f"\n初始工作目录: {server_config.get_root()}")
        
        # 测试1: 列出第一个目录的标签
        print("\n=== 测试 1: 在初始目录中列出标签 ===")
        try:
            from note_metadata_mcp import ListTagsArgs
            args = ListTagsArgs()
            result = await mcp.call_tool("list_tags", {"args": args})
            print(f"在 {test_dir1} 中找到 {result['total_tags']} 个标签")
            for tag_info in result['tags']:
                print(f"  - {tag_info['tag']} (出现 {tag_info['count']} 次)")
        except Exception as e:
            print(f"测试失败: {e}")
        
        # 测试2: 切换到第二个目录
        print(f"\n=== 测试 2: 切换到第二个目录 {test_dir2} ===")
        try:
            from note_metadata_mcp import SetWorkingDirectoryArgs
            args = SetWorkingDirectoryArgs(path=str(test_dir2))
            result = await mcp.call_tool("set_working_directory", {"args": args})
            print(f"切换结果: {result}")
            
            # 验证切换是否成功
            current_dir = server_config.get_root()
            print(f"当前工作目录: {current_dir}")
        except Exception as e:
            print(f"切换目录失败: {e}")
        
        # 测试3: 在第二个目录中列出标签
        print(f"\n=== 测试 3: 在切换后的目录中列出标签 ===")
        try:
            from note_metadata_mcp import ListTagsArgs
            args = ListTagsArgs()
            result = await mcp.call_tool("list_tags", {"args": args})
            print(f"在 {test_dir2} 中找到 {result['total_tags']} 个标签")
            for tag_info in result['tags']:
                print(f"  - {tag_info['tag']} (出现 {tag_info['count']} 次)")
        except Exception as e:
            print(f"测试失败: {e}")
        
        # 测试4: 获取当前工作目录信息
        print(f"\n=== 测试 4: 获取当前工作目录信息 ===")
        try:
            result = await mcp.call_tool("get_working_directory", {})
            print(f"当前目录: {result['current_directory']}")
            print(f"是否动态: {result['is_dynamic']}")
        except Exception as e:
            print(f"获取目录信息失败: {e}")
        
        # 测试5: 重置到默认目录
        print(f"\n=== 测试 5: 重置到默认目录 ===")
        try:
            result = await mcp.call_tool("reset_working_directory", {})
            print(f"重置结果: {result}")
            
            current_dir = server_config.get_root()
            print(f"重置后工作目录: {current_dir}")
        except Exception as e:
            print(f"重置目录失败: {e}")
        
        print("\n动态路径管理测试完成!")

def main():
    asyncio.run(test_dynamic_path())
    input("按回车键退出...")

if __name__ == "__main__":
    main()
