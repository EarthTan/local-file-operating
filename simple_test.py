"""
简单的笔记元数据 MCP 服务器测试
直接测试功能而不通过 MCP 协议
"""

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

def test_functions():
    """直接测试功能函数"""
    print("开始测试笔记元数据 MCP 服务器功能...")
    
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
        
        # 导入服务器函数
        from note_metadata_mcp import (
            _search_tags_in_file,
            _search_recent_files_in_directory,
            extract_tags_from_content,
            parse_frontmatter,
            extract_tags_from_frontmatter
        )
        
        print("\n=== 测试 1: 标签提取功能 ===")
        try:
            # 测试单个文件的标签提取
            test_file = test_dir / "python_notes.md"
            content_tags, frontmatter_tags, all_tags = _search_tags_in_file(test_file)
            
            print(f"文件: {test_file.name}")
            print(f"内容标签: {list(content_tags)}")
            print(f"Frontmatter 标签: {list(frontmatter_tags)}")
            print(f"所有标签: {list(all_tags)}")
        except Exception as e:
            print(f"标签提取测试失败: {e}")
        
        print("\n=== 测试 2: Frontmatter 解析 ===")
        try:
            test_content = """---
title: 测试笔记
tags: [test, example]
---
# 测试内容

#测试标签 #示例
"""
            frontmatter, body = parse_frontmatter(test_content)
            print(f"Frontmatter: {frontmatter}")
            print(f"Body: {body[:50]}...")
            
            tags = extract_tags_from_frontmatter(frontmatter)
            print(f"Frontmatter 标签: {list(tags)}")
            
            content_tags = extract_tags_from_content(body)
            print(f"内容标签: {list(content_tags)}")
        except Exception as e:
            print(f"Frontmatter 解析测试失败: {e}")
        
        print("\n=== 测试 3: 最近文件搜索 ===")
        try:
            from datetime import timedelta
            from note_metadata_mcp import TimeRangeType
            
            recent_files = _search_recent_files_in_directory(
                test_dir, "*.md", timedelta(days=1), TimeRangeType.MODIFIED
            )
            print(f"找到 {len(recent_files)} 个最近文件:")
            for file_path in recent_files:
                print(f"  - {file_path.name}")
        except Exception as e:
            print(f"最近文件搜索测试失败: {e}")
        
        print("\n功能测试完成!")

if __name__ == "__main__":
    test_functions()
    input("按回车键退出...")
