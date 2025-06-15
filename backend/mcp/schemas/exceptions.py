"""
MCP异常类定义

定义了MCP协议中可能出现的各种异常情况。
"""

from typing import Any, Dict, Optional


class MCPError(Exception):
    """MCP基础异常"""
    
    def __init__(self, message: str, code: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}
        

class MCPConnectionError(MCPError):
    """MCP连接异常"""
    
    def __init__(self, message: str = "连接到MCP服务器失败", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32001, data=data)


class MCPTimeoutError(MCPError):
    """MCP超时异常"""
    
    def __init__(self, message: str = "MCP请求超时", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32002, data=data)


class MCPProtocolError(MCPError):
    """MCP协议异常"""
    
    def __init__(self, message: str = "MCP协议错误", code: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        # 如果没有提供code，使用默认值
        actual_code = code if code is not None else -32603
        super().__init__(message, code=actual_code, data=data)


class MCPServerError(MCPError):
    """MCP服务器异常"""
    
    def __init__(self, message: str = "MCP服务器内部错误", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32000, data=data)


class MCPParseError(MCPError):
    """MCP解析异常"""
    
    def __init__(self, message: str = "JSON解析错误", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32700, data=data)


class MCPInvalidRequestError(MCPError):
    """MCP无效请求异常"""
    
    def __init__(self, message: str = "无效的请求", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32600, data=data)


class MCPMethodNotFoundError(MCPError):
    """MCP方法未找到异常"""
    
    def __init__(self, message: str = "方法未找到", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32601, data=data)


class MCPInvalidParamsError(MCPError):
    """MCP无效参数异常"""
    
    def __init__(self, message: str = "无效的参数", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32602, data=data)


class MCPCapabilityError(MCPError):
    """MCP能力异常"""
    
    def __init__(self, message: str = "不支持的能力", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32003, data=data)


class MCPResourceError(MCPError):
    """MCP资源异常"""
    
    def __init__(self, message: str = "资源操作失败", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32004, data=data)


class MCPToolError(MCPError):
    """MCP工具异常"""
    
    def __init__(self, message: str = "工具调用失败", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32005, data=data)


def create_mcp_error_from_code(code: int, message: str, data: Optional[Dict[str, Any]] = None) -> MCPError:
    """根据错误码创建对应的异常"""
    error_classes = {
        -32700: MCPParseError,
        -32600: MCPInvalidRequestError,
        -32601: MCPMethodNotFoundError,
        -32602: MCPInvalidParamsError,
        -32603: MCPProtocolError,
        -32000: MCPServerError,
        -32001: MCPConnectionError,
        -32002: MCPTimeoutError,
        -32003: MCPCapabilityError,
        -32004: MCPResourceError,
        -32005: MCPToolError,
    }
    
    error_class = error_classes.get(code, MCPError)
    
    # 对于MCPProtocolError，需要传递code参数
    if error_class == MCPProtocolError:
        return error_class(message, code=code, data=data)
    # 对于其他异常类，只传递message和data
    elif error_class in [MCPParseError, MCPInvalidRequestError, MCPMethodNotFoundError, 
                        MCPInvalidParamsError, MCPServerError, MCPConnectionError, 
                        MCPTimeoutError, MCPCapabilityError, MCPResourceError, MCPToolError]:
        return error_class(message, data=data)
    # 对于基础MCPError类，传递所有参数
    else:
        return error_class(message, code=code, data=data) 