"""
MCP 文件系统服务器配置
支持环境变量和动态配置
"""

import os
from pathlib import Path
from typing import Optional


class MCPConfig:
    """MCP 文件系统服务器配置管理"""
    
    def __init__(self):
        self._root_path: Optional[Path] = None
        self._load_config()
    
    def _load_config(self):
        """从环境变量加载配置"""
        # 优先使用环境变量
        env_root = os.getenv("MCP_FILESYSTEM_ROOT")
        if env_root:
            self._root_path = Path(env_root).expanduser().resolve()
        else:
            # 默认路径
            self._root_path = Path("D:/Ariane故事集").expanduser().resolve()
    
    def get_root(self) -> Path:
        """获取当前根目录"""
        if self._root_path is None:
            raise RuntimeError("配置未正确初始化")
        return self._root_path
    
    def set_root(self, new_root: str) -> str:
        """设置新的根目录"""
        new_path = Path(new_root).expanduser().resolve()
        
        # 验证路径
        if not new_path.exists():
            raise FileNotFoundError(f"路径不存在：{new_path}")
        if not new_path.is_dir():
            raise ValueError(f"路径不是目录：{new_path}")
        
        self._root_path = new_path
        return str(new_path)
    
    def reset_to_default(self) -> str:
        """重置到默认配置"""
        self._load_config()
        return str(self._root_path)


# 全局配置实例
config = MCPConfig()

# 向后兼容的ROOT函数
def ROOT() -> Path:
    """获取当前根目录（兼容性函数）"""
    return config.get_root()
