"""
测试笔记元数据 MCP 服务器
"""

import asyncio
import tempfile
import os
from pathlib import Path

# 创建测试文件
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
    
    note3_content = """---
title: 最近更新的笔记
tags: [recent, update]
---
# 最近更新的笔记

这是最近更新的笔记内容。

#最近 #更新
"""
    
    # 创建文件
    (test_dir / "python_notes.md").write_text(note1_content, encoding="utf-8")
    (test_dir / "mcp_development.md").write_text(note2_content, encoding="utf-8")
    (test_dir / "recent_update.md").write_text(note3_content, encoding="utf-8")
    
    print(f"测试文件已创建在: {test_dir}")

async def test_server():
    """测试 MCP 服务器功能"""
    print("开始测试笔记元数据 MCP 服务器...")
    
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        create_test_files(test_dir)
        
        # 设置环境变量以使用测试目录
        os.environ["MCP_FILESYSTEM_ROOT"] = str(test_dir)
        
        # 重新导入配置以应用新的根目录
        import importlib
        import config
        importlib.reload(config)
        
        # 导入服务器
        from note_metadata_mcp import mcp
        
        print("\n=== 测试 1: 列出所有标签 ===")
        try:
            result = await mcp.call_tool("list_tags", {
                "args": {
                    "directory_path": str(test_dir)
                }
            })
            print(f"找到 {result['total_count']} 个标签:")
            for tag_info in result['tags']:
                print(f"  - {tag_info['name']} (出现 {tag_info['count']} 次)")
        except Exception as e:
            print(f"测试失败: {e}")
        
        print("\n=== 测试 2: 按标签搜索笔记 ===")
        try:
            result = await mcp.call_tool("search_notes_by_tags", {
                "args": {
                    "tags": ["python", "mcp"],
                    "search_logic": "OR",
                    "limit": 10
                }
            })
            print(f"找到 {result.total_matches} 个匹配:")
            for match in result.results:
                print(f"  - {match.file_path}")
                print(f"    匹配标签: {match.matched_tags}")
        except Exception as e:
            print(f"测试失败: {e}")
        
        print("\n=== 测试 3: 搜索最近笔记 ===")
        try:
            result = await mcp.call_tool("search_recent_notes", {
                "args": {
                    "time_range": "1d",
                    "time_type": "modified",
                    "limit": 5
                }
            })
            print(f"找到 {result.total_matches} 个最近笔记:")
            for note in result.results:
                print(f"  - {note.file_name} (修改时间: {note.modified_time})")
        except Exception as e:
            print(f"测试失败: {e}")
        
        print("\n测试完成!")

if __name__ == "__main__":
    asyncio.run(test_server())
    input("按回车键退出...")
