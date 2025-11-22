"""
本地文件系统 MCP 服务器
为 Obsidian LLM 插件提供文件操作功能
"""

import glob
from pathlib import Path
from typing import List, Optional
import json

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field

# 创建 MCP 服务器实例
mcp = FastMCP(
    "Local File System", 
    instructions="本地文件系统操作服务器，提供文件读写、目录浏览等功能",
    json_response=True,
    stateless_http=True
)


# 数据模型定义
class FileContent(BaseModel):
    """文件内容模型"""
    path: str = Field(description="文件路径")
    content: str = Field(description="文件内容")
    size: int = Field(description="文件大小（字节）")


class DirectoryListing(BaseModel):
    """目录列表模型"""
    path: str = Field(description="目录路径")
    files: List[str] = Field(description="文件列表")
    directories: List[str] = Field(description="子目录列表")


class SearchResult(BaseModel):
    """搜索结果模型"""
    file_path: str = Field(description="文件路径")
    line_number: int = Field(description="行号")
    content: str = Field(description="匹配内容")


class NoteInfo(BaseModel):
    """笔记信息模型"""
    title: str = Field(description="笔记标题")
    path: str = Field(description="笔记路径")
    size: int = Field(description="文件大小")
    created_time: Optional[str] = Field(description="创建时间")
    modified_time: Optional[str] = Field(description="修改时间")


# 工具定义
@mcp.tool()
async def read_file(ctx: Context[ServerSession, None], file_path: str) -> FileContent:
    """
    读取文件内容
    
    Args:
        file_path: 要读取的文件路径
        
    Returns:
        FileContent: 文件内容和元数据
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")
            
        # 安全检查：防止读取敏感文件
        if is_sensitive_file(path):
            raise PermissionError(f"不允许读取敏感文件: {file_path}")
            
        content = path.read_text(encoding='utf-8')
        size = path.stat().st_size
        
        await ctx.info(f"成功读取文件: {file_path} ({size} 字节)")
        
        return FileContent(
            path=str(path),
            content=content,
            size=size
        )
        
    except Exception as e:
        await ctx.error(f"读取文件失败: {str(e)}")
        raise


@mcp.tool()
async def write_file(ctx: Context[ServerSession, None], file_path: str, content: str) -> str:
    """
    写入或编辑文件
    
    Args:
        file_path: 要写入的文件路径
        content: 要写入的内容
        
    Returns:
        str: 操作结果消息
    """
    try:
        path = Path(file_path)
        
        # 安全检查
        if is_sensitive_file(path):
            raise PermissionError(f"不允许写入敏感文件: {file_path}")
            
        # 确保目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        path.write_text(content, encoding='utf-8')
        
        await ctx.info(f"成功写入文件: {file_path}")
        
        return f"文件已成功写入: {file_path}"
        
    except Exception as e:
        await ctx.error(f"写入文件失败: {str(e)}")
        raise


@mcp.tool()
def list_directory(directory_path: str = ".", ctx: Context[ServerSession, None]) -> DirectoryListing:
    """
    列出目录内容
    
    Args:
        directory_path: 要列出的目录路径，默认为当前目录
        
    Returns:
        DirectoryListing: 目录内容列表
    """
    try:
        path = Path(directory_path)
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
            
        if not path.is_dir():
            raise ValueError(f"路径不是目录: {directory_path}")
            
        # 获取文件和目录列表
        files = []
        directories = []
        
        for item in path.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                directories.append(item.name)
                
        await ctx.info(f"列出目录: {directory_path} (找到 {len(files)} 个文件, {len(directories)} 个目录)")
        
        return DirectoryListing(
            path=str(path),
            files=sorted(files),
            directories=sorted(directories)
        )
        
    except Exception as e:
        await ctx.error(f"列出目录失败: {str(e)}")
        raise


@mcp.tool()
def search_files(search_term: str, directory_path: str = ".", file_pattern: str = "*.md", ctx: Context[ServerSession, None]) -> List[SearchResult]:
    """
    在文件中搜索文本
    
    Args:
        search_term: 要搜索的文本
        directory_path: 搜索的目录路径
        file_pattern: 文件匹配模式，默认为 *.md
        
    Returns:
        List[SearchResult]: 搜索结果列表
    """
    try:
        path = Path(directory_path)
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
            
        results = []
        
        # 使用 glob 匹配文件
        pattern = str(path / "**" / file_pattern)
        for file_path in glob.glob(pattern, recursive=True):
            file_path_obj = Path(file_path)
            
            # 跳过敏感文件
            if is_sensitive_file(file_path_obj):
                continue
                
            if file_path_obj.is_file():
                try:
                    content = file_path_obj.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        if search_term.lower() in line.lower():
                            results.append(SearchResult(
                                file_path=str(file_path_obj),
                                line_number=line_num,
                                content=line.strip()
                            ))
                            
                except Exception as e:
                    # 跳过无法读取的文件
                    continue
                    
        await ctx.info(f"搜索完成: 在 {directory_path} 中找到 {len(results)} 个匹配项")
        
        return results
        
    except Exception as e:
        await ctx.error(f"搜索文件失败: {str(e)}")
        raise


@mcp.tool()
def create_note(title: str, content: str = "", directory_path: str = ".", ctx: Context[ServerSession, None]) -> str:
    """
    创建新的 Obsidian 笔记
    
    Args:
        title: 笔记标题
        content: 笔记内容
        directory_path: 保存笔记的目录路径
        
    Returns:
        str: 创建结果消息
    """
    try:
        # 清理标题，确保是有效的文件名
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not clean_title:
            clean_title = "untitled_note"
            
        # 添加 .md 扩展名
        if not clean_title.endswith('.md'):
            clean_title += '.md'
            
        file_path = Path(directory_path) / clean_title
        
        # 写入文件
        file_path.write_text(content, encoding='utf-8')
        
        await ctx.info(f"创建笔记: {clean_title}")
        
        return f"笔记已创建: {file_path}"
        
    except Exception as e:
        await ctx.error(f"创建笔记失败: {str(e)}")
        raise


@mcp.tool()
def get_note_info(note_path: str, ctx: Context[ServerSession, None]) -> NoteInfo:
    """
    获取 Obsidian 笔记信息
    
    Args:
        note_path: 笔记文件路径
        
    Returns:
        NoteInfo: 笔记信息
    """
    try:
        path = Path(note_path)
        if not path.exists():
            raise FileNotFoundError(f"笔记不存在: {note_path}")
            
        if not path.is_file():
            raise ValueError(f"路径不是文件: {note_path}")
            
        stat = path.stat()
        
        # 从文件名提取标题（去掉扩展名）
        title = path.stem
        
        return NoteInfo(
            title=title,
            path=str(path),
            size=stat.st_size,
            created_time=str(stat.st_ctime),
            modified_time=str(stat.st_mtime)
        )
        
    except Exception as e:
        await ctx.error(f"获取笔记信息失败: {str(e)}")
        raise


# 资源定义
@mcp.resource("file://{path}")
def get_file_resource(path: str) -> str:
    """
    文件内容资源
    
    Args:
        path: 文件路径
        
    Returns:
        str: 文件内容
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return f"文件不存在: {path}"
        
    if is_sensitive_file(file_path):
        return "不允许读取敏感文件"
        
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception:
        return "无法读取文件内容"


@mcp.resource("dir://{path}")
def get_directory_resource(path: str) -> str:
    """
    目录列表资源
    
    Args:
        path: 目录路径
        
    Returns:
        str: 目录内容 JSON 格式
    """
    dir_path = Path(path)
    if not dir_path.exists() or not dir_path.is_dir():
        return f"目录不存在: {path}"
        
    try:
        files = []
        directories = []
        
        for item in dir_path.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                directories.append(item.name)
                
        result = {
            "path": str(dir_path),
            "files": sorted(files),
            "directories": sorted(directories)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception:
        return "无法读取目录内容"


# 安全辅助函数
def is_sensitive_file(file_path: Path) -> bool:
    """
    检查文件是否为敏感文件
    
    Args:
        file_path: 文件路径对象
        
    Returns:
        bool: 是否为敏感文件
    """
    sensitive_patterns = [
        # 系统文件
        '/etc/passwd', '/etc/shadow', '/etc/hosts',
        # 配置文件
        '.env', '.config', '.ssh', '.aws',
        # 数据库文件
        '.db', '.sqlite', '.mdb',
        # 日志文件
        '.log',
        # 可执行文件
        '.exe', '.bat', '.sh',
    ]
    
    abs_path = str(file_path.absolute()).lower()
    
    # 检查是否匹配敏感模式
    for pattern in sensitive_patterns:
        if pattern in abs_path:
            return True
            
    # 检查是否在系统目录中
    system_dirs = [
        '/windows/', '/system32/', '/program files/',
        '/etc/', '/var/', '/usr/bin/', '/usr/sbin/'
    ]
    
    for sys_dir in system_dirs:
        if sys_dir in abs_path:
            return True
            
    return False


# 运行服务器
if __name__ == "__main__":
    print("启动本地文件系统 MCP 服务器...")
    print("服务器将在 http://localhost:8000/mcp 运行")
    print("按 Ctrl+C 停止服务器")
    
    mcp.run(transport="streamable-http", host="localhost", port=8000)
