# MCP 文件系统服务器动态路径解决方案

## 问题背景

原来的 MCP 文件系统服务器存在两个主要问题：

1. **根目录硬编码问题**：路径被硬编码为 `D:/爱瑞安故事集`，每次更改仓库路径都需要修改源代码
2. **LLM 工具调用问题**：LLM 会连续调用多个 `read_file` 工具，导致 message ID 容易出错

## 解决方案

### 1. 动态路径配置系统

创建了新的配置系统，支持：

- **环境变量配置**：通过 `MCP_FILESYSTEM_ROOT` 环境变量设置默认目录
- **运行时动态配置**：通过工具动态切换工作目录
- **向后兼容**：保持原有 API 不变

### 2. 简化版 MCP 服务器

创建了 `local_filesystem_mcp_simple.py`，具有以下特性：

- **清晰的类型注解**：避免类型错误
- **简化的参数处理**：使用明确的 Pydantic 模型
- **动态路径管理**：支持运行时切换工作目录

## 文件说明

### 核心文件

- `config.py` - 配置管理系统
- `local_filesystem_mcp_simple.py` - 简化版 MCP 服务器（推荐使用）
- `local_filesystem_mcp.py` - 原始版本（存在类型问题）

### 配置系统

```python
# 从环境变量加载默认配置
export MCP_FILESYSTEM_ROOT="D:/Ariane故事集"

# 或者在代码中动态设置
from config import config
config.set_root("D:/新的故事集")
```

## 使用方法

### 1. 使用环境变量（推荐）

```bash
# 设置环境变量
set MCP_FILESYSTEM_ROOT=D:\Ariane故事集

# 启动服务器
python local_filesystem_mcp_simple.py
```

### 2. 运行时动态切换

通过 MCP 工具动态切换工作目录：

```python
# 设置工作目录
set_working_directory({"path": "D:/新的工作目录"})

# 获取当前目录
get_working_directory()

# 重置到默认目录
reset_working_directory()
```

### 3. 在 Obsidian 中使用

在 Claude Desktop 配置文件中使用新的服务器：

```json
{
  "mcpServers": {
    "local-filesystem": {
      "command": "python",
      "args": ["D:/mcp-file-process/local_filesystem_mcp_simple.py"],
      "env": {
        "MCP_FILESYSTEM_ROOT": "D:/Ariane故事集"
      }
    }
  }
}
```

## 新工具说明

### 动态路径管理工具

1. **set_working_directory**
   - 功能：设置当前工作目录
   - 参数：`{"path": "目录路径"}`
   - 示例：`set_working_directory({"path": "D:/新的目录"})`

2. **get_working_directory**
   - 功能：获取当前目录信息
   - 返回：当前目录路径和配置状态

3. **reset_working_directory**
   - 功能：重置到默认目录
   - 使用环境变量或原始配置

### 文件操作工具（保持不变）

- `read_file` - 读取文件
- `write_file` - 写入文件  
- `list_directory` - 列出目录
- `search_files` - 搜索文件

## 解决 LLM 工具调用问题

### 问题分析

LLM 倾向于连续调用多个 `read_file` 工具，这会导致：
- Message ID 冲突
- 并发访问问题
- 性能问题

### 解决方案

1. **简化工具接口**：使用明确的参数模型，避免歧义
2. **改进错误处理**：提供清晰的错误信息
3. **资源限制**：限制文件大小和搜索范围

### 最佳实践

```python
# 推荐：先列出目录，再读取特定文件
directory = list_directory({"directory_path": "笔记目录"})
file_content = read_file({"file_path": "特定文件.md"})

# 不推荐：连续读取多个文件
# file1 = read_file({"file_path": "file1.md"})
# file2 = read_file({"file_path": "file2.md"})
# file3 = read_file({"file_path": "file3.md"})
```

## 部署建议

### 开发环境

1. 使用环境变量设置默认路径
2. 使用简化版服务器 `local_filesystem_mcp_simple.py`
3. 定期测试路径切换功能

### 生产环境

1. 设置固定的环境变量
2. 使用权限限制确保安全
3. 监控工具使用情况

## 故障排除

### 常见问题

1. **权限错误**：确保目录存在且有读写权限
2. **路径越界**：所有操作限制在根目录内
3. **文件类型限制**：只允许特定扩展名（.md, .txt, .json 等）

### 调试方法

```python
# 检查当前配置
get_working_directory()

# 测试路径解析
try:
    path = resolve_path("测试文件.md")
    print(f"路径解析成功: {path}")
except Exception as e:
    print(f"路径解析失败: {e}")
```

## 总结

新的动态路径解决方案：

- ✅ 解决了根目录硬编码问题
- ✅ 支持环境变量和运行时配置
- ✅ 保持向后兼容性
- ✅ 改进了工具调用稳定性
- ✅ 提供了清晰的错误处理

推荐使用 `local_filesystem_mcp_simple.py` 作为新的 MCP 服务器。
