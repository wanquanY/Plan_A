"""
MCP协议数据结构定义

定义了MCP协议中使用的所有数据结构，包括消息、工具、资源、提示等。
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum
import json


class MCPVersion(str, Enum):
    """MCP协议版本"""
    V1 = "2024-11-05"


class MessageType(str, Enum):
    """消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class RequestMethod(str, Enum):
    """请求方法"""
    INITIALIZE = "initialize"
    PING = "ping"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    SUBSCRIBE_RESOURCE = "resources/subscribe"
    UNSUBSCRIBE_RESOURCE = "resources/unsubscribe"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    COMPLETE = "completion/complete"
    SET_LOGGING_LEVEL = "logging/setLevel"


class NotificationType(str, Enum):
    """通知类型"""
    INITIALIZED = "notifications/initialized"
    CANCELLED = "notifications/cancelled"
    PROGRESS = "notifications/progress"
    RESOURCE_UPDATED = "notifications/resources/updated"
    RESOURCE_LIST_CHANGED = "notifications/resources/list_changed"
    TOOL_LIST_CHANGED = "notifications/tools/list_changed"
    PROMPT_LIST_CHANGED = "notifications/prompts/list_changed"
    LOG_MESSAGE = "notifications/message"


class LoggingLevel(str, Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class MCPError(BaseModel):
    """MCP错误"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPMessage(BaseModel):
    """MCP基础消息"""
    jsonrpc: str = "2.0"


class MCPRequest(MCPMessage):
    """MCP请求"""
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(MCPMessage):
    """MCP响应"""
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None


class MCPNotification(MCPMessage):
    """MCP通知"""
    method: str
    params: Optional[Dict[str, Any]] = None


class ClientCapabilities(BaseModel):
    """客户端能力"""
    experimental: Dict[str, Any] = Field(default_factory=dict)
    sampling: Dict[str, Any] = Field(default_factory=dict)


class ServerCapabilities(BaseModel):
    """服务器能力"""
    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None


class Implementation(BaseModel):
    """实现信息"""
    name: str
    version: str


class InitializeRequest(BaseModel):
    """初始化请求参数"""
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class InitializeResponse(BaseModel):
    """初始化响应结果"""
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation


class ToolInputSchema(BaseModel):
    """工具输入schema"""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class Tool(BaseModel):
    """工具定义"""
    name: str
    description: Optional[str] = None
    inputSchema: ToolInputSchema


class ToolCall(BaseModel):
    """工具调用"""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """工具执行结果"""
    content: List[Dict[str, Any]] = Field(default_factory=list)
    isError: bool = False


class Resource(BaseModel):
    """资源定义"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ResourceContent(BaseModel):
    """资源内容"""
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[bytes] = None


class Prompt(BaseModel):
    """提示定义"""
    name: str
    description: Optional[str] = None
    arguments: List[Dict[str, Any]] = Field(default_factory=list)


class PromptMessage(BaseModel):
    """提示消息"""
    role: Literal["user", "assistant", "system"]
    content: Union[str, List[Dict[str, Any]]]


class PromptResult(BaseModel):
    """提示结果"""
    description: Optional[str] = None
    messages: List[PromptMessage] = Field(default_factory=list)


class ProgressToken(BaseModel):
    """进度令牌"""
    token: Union[str, int]
    
    
class LogMessage(BaseModel):
    """日志消息"""
    level: LoggingLevel
    data: Any
    logger: Optional[str] = None


class CancelledNotification(BaseModel):
    """取消通知"""
    requestId: Union[str, int]
    reason: Optional[str] = None


class ProgressNotification(BaseModel):
    """进度通知"""
    progressToken: Union[str, int]
    progress: int
    total: Optional[int] = None


# 工厂函数
def create_request(id: Union[str, int], method: str, params: Optional[Dict[str, Any]] = None) -> MCPRequest:
    """创建MCP请求"""
    return MCPRequest(id=id, method=method, params=params)


def create_response(id: Union[str, int], result: Optional[Dict[str, Any]] = None, 
                   error: Optional[MCPError] = None) -> MCPResponse:
    """创建MCP响应"""
    return MCPResponse(id=id, result=result, error=error)


def create_notification(method: str, params: Optional[Dict[str, Any]] = None) -> MCPNotification:
    """创建MCP通知"""
    return MCPNotification(method=method, params=params)


def create_error(code: int, message: str, data: Optional[Dict[str, Any]] = None) -> MCPError:
    """创建MCP错误"""
    return MCPError(code=code, message=message, data=data)


# 常见错误码
class ErrorCode:
    """错误码定义"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP特定错误码
    SERVER_ERROR = -32000
    CONNECTION_ERROR = -32001
    TIMEOUT_ERROR = -32002
    CAPABILITY_ERROR = -32003
    RESOURCE_ERROR = -32004
    TOOL_ERROR = -32005 