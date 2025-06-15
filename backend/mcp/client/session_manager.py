"""
MCP会话管理器

负责管理多个MCP客户端连接，提供统一的访问接口。
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from .mcp_client import MCPClient
from ..schemas.protocol import Tool, Resource, Prompt, ToolResult, ResourceContent, PromptResult
from ..schemas.exceptions import MCPError, MCPConnectionError
from backend.utils.logging import app_logger
from backend.core.config import settings


class MCPSessionManager:
    """MCP会话管理器"""
    
    def __init__(self):
        self._clients: Dict[int, MCPClient] = {}
        self._connection_locks: Dict[int, asyncio.Lock] = {}
        self._initialized = False
    
    async def initialize(self, user_id: int = None) -> None:
        """初始化会话管理器"""
        if self._initialized:
            return
        
        try:
            app_logger.info("初始化MCP会话管理器")
            
            if not settings.MCP_ENABLED:
                app_logger.info("MCP功能已禁用")
                return
            
            # 初始化系统级配置的MCP服务器（如果有）
            for server_key, server_config in settings.MCP_SERVERS.items():
                if server_config.get("enabled", False):
                    try:
                        # 对于配置文件中的服务器，使用负数ID来区分
                        # 这样就不会与数据库ID冲突
                        server_id = hash(server_key) % 1000000  # 生成一个正数ID
                        if server_id in self._clients:
                            server_id = -server_id  # 如果冲突，使用负数
                        await self._connect_server(server_id, server_config)
                    except Exception as e:
                        app_logger.error(f"连接系统级MCP服务器失败 {server_key}: {e}")
                        # 继续尝试连接其他服务器
                        continue
            
            # 如果提供了user_id，加载用户的服务器
            if user_id is not None:
                await self._load_user_servers(user_id)
            
            self._initialized = True
            app_logger.info(f"MCP会话管理器初始化完成，已连接 {len(self._clients)} 个服务器")
            
        except Exception as e:
            app_logger.error(f"初始化MCP会话管理器失败: {e}")
            raise
    
    async def _load_user_servers(self, user_id: int) -> None:
        """加载用户的MCP服务器"""
        try:
            from backend.db.session import get_async_session
            from backend.crud.mcp_server import mcp_server
            
            async for db in get_async_session():
                # 获取用户启用且自动启动的服务器
                servers = await mcp_server.get_user_servers(db, user_id=user_id, skip=0, limit=1000)
                
                for server in servers:
                    if server.enabled and server.auto_start:
                        try:
                            await self._connect_server(server.id, server.to_config_dict())
                        except Exception as e:
                            app_logger.error(f"连接用户MCP服务器失败 ID {server.id} ({server.name}): {e}")
                            continue
                break
        except Exception as e:
            app_logger.error(f"加载用户MCP服务器失败: {e}")

    async def load_user_servers_for_user(self, user_id: int) -> None:
        """为特定用户加载MCP服务器（动态调用）"""
        if not self._initialized:
            await self.initialize(user_id)
        else:
            await self._load_user_servers(user_id)
    
    async def shutdown(self) -> None:
        """关闭所有连接"""
        app_logger.info("关闭MCP会话管理器")
        
        disconnect_tasks = []
        for client in self._clients.values():
            disconnect_tasks.append(client.disconnect())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self._clients.clear()
        self._connection_locks.clear()
        self._initialized = False
        
        app_logger.info("MCP会话管理器已关闭")
    
    async def _connect_server(self, server_id: int, server_config: Dict[str, Any]) -> None:
        """连接单个MCP服务器"""
        server_name = server_config.get("name", f"server_{server_id}")
        app_logger.info(f"连接MCP服务器: {server_name} (ID: {server_id})")
        
        client = MCPClient(
            name=server_name,
            version="1.0.0",
            timeout=settings.MCP_CONNECTION_TIMEOUT,
            retry_attempts=settings.MCP_RETRY_ATTEMPTS,
            retry_delay=settings.MCP_RETRY_DELAY
        )
        
        # 准备连接参数
        transport_type = server_config.get("type", "stdio")
        # 过滤掉数据库和控制字段，只保留传输层需要的参数
        excluded_fields = [
            "enabled", "type", "description", "transport_type", 
            "auto_start", "is_public", "share_link", "config", "tags",
            "retry_attempts", "retry_delay", "name"  # 这些已经在MCPClient构造函数中处理
        ]
        transport_config = {
            key: value for key, value in server_config.items()
            if key not in excluded_fields
        }
        
        # 连接
        await client.connect(transport_type, **transport_config)
        
        # 保存客户端和锁，使用数据库ID作为key
        self._clients[server_id] = client
        self._connection_locks[server_id] = asyncio.Lock()
        
        app_logger.info(f"MCP服务器连接成功: {server_name} (ID: {server_id})")
    
    async def add_server(self, server_id: int, server_config: Dict[str, Any]) -> None:
        """动态添加MCP服务器"""
        if server_id in self._clients:
            app_logger.warning(f"MCP服务器已存在: ID {server_id}")
            return
        
        try:
            await self._connect_server(server_id, server_config)
            app_logger.info(f"动态添加MCP服务器成功: ID {server_id}")
        except Exception as e:
            app_logger.error(f"动态添加MCP服务器失败 ID {server_id}: {e}")
            raise
    
    async def remove_server(self, server_id: int) -> None:
        """移除MCP服务器"""
        if server_id not in self._clients:
            app_logger.warning(f"MCP服务器不存在: ID {server_id}")
            return
        
        try:
            client = self._clients[server_id]
            await client.disconnect()
            
            del self._clients[server_id]
            del self._connection_locks[server_id]
            
            app_logger.info(f"移除MCP服务器成功: ID {server_id}")
        except Exception as e:
            app_logger.error(f"移除MCP服务器失败 ID {server_id}: {e}")
            raise
    
    async def reconnect_server(self, server_id: int) -> None:
        """重连MCP服务器"""
        if server_id not in self._clients:
            app_logger.error(f"MCP服务器不存在: ID {server_id}")
            return
        
        async with self._connection_locks[server_id]:
            try:
                client = self._clients[server_id]
                
                # 如果已连接，先断开
                if client.is_connected:
                    await client.disconnect()
                
                # 获取原始配置重新连接
                server_config = settings.MCP_SERVERS.get(server_id)
                if not server_config:
                    app_logger.error(f"找不到MCP服务器配置: ID {server_id}")
                    return
                
                # 重新连接
                transport_type = server_config.get("type", "stdio")
                # 过滤掉数据库和控制字段，只保留传输层需要的参数
                excluded_fields = [
                    "enabled", "type", "description", "transport_type", 
                    "auto_start", "is_public", "share_link", "config", "tags",
                    "retry_attempts", "retry_delay", "name"  # 这些已经在MCPClient构造函数中处理
                ]
                transport_config = {
                    key: value for key, value in server_config.items()
                    if key not in excluded_fields
                }
                
                await client.connect(transport_type, **transport_config)
                app_logger.info(f"MCP服务器重连成功: ID {server_id}")
                
            except Exception as e:
                app_logger.error(f"MCP服务器重连失败 ID {server_id}: {e}")
                raise
    
    def get_client(self, server_id: int) -> Optional[MCPClient]:
        """获取MCP客户端"""
        return self._clients.get(server_id)
    
    def list_servers(self) -> List[int]:
        """获取所有服务器ID"""
        return list(self._clients.keys())
    
    def get_connected_servers(self) -> List[int]:
        """获取已连接的服务器"""
        connected = []
        for id, client in self._clients.items():
            if client.is_connected:
                connected.append(id)
        return connected
    
    async def get_server_status(self, server_id: int) -> Dict[str, Any]:
        """获取服务器状态"""
        if server_id not in self._clients:
            return {"exists": False}
        
        client = self._clients[server_id]
        
        status = {
            "exists": True,
            "connected": client.is_connected,
            "server_info": client.server_info.model_dump() if client.server_info else None,
            "capabilities": client.capabilities,
            "protocol_version": client.protocol_version,
            "tools": [],
            "resources": [],
            "prompts": []
        }
        
        # 测试连接
        if client.is_connected:
            try:
                status["ping_ok"] = await client.ping()
                
                # 获取可用的工具、资源和提示
                # 检查服务器能力，只获取服务器声明支持的功能
                capabilities = client.capabilities or {}
                
                # 工具功能 - 大多数MCP服务器都支持
                if capabilities.get("tools") is not None:
                    try:
                        tools = await client.list_tools()
                        status["tools"] = [tool.model_dump() for tool in tools]
                    except Exception as e:
                        app_logger.warning(f"获取服务器 ID {server_id} 工具列表失败: {e}")
                else:
                    app_logger.debug(f"服务器 ID {server_id} 不声明支持工具功能")
                
                # 资源功能 - 只有声明支持时才获取
                if capabilities.get("resources") is not None:
                    try:
                        resources = await client.list_resources()
                        status["resources"] = [resource.model_dump() for resource in resources]
                    except Exception as e:
                        app_logger.warning(f"获取服务器 ID {server_id} 资源列表失败: {e}")
                else:
                    app_logger.debug(f"服务器 ID {server_id} 不支持资源功能")
                
                # 提示功能 - 只有声明支持时才获取
                if capabilities.get("prompts") is not None:
                    try:
                        prompts = await client.list_prompts()
                        status["prompts"] = [prompt.model_dump() for prompt in prompts]
                    except Exception as e:
                        app_logger.warning(f"获取服务器 ID {server_id} 提示列表失败: {e}")
                else:
                    app_logger.debug(f"服务器 ID {server_id} 不支持提示功能")
                    
            except Exception:
                status["ping_ok"] = False
        else:
            status["ping_ok"] = False
        
        return status
    
    async def list_all_tools(self, force_refresh: bool = False) -> Dict[int, List[Tool]]:
        """获取所有服务器的工具列表"""
        all_tools = {}
        
        for server_id, client in self._clients.items():
            if not client.is_connected:
                app_logger.warning(f"服务器 ID {server_id} 未连接，跳过工具列表获取")
                continue
            
            try:
                app_logger.info(f"开始获取服务器 ID {server_id} 的工具列表")
                tools = await client.list_tools(force_refresh)
                all_tools[server_id] = tools
                app_logger.info(f"成功获取服务器 ID {server_id} 的 {len(tools)} 个工具")
            except Exception as e:
                app_logger.error(f"获取服务器工具列表失败 ID {server_id}: {e}")
                all_tools[server_id] = []
        
        return all_tools
    
    async def list_all_resources(self, force_refresh: bool = False) -> Dict[int, List[Resource]]:
        """获取所有服务器的资源列表"""
        all_resources = {}
        
        for server_id, client in self._clients.items():
            if not client.is_connected:
                continue
            
            try:
                resources = await client.list_resources(force_refresh)
                all_resources[server_id] = resources
            except Exception as e:
                app_logger.error(f"获取服务器资源列表失败 ID {server_id}: {e}")
                all_resources[server_id] = []
        
        return all_resources
    
    async def list_all_prompts(self, force_refresh: bool = False) -> Dict[int, List[Prompt]]:
        """获取所有服务器的提示列表"""
        all_prompts = {}
        
        for server_id, client in self._clients.items():
            if not client.is_connected:
                continue
            
            try:
                prompts = await client.list_prompts(force_refresh)
                all_prompts[server_id] = prompts
            except Exception as e:
                app_logger.error(f"获取服务器提示列表失败 ID {server_id}: {e}")
                all_prompts[server_id] = []
        
        return all_prompts
    
    async def call_tool(
        self,
        server_id: int,
        tool_name: str,
        arguments: Dict[str, Any] = None
    ) -> ToolResult:
        """调用指定服务器的工具"""
        client = self._clients.get(server_id)
        if not client:
            raise MCPError(f"MCP服务器不存在: ID {server_id}")
        
        if not client.is_connected:
            raise MCPConnectionError(f"MCP服务器未连接: ID {server_id}")
        
        return await client.call_tool(tool_name, arguments)
    
    async def read_resource(self, server_id: int, uri: str) -> ResourceContent:
        """读取指定服务器的资源"""
        client = self._clients.get(server_id)
        if not client:
            raise MCPError(f"MCP服务器不存在: ID {server_id}")
        
        if not client.is_connected:
            raise MCPConnectionError(f"MCP服务器未连接: ID {server_id}")
        
        return await client.read_resource(uri)
    
    async def get_prompt(
        self,
        server_id: int,
        prompt_name: str,
        arguments: Dict[str, Any] = None
    ) -> PromptResult:
        """获取指定服务器的提示"""
        client = self._clients.get(server_id)
        if not client:
            raise MCPError(f"MCP服务器不存在: ID {server_id}")
        
        if not client.is_connected:
            raise MCPConnectionError(f"MCP服务器未连接: ID {server_id}")
        
        return await client.get_prompt(prompt_name, arguments)
    
    async def find_tool(self, tool_name: str) -> Optional[tuple[int, Tool]]:
        """在所有服务器中查找工具"""
        for server_id, client in self._clients.items():
            if not client.is_connected:
                continue
            
            try:
                tools = await client.list_tools()
                for tool in tools:
                    if tool.name == tool_name:
                        return server_id, tool
            except Exception as e:
                app_logger.error(f"查找工具时出错 ID {server_id}: {e}")
                continue
        
        return None
    
    async def find_resource(self, uri: str) -> Optional[tuple[int, Resource]]:
        """在所有服务器中查找资源"""
        for server_id, client in self._clients.items():
            if not client.is_connected:
                continue
            
            try:
                resources = await client.list_resources()
                for resource in resources:
                    if resource.uri == uri:
                        return server_id, resource
            except Exception as e:
                app_logger.error(f"查找资源时出错 ID {server_id}: {e}")
                continue
        
        return None
    
    async def find_prompt(self, prompt_name: str) -> Optional[tuple[int, Prompt]]:
        """在所有服务器中查找提示"""
        for server_id, client in self._clients.items():
            if not client.is_connected:
                continue
            
            try:
                prompts = await client.list_prompts()
                for prompt in prompts:
                    if prompt.name == prompt_name:
                        return server_id, prompt
            except Exception as e:
                app_logger.error(f"查找提示时出错 ID {server_id}: {e}")
                continue
        
        return None
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def __aenter__(self):
        """异步上下文管理器支持"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器清理"""
        await self.shutdown()


# 全局会话管理器实例
mcp_session_manager = MCPSessionManager() 