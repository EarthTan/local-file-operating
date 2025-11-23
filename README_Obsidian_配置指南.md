# 本地文件系统 MCP 服务器 - Obsidian 配置指南

## 概述

这个 MCP 服务器为 Obsidian 的 LLM 插件提供本地文件系统操作功能，让您的 AI 助手能够读取、写入、搜索和管理您的笔记文件。

## 功能特性

### 可用工具
- **read_file** - 读取文件内容
- **write_file** - 写入或编辑文件
- **list_directory** - 列出目录内容
- **search_files** - 在文件中搜索文本
- **create_note** - 创建新的 Obsidian 笔记
- **get_note_info** - 获取笔记信息

### 可用资源
- **file://{path}** - 文件内容资源
- **dir://{path}** - 目录列表资源

## 安装和启动

### 1. 安装依赖
```bash
pip install mcp[cli]
```

### 2. 启动服务器
**方法一：使用批处理文件（推荐）**
```bash
start_server.bat
```

**方法二：直接运行 Python 脚本**
```bash
python local_filesystem_mcp.py
```

### 3. 验证服务器运行
服务器启动后，您应该看到：
```
启动本地文件系统 MCP 服务器...
服务器将在 http://localhost:8000/mcp 运行
按 Ctrl+C 停止服务器
```

## Obsidian 插件配置

### 支持的 Obsidian 插件
- **Copilot** (推荐)
- **Text Generator**
- **AI Assistant**
- 其他支持 MCP 协议的 LLM 插件

### 配置步骤

## MCP 服务器配置参数

根据您提供的示例格式，以下是本地文件系统 MCP 服务器的配置参数：

### 对于 stdio 传输（推荐用于本地服务器）

```json
{
  "command": "python",
  "args": [
    "local_filesystem_mcp.py"
  ],
  "env": {
    "PYTHONPATH": "."
  }
}
```

### 对于 HTTP 传输（如果使用 HTTP 服务器）

```json
{
  "command": "python",
  "args": [
    "local_filesystem_mcp.py"
  ],
  "env": {
    "PYTHONPATH": "."
  }
}
```

**注意**：Obsidian 插件会自动检测服务器使用的传输协议（stdio 或 HTTP）。

### 配置说明

- **command**: 执行命令（这里是 `python`）
- **args**: 命令行参数（服务器脚本路径）
- **env**: 环境变量（设置 Python 路径）

### 在 Obsidian 插件中的配置步骤

1. **打开 Obsidian 设置**
2. **进入您的 LLM 插件设置**（Copilot、Text Generator 等）
3. **找到 "MCP Servers" 或 "External Tools" 部分**
4. **添加新的 MCP 服务器配置**
5. **将上述 JSON 配置粘贴到配置框中**
6. **保存设置**

### 验证配置

配置完成后，您的 AI 助手应该能够：
- 读取和列出可用的工具
- 执行文件操作
- 访问文件资源

### 安全配置建议

为了确保文件安全，建议在插件中配置以下限制：

1. **文件访问范围**：限制为您的 Obsidian 库目录
2. **文件类型限制**：主要允许 `.md` 文件
3. **操作权限**：根据需求启用读写权限

## 使用示例

### 1. 读取笔记
```
请读取我的 "项目计划.md" 文件
```

### 2. 搜索内容
```
搜索所有包含 "TODO" 的笔记
```

### 3. 创建新笔记
```
创建一个名为 "会议记录" 的新笔记，内容为今天的会议要点
```

### 4. 编辑笔记
```
在 "购物清单.md" 中添加 "牛奶" 和 "面包"
```

### 5. 浏览目录
```
列出我的笔记库中的所有文件
```

## 故障排除

### 常见问题

**1. 服务器无法启动**
- 检查 Python 是否安装：`python --version`
- 检查 MCP 是否安装：`pip list | grep mcp`
- 确保端口 8000 未被占用

**2. 插件无法连接**
- 确认服务器正在运行
- 检查防火墙设置
- 验证 URL：`http://localhost:8000/mcp`

**3. 权限错误**
- 确保服务器有文件读写权限
- 检查文件路径是否正确
- 验证文件是否被其他程序锁定

**4. 安全限制**
- 服务器会自动阻止访问敏感系统文件
- 如果遇到权限问题，检查文件路径是否在允许范围内

### 调试方法

1. **检查服务器日志**：查看控制台输出
2. **测试连接**：使用浏览器访问 `http://localhost:8000/mcp`
3. **验证工具列表**：使用 MCP Inspector 测试

## 安全注意事项

1. **文件访问限制**：服务器会自动阻止访问系统敏感文件
2. **网络访问**：默认只允许本地连接 (localhost)
3. **权限管理**：建议在沙盒环境中运行
4. **备份重要文件**：在进行批量操作前备份重要笔记

## 高级配置

### 自定义启动参数

如果需要修改服务器配置，可以编辑 `local_filesystem_mcp.py` 文件：

```python
# 修改端口（如果需要）
mcp.run(transport="streamable-http", port=8080)

# 修改主机（允许远程连接，不推荐）
mcp.run(transport="streamable-http", host="0.0.0.0")
```

### 添加自定义工具

您可以在 `local_filesystem_mcp.py` 中添加自定义工具：

```python
@mcp.tool()
async def custom_tool(ctx: Context[ServerSession, None], parameter: str) -> str:
    """自定义工具示例"""
    return f"处理结果: {parameter}"
```

## 技术支持

如果遇到问题，请：
1. 检查此文档的故障排除部分
2. 查看服务器控制台错误信息
3. 确保所有依赖项正确安装
4. 验证 Obsidian 插件配置

## 更新日志

- **v1.0** - 初始版本，提供基础文件操作功能
- 支持文件读写、搜索、目录浏览
- 集成 Obsidian 特定功能
- 内置安全保护机制

---

**注意**：请确保在使用前了解文件操作的风险，并定期备份重要数据。
