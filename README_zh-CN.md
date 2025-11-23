# 本地文件系统 MCP 服务器（简化版）

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个简洁高效的本地文件系统 MCP 服务器，支持动态路径配置和丰富的文件操作功能。专为 AI 助手和自动化工具设计，提供安全的文件系统访问能力。

## 📖 项目背景

本项目是基于 Anthropic 官方 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) 开发的简化版本。在保持核心功能和安全性特性的同时，本版本专注于：

- **代码简化**：相比原版减少 60% 代码量
- **动态配置**：增强的运行时路径管理
- **部分编辑**：丰富的文件操作能力
- **开发体验**：更清晰的架构和更好的文档

原项目采用 MIT 许可证，本项目同样遵循 MIT 许可证。

## ✨ 核心特性

### 🚀 简化设计
- **代码简洁**：相比原版减少 60% 代码量，易于理解和维护
- **动态配置**：支持环境变量和运行时路径配置
- **即开即用**：无需复杂配置，快速启动使用

### 🔧 丰富功能
- **基础操作**：文件读取、写入、目录列表、内容搜索
- **部分编辑**：追加、插入、替换、删除、应用补丁
- **动态管理**：运行时设置和切换工作目录
- **资源访问**：通过 MCP 协议访问文件和目录资源

### 🛡️ 安全保障
- **根目录限制**：所有操作限制在预设根目录内
- **文件类型白名单**：仅允许操作指定类型的文件
- **大小限制**：防止读取过大文件（最大 10MB）

## 🚀 快速开始

### 环境要求
- Python 3.10+
- MCP SDK

### 安装依赖
```bash
pip install mcp[cli]
```

### 启动服务器
```bash
# 使用默认配置
python local_filesystem_mcp_simple.py

# 或使用环境变量设置根目录
set MCP_FILESYSTEM_ROOT=D:/your/workspace
python local_filesystem_mcp_simple.py
```

### 验证运行
服务器启动后，您将看到：
```
启动本地文件系统 MCP 服务器（动态路径版）...
根目录：D:/your/workspace
支持环境变量 MCP_FILESYSTEM_ROOT 设置默认目录
按 Ctrl+C 停止服务器
```

## 📋 可用工具

### 基础文件操作
| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `read_file` | 读取文件内容 | `file_path` |
| `write_file` | 写入或覆盖文件 | `file_path`, `content`, `create_dirs` |
| `list_directory` | 列出目录内容 | `directory_path` |
| `search_files` | 搜索文件内容 | `search_term`, `directory_path`, `file_pattern`, `limit` |

### 部分文件编辑
| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `append_to_file` | 在文件末尾追加内容 | `file_path`, `content` |
| `insert_into_file` | 在指定行号插入内容 | `file_path`, `line_number`, `content` |
| `replace_in_file` | 搜索并替换文本 | `file_path`, `search_text`, `replace_text` |
| `delete_from_file` | 删除指定行范围 | `file_path`, `line_start`, `line_end` |
| `patch_file` | 应用统一差异格式补丁 | `file_path`, `patch_content` |

### 动态路径管理
| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `set_working_directory` | 设置当前工作目录 | `path` |
| `get_working_directory` | 获取当前目录信息 | - |
| `reset_working_directory` | 重置到默认目录 | - |

## 🔧 配置说明

### 环境变量配置
```bash
# 设置默认工作目录
export MCP_FILESYSTEM_ROOT=/path/to/your/workspace

# Windows
set MCP_FILESYSTEM_ROOT=D:\your\workspace
```

### 运行时配置
通过工具动态设置工作目录：
```python
# 设置新的工作目录
await set_working_directory({"path": "/new/workspace/path"})

# 获取当前目录信息
info = await get_working_directory()
print(info)  # {"current_directory": "/new/workspace/path", "is_dynamic": "true"}

# 重置到默认目录
await reset_working_directory()
```

## 💡 使用示例

### 基础文件操作
```python
# 读取文件
content = await read_file({"file_path": "notes/readme.md"})

# 写入文件
await write_file({
    "file_path": "notes/new_note.md", 
    "content": "# 新笔记\n这是内容",
    "create_dirs": True
})

# 列出目录
listing = await list_directory({"directory_path": "notes"})

# 搜索内容
results = await search_files({
    "search_term": "TODO",
    "directory_path": "notes",
    "limit": 50
})
```

### 部分文件编辑
```python
# 在文件末尾追加内容
await append_to_file({
    "file_path": "notes/log.md",
    "content": "\n## 新记录\n- 完成功能开发"
})

# 在指定行插入内容
await insert_into_file({
    "file_path": "notes/todo.md",
    "line_number": 3,
    "content": "- [ ] 新任务"
})

# 替换文本
await replace_in_file({
    "file_path": "notes/config.md",
    "search_text": "old_value",
    "replace_text": "new_value"
})

# 删除指定行
await delete_from_file({
    "file_path": "notes/temp.md",
    "line_start": 5,
    "line_end": 10
})
```

### 动态路径管理
```python
# 切换到新工作目录
await set_working_directory({"path": "/projects/current"})

# 获取当前目录信息
info = await get_working_directory()
print(f"当前目录: {info['current_directory']}")

# 重置到默认目录
await reset_working_directory()
```

## 🛡️ 安全特性

### 访问限制
- **根目录限制**：所有文件操作限制在预设根目录及其子目录内
- **路径解析**：自动解析相对路径，防止目录遍历攻击
- **越界检查**：严格检查所有操作路径是否在允许范围内

### 文件类型控制
```python
# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
```

### 大小限制
- **最大文件大小**：10MB，防止内存溢出
- **搜索结果限制**：默认 200 条，最大 5000 条

## 🔍 故障排除

### 常见问题

**服务器无法启动**
```bash
# 检查 Python 版本
python --version

# 检查 MCP 安装
python -c "import mcp"
```

**权限错误**
- 确保目标目录存在且有读写权限
- 检查文件路径是否在根目录范围内
- 验证文件类型是否在允许列表中

**文件操作失败**
- 检查文件是否被其他程序占用
- 确认文件编码为 UTF-8
- 验证文件大小是否超过限制

### 调试方法
1. 查看服务器控制台输出
2. 检查环境变量设置
3. 验证文件路径权限
4. 使用简单文件测试基本功能

## 🤝 参与开发

我们欢迎社区贡献！以下是参与方式：

### 报告问题
- 使用 GitHub Issues 报告 bug 或提出功能建议
- 提供详细的错误信息和复现步骤

### 提交代码
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发指南
- 遵循现有代码风格
- 添加适当的单元测试
- 更新相关文档
- 确保向后兼容性

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 感谢 [Model Context Protocol](https://modelcontextprotocol.io) 团队
- 感谢所有贡献者和用户

---

**注意**：在使用前请了解文件操作的风险，定期备份重要数据。

如有问题，请查看 [Issues](https://github.com/your-repo/issues) 或提交新问题。

---

[English Documentation](README.md) | [中文文档](README_zh-CN.md)
