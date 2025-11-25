# 笔记元数据 MCP 服务器

这是一个专注于笔记元数据管理和高级搜索功能的 MCP 服务器，与现有的文件系统服务器区分开，专门处理笔记的标签管理和时间范围搜索。

## 功能特性

### 1. 标签管理
- **列出所有标签**: 搜索所有包含 `#标签` 格式的标签，支持文本文件和 YAML frontmatter
- **按标签搜索笔记**: 支持单个标签搜索、多个标签的 AND/OR 逻辑搜索

### 2. 时间范围搜索
- **搜索最近笔记**: 根据文件元数据搜索最近特定时间范围内改动过或创建过的笔记
- **支持时间类型**: 创建时间或修改时间
- **灵活的时间范围**: 支持天、周、月等不同时间单位

## 安装和配置

### 环境要求
- Python 3.10+
- 依赖包: `pydantic`, `mcp`, `pyyaml`

### 配置
服务器使用与现有文件系统服务器相同的配置系统，支持环境变量 `MCP_FILESYSTEM_ROOT` 设置默认工作目录。

## 动态路径管理

服务器支持动态路径管理，让 LLM 能够自己设置工作目录，解决跨服务器路径同步问题。

### 动态路径管理工具

#### set_working_directory - 设置当前工作目录
设置服务器的工作目录到指定路径。

**参数:**
- `path` (必需): 要设置为工作目录的路径

**示例:**
```json
{
  "path": "D:\\Knowledge"
}
```

**返回:**
```
工作目录已设置为：D:\Knowledge
```

#### get_working_directory - 获取当前工作目录信息
获取当前工作目录的详细信息。

**参数:** 无

**返回:**
```json
{
  "current_directory": "D:\\Knowledge",
  "is_dynamic": "true"
}
```

#### reset_working_directory - 重置工作目录到默认
将工作目录重置为环境变量或默认配置。

**参数:** 无

**返回:**
```
工作目录已重置为默认：C:\Users\{username}\Documents
```

## 工具使用说明

### 同步工具（推荐用于不支持 await 的客户端）

如果您的客户端环境不支持异步调用（如某些命令行工具或旧版 SDK），请使用以下同步版本的工具：

#### 1. list_tags_sync - 列出所有标签（同步版）

**参数：** 与 `list_tags` 相同
**返回：** 与 `list_tags` 相同

**示例：**
```json
{
  "limit": 20,
  "include_file_paths": true
}
```

#### 2. search_notes_by_tags_sync - 按标签搜索笔记（同步版）

**参数：** 与 `search_notes_by_tags` 相同
**返回：** 与 `search_notes_by_tags` 相同

**示例：**
```json
{
  "tags": ["python", "mcp"],
  "search_logic": "OR"
}
```

#### 3. search_recent_notes_sync - 搜索最近笔记（同步版）

**参数：** 与 `search_recent_notes` 相同
**返回：** 与 `search_recent_notes` 相同

**示例：**
```json
{
  "time_range": "7d",
  "limit": 10
}
```

### 异步工具（适用于支持 await 的客户端）

如果您在异步环境中使用 MCP 客户端，可以使用以下异步版本的工具：

#### 1. list_tags - 列出所有标签（异步版）

列出指定目录中的所有标签。

**参数:**
- `directory_path` (可选): 搜索目录路径，默认为当前工作目录
- `file_pattern` (可选): 文件模式匹配，支持通配符，默认 `*.md`
- `min_count` (可选): 标签最小出现次数，默认 1
- `include_file_paths` (可选): 是否包含文件路径信息，默认 False

**示例:**
```json
{
  "directory_path": "/path/to/notes",
  "include_file_paths": true,
  "min_count": 2
}
```

**返回:**
```json
{
  "total_tags": 15,
  "tags": [
    {
      "tag": "python",
      "count": 5,
      "files": ["note1.md", "note2.md"]
    },
    {
      "tag": "mcp",
      "count": 3
    }
  ],
  "directory": "/path/to/notes"
}
```

### 2. search_notes_by_tags - 按标签搜索笔记

搜索包含特定标签的笔记。

**参数:**
- `tags` (必需): 要搜索的标签列表
- `directory_path` (可选): 搜索目录路径，默认为当前工作目录
- `file_pattern` (可选): 文件模式匹配，支持通配符，默认 `*.md`
- `search_logic` (可选): 搜索逻辑："OR" 匹配任意标签，"AND" 必须匹配所有标签，默认 "OR"
- `limit` (可选): 搜索结果数量限制，默认 100，最大 1000

**示例:**
```json
{
  "tags": ["python", "mcp"],
  "search_logic": "OR",
  "limit": 50
}
```

**返回:**
```json
{
  "total_matches": 8,
  "results": [
    {
      "file_path": "python_notes.md",
      "matched_tags": ["python"],
      "frontmatter_tags": ["python", "programming"],
      "content_tags": ["python", "学习", "编程"]
    }
  ],
  "limit": 50
}
```

### 3. search_recent_notes - 搜索最近笔记

搜索最近特定时间范围内改动过或创建过的笔记。

**参数:**
- `time_range` (必需): 时间范围，例如：`7d` (7天), `1w` (1周), `30d` (30天), `1m` (1月)
- `directory_path` (可选): 搜索目录路径，默认为当前工作目录
- `file_pattern` (可选): 文件模式匹配，支持通配符，默认 `*.md`
- `time_type` (可选): 时间类型：`created` 创建时间，`modified` 修改时间，默认 `modified`
- `limit` (可选): 搜索结果数量限制，默认 100，最大 1000

**示例:**
```json
{
  "time_range": "7d",
  "time_type": "modified",
  "limit": 20
}
```

**返回:**
```json
{
  "total_matches": 12,
  "results": [
    {
      "file_path": "recent_note.md",
      "file_name": "recent_note.md",
      "created_time": "2025-01-20T10:30:00+00:00",
      "modified_time": "2025-01-25T15:45:00+00:00",
      "size": 1024,
      "time_type": "modified",
      "time_value": "2025-01-25T15:45:00+00:00"
    }
  ],
  "time_range": "7d",
  "time_type": "modified"
}
```

## 标签格式支持

### 1. YAML Frontmatter 标签
支持多种标签字段名：
- `tags`
- `tag` 
- `labels`
- `label`

支持格式：
- 列表格式: `tags: [python, mcp, development]`
- 字符串格式: `tags: python, mcp, development`

### 2. 内容内联标签
支持 `#标签` 格式，支持中英文：
- `#python`
- `#学习`
- `#development`

## 与现有文件系统服务器的区别

| 特性 | 文件系统服务器 | 笔记元数据服务器 |
|------|---------------|-----------------|
| 文件操作 | ✅ 读写、编辑、删除文件 | ❌ 不提供文件操作 |
| 标签搜索 | ❌ 仅支持内容搜索 | ✅ 专门的标签搜索 |
| 时间范围搜索 | ❌ 不支持 | ✅ 专门的元数据搜索 |
| YAML frontmatter 解析 | ❌ 不支持 | ✅ 完整支持 |
| 标签统计 | ❌ 不支持 | ✅ 标签计数和统计 |
| 动态路径管理 | ✅ 支持 | ✅ 支持 |
| 同步工具支持 | ❌ 不支持 | ✅ 支持同步和异步版本 |

## 使用场景

### 1. 知识管理
- 快速查找特定主题的笔记
- 分析笔记库中的标签分布
- 发现相关的笔记内容

### 2. 内容整理
- 基于标签组织笔记
- 查找最近更新的内容
- 清理未使用的标签

### 3. 工作流程优化
- 跟踪最近的工作进展
- 基于标签的自动化处理
- 内容分析和统计
- 跨服务器路径同步管理

## 性能优化

- 使用线程池并行处理文件搜索
- 支持搜索限制和分页
- 优化的正则表达式匹配
- 文件大小限制保护

## 注意事项

1. **文件类型限制**: 仅支持 `.md` 和 `.txt` 文件
2. **文件大小限制**: 最大读取 5MB 的文件
3. **编码支持**: 支持 UTF-8 编码，自动处理编码错误
4. **路径安全**: 所有路径都在配置的根目录内，防止路径越界

## 故障排除

### 常见问题

1. **找不到标签**
   - 检查文件是否在搜索目录内
   - 确认标签格式是否正确
   - 检查文件编码是否为 UTF-8

2. **搜索速度慢**
   - 减少搜索范围
   - 使用更具体的文件模式
   - 增加搜索限制

3. **权限错误**
   - 确认有文件读取权限
   - 检查路径是否在允许的根目录内

4. **路径越界错误**
   - 使用 `set_working_directory` 工具设置正确的工作目录
   - 检查路径是否存在且为有效目录
   - 使用 `get_working_directory` 确认当前工作目录

### 解决跨服务器路径同步问题

当在不同 MCP 服务器实例中遇到路径不一致问题时：

1. **使用动态路径管理工具**
   ```json
   {
     "path": "D:\\Knowledge"
   }
   ```

2. **验证路径设置**
   ```json
   {}
   ```

3. **重置到默认配置（如果需要）**
   ```json
   {}
   ```

这样就能确保所有服务器实例使用相同的工作目录。

### 解决异步调用问题

如果客户端返回 `<coroutine object ...>` 错误，说明客户端不支持异步调用：

**解决方案：**
- 使用同步版本的工具（工具名以 `_sync` 结尾）
- 或者确保客户端正确使用 `await` 调用异步工具

**推荐做法：**
- 在同步环境中使用 `*_sync` 工具
- 在异步环境中使用原始工具名

## 开发说明

服务器基于 FastMCP 框架构建，使用 Pydantic 进行数据验证，支持异步处理和并发搜索。
