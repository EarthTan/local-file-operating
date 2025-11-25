# LLM 使用指南 - Obsidian MCP 服务器

## 🎯 核心指令

### 首要步骤：设置工作目录
**在使用任何工具之前，必须先设置工作目录：**
```python
await set_working_directory({"path": "D:/Knowledge"})
```

## 📋 重要注意事项

### 1. 严格JSON格式
- 调用MCP工具时请严格遵循JSON数据格式
- 确保所有括号正确对齐
- 检查引号是否正确闭合

**正确示例：**
```python
await write_file({
    "file_path": "notes/example.md",
    "content": "# 示例笔记\n这是内容",
    "create_dirs": True,
    "open_after_write": True
})
```

### 2. 长文本策略
- 对于长文本输出或多步骤任务，先制定计划
- 分步执行，每次输出只输出部分内容
- 使用`write_file`创建文件，书写开头
- 在后续对话中使用`append_to_file`继续添加内容

**示例流程：**
```python
# 第一步：创建文件并写开头
await write_file({
    "file_path": "长文档.md",
    "content": "# 长文档\n\n## 第一部分\n这是开头内容...",
    "open_after_write": True
})

# 第二步：追加内容
await append_to_file({
    "file_path": "长文档.md",
    "content": "\n\n## 第二部分\n这是后续内容..."
})
```

### 3. 先搜索再操作
- 当我提到笔记时，先用`search_files`搜索标题
- 我很少使用完整的文件名
- 搜索可以帮助找到确切的文件

**搜索示例：**
```python
# 搜索包含"项目"的文件
results = await search_files({
    "search_term": "项目",
    "search_mode": "filename",
    "limit": 10
})
```

### 4. 改动后打开
- 在改动文件时总是选择改动后打开
- 使用`open_after_write=True`或类似参数
- 这让我可以立即查看修改结果

### 5. 任务总结
- 任务完成后，总结所有改动或创建的笔记
- 提供文件链接或路径
- 说明每个文件的修改内容

## 🔍 Obsidian 特性理解

### 文件名即标题
- Obsidian中文件名就是最大的标题（零级标题）
- 无需在文件内容中添加额外标题作为笔记名称
- 文件结构应该反映内容的层次关系

**正确做法：**
```
文件名：项目计划.md
内容：
- 项目目标
- 时间安排
- 资源需求
```

**避免做法：**
```
文件名：项目计划.md
内容：
# 项目计划  # ← 重复的标题，不需要
- 项目目标
- 时间安排
```

## 📝 输出格式规范

### 数学公式
- **公式块**：使用双美元符号包裹
  ```
  $$
  E = mc^2
  $$
  ```
- **行内公式**：使用单美元符号包裹
  ```
  根据公式 $F = ma$ 计算...
  ```

### YAML Frontmatter
- YAML必须在文件首行开始
- 修改YAML时注意不要破坏格式
- 确保YAML以`---`开始和结束

**正确格式：**
```
---
title: 项目笔记
tags: [项目, 计划]
date: 2024-01-01
---
正文内容...
```

## ✅ 小约定

### 项目完成标记
- 当项目完成时，添加YAML属性：`done: true`
- 这有助于跟踪项目状态

**示例：**
```
---
title: 项目完成报告
done: true
date: 2024-01-15
---
项目已成功完成...
```

## 🛠️ 工具使用最佳实践

### 文件系统服务器工具
```python
# 1. 设置工作目录（必须）
await set_working_directory({"path": "D:/Knowledge"})

# 2. 搜索文件（推荐先搜索）
results = await search_files({
    "search_term": "关键词",
    "search_mode": "both",
    "limit": 20
})

# 3. 读取文件
content = await read_file({
    "file_path": "目标文件.md",
    "open_after_read": True
})

# 4. 写入文件（推荐打开）
await write_file({
    "file_path": "新文件.md",
    "content": "文件内容",
    "create_dirs": True,
    "open_after_write": True
})

# 5. 追加内容
await append_to_file({
    "file_path": "现有文件.md",
    "content": "追加的内容",
    "open_after_append": True
})
```

### 元数据服务器工具
```python
# 1. 列出所有标签
tags = await list_tags({
    "directory_path": "D:/Knowledge",
    "min_count": 1
})

# 2. 按标签搜索笔记
tag_results = await search_notes_by_tags({
    "tags": ["项目", "重要"],
    "search_logic": "AND"
})

# 3. 搜索最近笔记
recent_notes = await search_recent_notes({
    "time_range": "7d",
    "time_type": "modified"
})
```

## 🚨 常见错误避免

### JSON格式错误
```python
# ❌ 错误：缺少逗号
await write_file({
    "file_path": "test.md"
    "content": "内容"  # 缺少逗号
})

# ✅ 正确
await write_file({
    "file_path": "test.md",
    "content": "内容"
})
```

### 路径错误
```python
# ❌ 错误：未设置工作目录
await read_file({"file_path": "笔记.md"})  # 可能找不到文件

# ✅ 正确：先设置工作目录
await set_working_directory({"path": "D:/Knowledge"})
await read_file({"file_path": "笔记.md"})
```

## 📊 任务执行流程

### 标准工作流程
1. **设置环境**：`set_working_directory`
2. **搜索定位**：`search_files` 找到目标文件
3. **读取分析**：`read_file` 了解当前内容
4. **执行操作**：`write_file` / `append_to_file` / 其他工具
5. **验证结果**：确保文件正确打开和显示
6. **总结报告**：列出所有修改的文件和内容

### 多步骤任务示例
```python
# 步骤1：设置环境
await set_working_directory({"path": "D:/Knowledge"})

# 步骤2：搜索相关文件
project_files = await search_files({
    "search_term": "项目计划",
    "search_mode": "filename"
})

# 步骤3：读取现有内容
for file in project_files.results[:3]:
    content = await read_file({"file_path": file.file_path})
    # 分析内容...

# 步骤4：创建总结文件
await write_file({
    "file_path": "项目总结.md",
    "content": "# 项目总结\n\n## 发现的文件\n- 文件1\n- 文件2",
    "open_after_write": True
})

# 步骤5：任务完成总结
print("任务完成！创建了以下文件：")
print("- 项目总结.md")
```

---

**记住：遵循这些指南将确保您能够高效、准确地使用MCP服务器与我的Obsidian笔记库进行交互。**
