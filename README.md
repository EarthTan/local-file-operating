# Local File System MCP Server (Simplified) - Obsidian Integration

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io)
[![Obsidian](https://img.shields.io/badge/Obsidian-Integration-purple.svg)](https://obsidian.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight and efficient local file system MCP server specifically designed for **Obsidian vaults** and markdown file management. With dynamic path configuration and rich file operations, this server enables AI assistants to securely interact with your Obsidian notes and knowledge base.

## 📖 Project Background

This project is a simplified version based on the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) developed by Anthropic. While maintaining the core functionality and security features, this version focuses on:

- **Code Simplification**: 60% less code compared to the original version
- **Dynamic Configuration**: Enhanced runtime path management
- **Partial Editing**: Rich file manipulation capabilities
- **Developer Experience**: Cleaner architecture and better documentation

The original project is licensed under MIT, and this project follows the same license.

## 🗂️ Obsidian Integration

### Perfect for Obsidian Vaults
This server is specifically optimized for managing **Obsidian vaults** and markdown files. It provides AI assistants with powerful tools to interact with your knowledge base:

- **Note Management**: Create, read, update, and search notes
- **Content Organization**: Manage folders and file structures
- **Smart Editing**: Precise text manipulation within notes
- **Link Management**: Handle internal links and references

### Common Obsidian Use Cases
- **AI-Powered Note Taking**: Let AI assistants help you organize and expand your notes
- **Automated Content Generation**: Generate summaries, outlines, or new content
- **Knowledge Base Maintenance**: Clean up and reorganize your vault
- **Research Assistance**: Search and analyze your existing notes
- **Template Management**: Create and apply note templates

## ✨ Core Features

### 🚀 Simplified Design
- **Clean Code**: 60% less code compared to the original version, easy to understand and maintain
- **Dynamic Configuration**: Support for environment variables and runtime path configuration
- **Ready to Use**: No complex setup required, quick startup

### 🔧 Rich Functionality
- **Basic Operations**: File read, write, directory listing, content search
- **Partial Editing**: Append, insert, replace, delete, apply patches
- **Dynamic Management**: Runtime working directory switching
- **Resource Access**: Access files and directories via MCP protocol

### 🛡️ Security Features
- **Root Directory Restriction**: All operations confined to preset root directory
- **File Type Whitelist**: Only allowed file types can be operated
- **Size Limits**: Prevent reading oversized files (max 10MB)

## 🚀 Quick Start

### Requirements
- Python 3.10+
- MCP SDK

### Install Dependencies
```bash
pip install mcp[cli]
```

### Start Server
```bash
# Use default configuration
python local_filesystem_mcp_simple.py

# Or set root directory via environment variable
set MCP_FILESYSTEM_ROOT=D:/your/workspace
python local_filesystem_mcp_simple.py
```

### Verify Operation
After starting the server, you'll see:
```
Starting Local File System MCP Server (Dynamic Path Version)...
Root Directory: D:/your/workspace
Support environment variable MCP_FILESYSTEM_ROOT for default directory
Press Ctrl+C to stop server
```

## 📋 Available Tools

### Basic File Operations
| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `read_file` | Read file content | `file_path` |
| `write_file` | Write or overwrite file | `file_path`, `content`, `create_dirs`, `open_after_write` |
| `open_note` | Open note file in Obsidian | `file_path` |
| `list_directory` | List directory contents | `directory_path` |
| `search_files` | Search file content | `search_term`, `directory_path`, `file_pattern`, `limit` |

### Partial File Editing
| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `append_to_file` | Append content to end of file | `file_path`, `content` |
| `insert_into_file` | Insert content at specific line | `file_path`, `line_number`, `content` |
| `replace_in_file` | Search and replace text | `file_path`, `search_text`, `replace_text` |
| `delete_from_file` | Delete specific line range | `file_path`, `line_start`, `line_end` |
| `patch_file` | Apply unified diff format patch | `file_path`, `patch_content` |

### Dynamic Path Management
| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `set_working_directory` | Set current working directory | `path` |
| `get_working_directory` | Get current directory info | - |
| `reset_working_directory` | Reset to default directory | - |

## 🔧 Configuration

### Environment Variables
```bash
# Set default working directory
export MCP_FILESYSTEM_ROOT=/path/to/your/workspace

# Windows
set MCP_FILESYSTEM_ROOT=D:\your\workspace
```

### Runtime Configuration
Dynamically set working directory via tools:
```python
# Set new working directory
await set_working_directory({"path": "/new/workspace/path"})

# Get current directory info
info = await get_working_directory()
print(info)  # {"current_directory": "/new/workspace/path", "is_dynamic": "true"}

# Reset to default directory
await reset_working_directory()
```

## 🎯 LLM Usage Guidelines

### Essential Instructions for AI Assistants

**Before using any tools, always set the working directory first:**
```python
await set_working_directory({"path": "D:/Knowledge"})
```

**Important Notes:**
1. **Strict JSON Format**: Always follow JSON data format strictly when calling MCP tools, ensure all brackets are properly aligned
2. **Long Text Strategy**: For long text output or multi-step tasks, create a plan first and execute step by step. Use `write_file` to create files, write the beginning, then use `append_to_file` in subsequent conversations
3. **Search First**: When I mention a note, always search for its title first using `search_files` (I rarely use exact full names)
4. **Open After Modification**: Always choose to open files after modification using `open_after_write=True` or similar parameters
5. **Task Summary**: After completing tasks, always summarize all modified or created notes (provide links)

**Understanding Obsidian:**
1. **File Names as Titles**: In Obsidian, file names serve as the main title (level 0 heading), so no additional titles are needed as note names

**Output Format:**
1. **Math Blocks**: Use double dollar signs for math blocks, single dollar signs for inline math
2. **YAML Integrity**: Obsidian YAML must start at the first line. When modifying YAML, ensure you don't break this validity

**Small Conventions:**
1. **Project Completion**: When a project is completed, add this YAML property: `done: true`

## 📚 Detailed LLM Guide

For comprehensive LLM usage instructions, see the [LLM Usage Guide](LLM_使用指南.md) which provides detailed examples, best practices, and troubleshooting tips.

## 💡 Usage Examples

### Basic File Operations
```python
# Set working directory first
await set_working_directory({"path": "D:/Knowledge"})

# Read file
content = await read_file({"file_path": "notes/readme.md"})

# Write file and open in Obsidian (recommended)
await write_file({
    "file_path": "notes/new_note.md", 
    "content": "# New Note\nThis is content",
    "create_dirs": True,
    "open_after_write": True
})

# Open existing note in Obsidian
await open_note({
    "file_path": "notes/existing_note.md"
})

# List directory
listing = await list_directory({"directory_path": "notes"})

# Search content (always search first when note name is mentioned)
results = await search_files({
    "search_term": "TODO",
    "directory_path": "notes",
    "limit": 50
})
```

### Partial File Editing
```python
# Append content to end of file
await append_to_file({
    "file_path": "notes/log.md",
    "content": "\n## New Record\n- Completed feature development"
})

# Insert content at specific line
await insert_into_file({
    "file_path": "notes/todo.md",
    "line_number": 3,
    "content": "- [ ] New task"
})

# Replace text
await replace_in_file({
    "file_path": "notes/config.md",
    "search_text": "old_value",
    "replace_text": "new_value"
})

# Delete specific lines
await delete_from_file({
    "file_path": "notes/temp.md",
    "line_start": 5,
    "line_end": 10
})
```

### Dynamic Path Management
```python
# Switch to new working directory
await set_working_directory({"path": "/projects/current"})

# Get current directory info
info = await get_working_directory()
print(f"Current directory: {info['current_directory']}")

# Reset to default directory
await reset_working_directory()
```

## 🛡️ Security Features

### Access Restrictions
- **Root Directory Restriction**: All file operations confined to preset root directory and its subdirectories
- **Path Resolution**: Automatic relative path resolution to prevent directory traversal attacks
- **Boundary Checking**: Strict verification of all operation paths within allowed scope

### File Type Control
```python
# Allowed file extensions
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
```

### Size Limits
- **Maximum File Size**: 10MB to prevent memory overflow
- **Search Result Limit**: Default 200, maximum 5000 results

## 🔍 Troubleshooting

### Common Issues

**Server Won't Start**
```bash
# Check Python version
python --version

# Check MCP installation
python -c "import mcp"
```

**Permission Errors**
- Ensure target directory exists and has read/write permissions
- Check if file path is within root directory scope
- Verify file type is in allowed list

**File Operation Failures**
- Check if file is locked by another program
- Confirm file encoding is UTF-8
- Verify file size doesn't exceed limits

### Debugging Methods
1. Check server console output
2. Verify environment variable settings
3. Check file path permissions
4. Test basic functionality with simple files

## 🤝 Contributing

We welcome community contributions! Here's how you can participate:

### Reporting Issues
- Use GitHub Issues to report bugs or suggest features
- Provide detailed error information and reproduction steps

### Submitting Code
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

### Development Guidelines
- Follow existing code style
- Add appropriate unit tests
- Update relevant documentation
- Ensure backward compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to the [Model Context Protocol](https://modelcontextprotocol.io) team
- Thanks to all contributors and users

---

**Note**: Understand the risks of file operations before use, and regularly backup important data.

For questions, check [Issues](https://github.com/your-repo/issues) or submit a new issue.

---

[中文文档](README_zh-CN.md) | [English Documentation](README.md)
