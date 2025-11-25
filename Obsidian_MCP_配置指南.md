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

## 🎯 LLM 使用指南

### AI 助手的重要指令

**工作目录设置：**
目前你正处在一个obsidian仓库之中，在一切开始之前，请先使用set_working_directory将对应的server的工作目录设置为："D:/Knowledge"。
如果存在多个set_working_directory工具，则一开始每个都要设置一遍。

**调用格式规范：**
调用工具的时候，一定要先声明调用的是哪个server，格式为 servername:toolname
避免同时调用多个工具

**重要注意事项：**
1. **严格JSON格式**：调用MCP工具的时候请严格遵循JSON数据格式，确保所有括号对齐
2. **长文本策略**：如果要进行长文本输出，或者完成一个多步骤任务，请先制定计划，然后分步进行，每次输出只输出部分内容（因此，你可以用write工具创建文件，书写开头，结束输出，然后在之后的对话中再不断append）
3. **先搜索**：当我提到每个笔记的时候，推荐你先用search工具搜索其标题（因为我基本不会直接写全名）
4. **改动后打开**：在改动文件的时候总是选择改动后打开
5. **任务总结**：任务完成后，总是总结一下所有你改动或者创建的笔记（给出链接）

**理解Obsidian特性：**
1. **文件名即标题**：由于Obsidian的特性，文件名可以理解为最大的标题（零级标题），所以无需添加额外标题作为笔记名称

**输出格式：**
1. **公式块**：使用双美元符号包裹，行内公式使用美元符号包裹
2. **YAML完整性**：Obsidian的YAML需要在首行开始，因此修改YAML的时候注意不要破坏这个合法性

**小约定：**
1. **项目完成标记**：如果一个Project完成了，请帮我添加这个yaml属性：`done: true`

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
