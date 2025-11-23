# Obsidian MCP 服务器配置指南

## 问题分析

您遇到的连接问题主要有两个原因：

1. **JSON 路径转义问题**：Windows 路径中的反斜杠 `\` 在 JSON 中需要转义
2. **传输协议不匹配**：服务器配置为 HTTP 传输，但 Obsidian 插件需要 stdio 传输

## 解决方案

### 1. 修复后的服务器配置

服务器已修改为使用 stdio 传输协议，这是 Obsidian 插件期望的协议。

### 2. 正确的 Obsidian 插件配置

在您的 Obsidian LLM 插件中，使用以下 JSON 配置：

#### 选项一：使用转义的反斜杠
```json
{
  "command": "python",
  "args": [
    "D:\\python-sdk\\local_filesystem_mcp.py"
  ],
  "env": {
    "PYTHONPATH": "."
  }
}
```

#### 选项二：使用正斜杠（推荐）
```json
{
  "command": "python",
  "args": [
    "D:/python-sdk/local_filesystem_mcp.py"
  ],
  "env": {
    "PYTHONPATH": "."
  }
}
```

#### 选项三：使用相对路径（如果插件支持）
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

### 3. 安装 Python 和依赖

如果 Python 未安装，请先安装 Python：

1. 下载 Python：https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"
3. 安装 MCP SDK：
   ```bash
   pip install mcp[cli]
   ```

### 4. 验证安装

安装完成后，验证 Python 和 MCP SDK：

```bash
python --version
python -c "import mcp; print('MCP SDK 已安装')"
```

### 5. 测试服务器

运行服务器测试连接：

```bash
python local_filesystem_mcp.py
```

如果服务器正常启动，您应该看到：
```
启动本地文件系统 MCP 服务器...
服务器使用 stdio 传输协议
按 Ctrl+C 停止服务器
```

## 故障排除

### 如果仍然连接失败

1. **检查 Python 安装**：
   - 确保 Python 已添加到 PATH
   - 重新启动终端或 Obsidian
   - 如果 Python 未安装，请下载并安装 Python

2. **检查路径**：
   - 确保 `D:/python-sdk/local_filesystem_mcp.py` 文件存在
   - 检查路径拼写是否正确

3. **检查依赖**：
   - 确保已安装 MCP SDK：`pip install mcp[cli]`
   - 确保已安装 pydantic：`pip install pydantic`

4. **检查插件配置**：
   - 确保 JSON 格式正确
   - 确保没有额外的逗号或引号
   - 使用 JSON 验证器检查配置

### 常见错误

- **"invalid json"**：检查路径中的反斜杠是否已转义
- **"command not found"**：Python 未安装或不在 PATH 中
- **"module not found"**：MCP SDK 未安装
- **"Connection closed"**：Python 环境问题或依赖缺失

### Python 安装步骤

如果 Python 未安装：

1. 下载 Python：https://www.python.org/downloads/
2. 安装时务必勾选 "Add Python to PATH"
3. 安装完成后，重新启动命令行或 Obsidian
4. 验证安装：`python --version` 或 `py --version`
5. 安装依赖：`pip install mcp[cli] pydantic`

## 功能验证

配置成功后，您的 AI 助手应该能够：

- 读取和写入文件
- 搜索文件内容
- 创建新笔记
- 浏览目录结构

## 安全说明

服务器已内置安全保护：
- 阻止访问系统敏感文件
- 限制文件操作范围
- 自动安全检查

如果遇到权限问题，请检查文件路径是否在允许范围内。
