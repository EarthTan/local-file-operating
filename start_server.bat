@echo off
echo 启动本地文件系统 MCP 服务器...
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)

REM 检查是否安装了 MCP
python -c "import mcp" >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未安装 MCP SDK，请运行: pip install mcp[cli]
    pause
    exit /b 1
)

echo 服务器使用 stdio 传输协议
echo 按 Ctrl+C 停止服务器
echo.

REM 启动服务器
python local_filesystem_mcp.py
