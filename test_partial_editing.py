"""
测试部分文件编辑功能
"""

import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def test_partial_editing():
    """测试部分文件编辑功能"""
    
    # 创建服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["local_filesystem_mcp_simple.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            
            print("=== 测试部分文件编辑功能 ===")
            
            # 1. 测试追加功能
            print("\n1. 测试 append_to_file:")
            result = await session.call_tool("append_to_file", {
                "file_path": "test_file.txt",
                "content": "\n这是追加的内容"
            })
            print(f"结果: {result}")
            
            # 2. 测试插入功能
            print("\n2. 测试 insert_into_file:")
            result = await session.call_tool("insert_into_file", {
                "file_path": "test_file.txt",
                "line_number": 3,
                "content": "这是插入的第三行"
            })
            print(f"结果: {result}")
            
            # 3. 测试替换功能
            print("\n3. 测试 replace_in_file:")
            result = await session.call_tool("replace_in_file", {
                "file_path": "test_file.txt",
                "search_text": "第四行内容",
                "replace_text": "第四行已被替换"
            })
            print(f"结果: {result}")
            
            # 4. 测试删除功能
            print("\n4. 测试 delete_from_file:")
            result = await session.call_tool("delete_from_file", {
                "file_path": "test_file.txt",
                "line_start": 6,
                "line_end": 7
            })
            print(f"结果: {result}")
            
            # 5. 读取最终结果
            print("\n5. 读取最终文件内容:")
            result = await session.call_tool("read_file", {
                "file_path": "test_file.txt"
            })
            print(f"最终内容: {result}")
            
            print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_partial_editing())
