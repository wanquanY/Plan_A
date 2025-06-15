"""
MCP客户端核心实现

提供完整的MCP客户端功能，包括：
- 连接管理
- 消息收发
- 工具调用
- 资源访问
- 提示管理
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union, Callable, AsyncIterator
from .transport import Transport, create_transport
from ..schemas.protocol import (
    MCPRequest, MCPResponse, MCPNotification,
    Tool, ToolCall, ToolResult,
    Resource, ResourceContent,
    Prompt, PromptResult,
    InitializeRequest, InitializeResponse,
    ClientCapabilities, Implementation,
    RequestMethod, NotificationType,
    create_request, create_response, create_notification, create_error,
    ErrorCode
)
from ..schemas.exceptions import (
    MCPError, MCPConnectionError, MCPTimeoutError, MCPProtocolError,
    create_mcp_error_from_code
)
from backend.utils.logging import app_logger


class MCPClient:
    """MCP客户端"""
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        transport_config: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        self.name = name
        self.version = version
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # 传输层
        self.transport: Optional[Transport] = None
        self.transport_config = transport_config or {}
        
        # 连接状态
        self.connected = False
        self.initialized = False
        
        # 协议信息
        self.server_info: Optional[Implementation] = None
        self.server_capabilities: Optional[Dict[str, Any]] = None
        self.protocol_version: Optional[str] = None
        
        # 缓存
        self._tools_cache: List[Tool] = []
        self._resources_cache: List[Resource] = []
        self._prompts_cache: List[Prompt] = []
        
        # 消息处理
        self._request_id_counter = 0
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._notification_handlers: Dict[str, List[Callable]] = {}
        
        # 后台任务
        self._message_handler_task: Optional[asyncio.Task] = None
    
    async def connect(self, transport_type: str = "stdio", **transport_kwargs) -> None:
        """连接到MCP服务器"""
        try:
            app_logger.info(f"连接MCP服务器: {self.name}")
            
            # 创建传输层
            config = {**self.transport_config, **transport_kwargs}
            config["timeout"] = self.timeout
            self.transport = create_transport(transport_type, **config)
            
            # 建立连接
            await self.transport.connect()
            self.connected = True
            
            # 启动消息处理任务
            self._message_handler_task = asyncio.create_task(self._handle_messages())
            
            # 执行初始化握手
            await self._initialize()
            
            app_logger.info(f"MCP客户端连接成功: {self.name}")
            
        except Exception as e:
            app_logger.error(f"连接MCP服务器失败: {e}")
            await self.disconnect()
            raise
    
    async def disconnect(self) -> None:
        """断开连接"""
        app_logger.info(f"断开MCP连接: {self.name}")
        
        # 停止消息处理任务
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass
        
        # 清理待处理的请求
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(MCPConnectionError("连接已断开"))
        self._pending_requests.clear()
        
        # 断开传输层连接
        if self.transport:
            await self.transport.disconnect()
            self.transport = None
        
        # 重置状态
        self.connected = False
        self.initialized = False
        self.server_info = None
        self.server_capabilities = None
        self.protocol_version = None
        
        app_logger.info(f"MCP连接已断开: {self.name}")
    
    async def ping(self) -> bool:
        """发送ping请求测试连接"""
        try:
            await self._send_request(RequestMethod.PING, params={})
            return True
        except Exception as e:
            app_logger.warning(f"MCP ping失败: {e}")
            return False
    
    async def list_tools(self, force_refresh: bool = False) -> List[Tool]:
        """获取可用工具列表"""
        if not force_refresh and self._tools_cache:
            app_logger.debug(f"使用缓存的工具列表，共 {len(self._tools_cache)} 个工具")
            return self._tools_cache
        
        try:
            app_logger.info(f"向服务器 {self.name} 发送工具列表请求")
            # 为工具列表请求使用更长的超时时间（60秒）
            response = await self._send_request(RequestMethod.LIST_TOOLS, params={}, timeout=60.0)
            app_logger.info(f"收到工具列表响应: {response}")
            
            tools_data = response.get("tools", [])
            app_logger.info(f"解析到 {len(tools_data)} 个工具数据")
            self._tools_cache = [Tool(**tool) for tool in tools_data]
            app_logger.info(f"成功解析 {len(self._tools_cache)} 个工具")
            return self._tools_cache
        except Exception as e:
            app_logger.error(f"获取工具列表失败: {e}")
            import traceback
            app_logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        """调用工具"""
        try:
            params = {
                "name": name,
                "arguments": arguments or {}
            }
            
            response = await self._send_request(RequestMethod.CALL_TOOL, params)
            return ToolResult(**response)
            
        except Exception as e:
            app_logger.error(f"调用工具失败 {name}: {e}")
            raise
    
    async def list_resources(self, force_refresh: bool = False) -> List[Resource]:
        """获取可用资源列表"""
        if not force_refresh and self._resources_cache:
            return self._resources_cache
        
        try:
            response = await self._send_request(RequestMethod.LIST_RESOURCES, params={}, timeout=60.0)
            resources_data = response.get("resources", [])
            self._resources_cache = [Resource(**resource) for resource in resources_data]
            return self._resources_cache
        except Exception as e:
            app_logger.error(f"获取资源列表失败: {e}")
            raise
    
    async def read_resource(self, uri: str) -> ResourceContent:
        """读取资源内容"""
        try:
            params = {"uri": uri}
            response = await self._send_request(RequestMethod.READ_RESOURCE, params)
            return ResourceContent(**response)
        except Exception as e:
            app_logger.error(f"读取资源失败 {uri}: {e}")
            raise
    
    async def list_prompts(self, force_refresh: bool = False) -> List[Prompt]:
        """获取可用提示列表"""
        if not force_refresh and self._prompts_cache:
            return self._prompts_cache
        
        try:
            response = await self._send_request(RequestMethod.LIST_PROMPTS, params={}, timeout=60.0)
            prompts_data = response.get("prompts", [])
            self._prompts_cache = [Prompt(**prompt) for prompt in prompts_data]
            return self._prompts_cache
        except Exception as e:
            app_logger.error(f"获取提示列表失败: {e}")
            raise
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> PromptResult:
        """获取提示内容"""
        try:
            params = {
                "name": name,
                "arguments": arguments or {}
            }
            
            response = await self._send_request(RequestMethod.GET_PROMPT, params)
            return PromptResult(**response)
            
        except Exception as e:
            app_logger.error(f"获取提示失败 {name}: {e}")
            raise
    
    def add_notification_handler(self, notification_type: str, handler: Callable) -> None:
        """添加通知处理器"""
        if notification_type not in self._notification_handlers:
            self._notification_handlers[notification_type] = []
        self._notification_handlers[notification_type].append(handler)
    
    def remove_notification_handler(self, notification_type: str, handler: Callable) -> None:
        """移除通知处理器"""
        if notification_type in self._notification_handlers:
            try:
                self._notification_handlers[notification_type].remove(handler)
            except ValueError:
                pass
    
    async def _initialize(self) -> None:
        """执行初始化握手"""
        app_logger.info("开始MCP初始化握手")
        
        # 构建初始化请求
        client_capabilities = ClientCapabilities()
        client_info = Implementation(name=self.name, version=self.version)
        
        init_request = InitializeRequest(
            protocolVersion="2024-11-05",
            capabilities=client_capabilities,
            clientInfo=client_info
        )
        
        try:
            # 发送初始化请求
            response = await self._send_request(
                RequestMethod.INITIALIZE,
                init_request.model_dump()
            )
            
            # 解析响应
            init_response = InitializeResponse(**response)
            self.protocol_version = init_response.protocolVersion
            self.server_capabilities = init_response.capabilities.model_dump() if init_response.capabilities else {}
            self.server_info = init_response.serverInfo
            
            # 发送初始化完成通知
            await self._send_notification(NotificationType.INITIALIZED)
            
            self.initialized = True
            app_logger.info(f"MCP初始化完成: {self.server_info.name} v{self.server_info.version}")
            
        except Exception as e:
            app_logger.error(f"MCP初始化失败: {e}")
            raise MCPProtocolError(f"初始化失败: {e}")
    
    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """发送请求并等待响应"""
        if not self.transport or not self.connected:
            raise MCPConnectionError("未连接到MCP服务器")
        
        request_id = self._generate_request_id()
        request = create_request(request_id, method, params)
        
        # 创建Future等待响应
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # 发送请求
            app_logger.info(f"发送MCP请求: {method}, ID: {request_id}")
            await self.transport.send(request)
            
            # 等待响应
            actual_timeout = timeout or self.timeout
            app_logger.info(f"等待响应，超时时间: {actual_timeout}秒")
            response = await asyncio.wait_for(future, timeout=actual_timeout)
            
            app_logger.info(f"收到响应: {type(response).__name__}")
            if response.error:
                error = response.error
                app_logger.error(f"MCP请求错误: {error.code} - {error.message}")
                raise create_mcp_error_from_code(error.code, error.message, error.data)
            
            result = response.result or {}
            app_logger.info(f"请求成功，结果类型: {type(result)}, 内容: {result}")
            return result
            
        except asyncio.TimeoutError:
            app_logger.error(f"MCP请求超时: {method}, 超时时间: {timeout or self.timeout}秒")
            raise MCPTimeoutError(f"请求超时: {method}")
        finally:
            self._pending_requests.pop(request_id, None)
    
    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """发送通知"""
        if not self.transport or not self.connected:
            raise MCPConnectionError("未连接到MCP服务器")
        
        notification = create_notification(method, params)
        await self.transport.send(notification)
    
    async def _handle_messages(self) -> None:
        """处理接收到的消息"""
        if not self.transport:
            return
        
        try:
            async for message in self.transport.receive():
                try:
                    if isinstance(message, MCPResponse):
                        await self._handle_response(message)
                    elif isinstance(message, MCPNotification):
                        await self._handle_notification(message)
                    elif isinstance(message, MCPRequest):
                        await self._handle_request(message)
                except Exception as e:
                    app_logger.error(f"处理MCP消息失败: {e}")
                    
        except Exception as e:
            app_logger.error(f"消息处理循环异常: {e}")
            self.connected = False
    
    async def _handle_response(self, response: MCPResponse) -> None:
        """处理响应消息"""
        request_id = response.id
        if request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(response)
    
    async def _handle_notification(self, notification: MCPNotification) -> None:
        """处理通知消息"""
        method = notification.method
        if method in self._notification_handlers:
            handlers = self._notification_handlers[method]
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(notification)
                    else:
                        handler(notification)
                except Exception as e:
                    app_logger.error(f"通知处理器异常 {method}: {e}")
    
    async def _handle_request(self, request: MCPRequest) -> None:
        """处理请求消息(客户端通常不需要处理请求)"""
        # 客户端通常不处理来自服务器的请求
        # 如果需要，可以在这里实现
        app_logger.warning(f"收到未处理的请求: {request.method}")
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        self._request_id_counter += 1
        return f"{self.name}_{self._request_id_counter}_{int(time.time() * 1000)}"
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.initialized
    
    @property
    def capabilities(self) -> Dict[str, Any]:
        """获取服务器能力"""
        return self.server_capabilities or {}
    
    async def __aenter__(self):
        """异步上下文管理器支持"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器清理"""
        await self.disconnect() 