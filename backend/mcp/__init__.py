"""
Model Context Protocol (MCP) 集成模块

提供MCP客户端和服务器的完整实现，支持：
- 多种传输协议（stdio, SSE, WebSocket）
- 工具调用
- 资源访问
- 提示管理
- 采样支持
"""

__version__ = "1.0.0"
__author__ = "FreeWrite Team"

from .client.mcp_client import MCPClient
from .client.session_manager import MCPSessionManager
from .client.transport import StdioTransport, SSETransport
from .schemas.protocol import *

__all__ = [
    "MCPClient",
    "MCPSessionManager", 
    "StdioTransport",
    "SSETransport",
] 