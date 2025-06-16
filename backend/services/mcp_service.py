"""
MCP服务管理器

提供MCP服务器的连接、管理和工具调用功能。
支持用户级别的配置管理和系统级默认服务。
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from backend.mcp.schemas.protocol import Tool, Resource, Prompt, ToolResult, ResourceContent, PromptResult

from backend.core.config import settings
from backend.utils.logging import app_logger as logger
from backend.mcp.client.session_manager import MCPSessionManager
from backend.mcp.schemas.exceptions import MCPError
from backend.db.session import get_async_session
from backend.crud.mcp_server import mcp_server
from sqlalchemy import select
from backend.utils.id_converter import IDConverter
from backend.models.mcp_server import MCPServer


class MCPService:
    """MCP服务管理器"""
    
    def __init__(self):
        self.session_manager = MCPSessionManager()
        self._initialized = False
    
    async def initialize(self, user_id: int = None) -> None:
        """初始化MCP服务"""
        if self._initialized:
            return
        
        try:
            # 加载系统默认服务器配置（从环境变量）
            await self._load_system_default_servers()
            
            # 初始化会话管理器，可以传入user_id来加载用户服务器
            await self.session_manager.initialize(user_id)
            
            self._initialized = True
            logger.info("MCP服务初始化成功")
            
        except Exception as e:
            logger.error(f"MCP服务初始化失败: {e}")
            raise MCPError(f"MCP服务初始化失败: {e}")
    
    async def shutdown(self) -> None:
        """关闭MCP服务"""
        try:
            await self.session_manager.shutdown()
            logger.info("MCP服务已关闭")
        except Exception as e:
            logger.error(f"关闭MCP服务失败: {e}")
    
    def is_enabled(self) -> bool:
        """检查MCP服务是否启用"""
        return self._initialized and self.session_manager is not None
    
    def get_status(self) -> Dict[str, Any]:
        """获取MCP服务状态"""
        if not self.is_enabled():
            return {
                "enabled": False,
                "server_count": 0,
                "connected_count": 0,
                "active_servers": 0,
                "available_tools": 0,
                "servers": {},
                "healthy": False,
                "message": "MCP服务未启用"
            }
        
        try:
            status = self.session_manager.get_status()
            connected_count = sum(1 for s in status["servers"].values() if s.get("connected", False))
            server_count = len(status["servers"])
            
            return {
                "enabled": True,
                "server_count": server_count,
                "connected_count": connected_count,
                "active_servers": connected_count,
                "available_tools": 0,  # TODO: 计算可用工具数量
                "servers": status["servers"],
                "healthy": connected_count > 0,
                "message": f"已连接 {connected_count}/{server_count} 个服务器"
            }
        except Exception as e:
            logger.error(f"获取MCP状态时出错: {e}")
            return {
                "enabled": True,
                "server_count": 0,
                "connected_count": 0,
                "active_servers": 0,
                "available_tools": 0,
                "servers": {},
                "healthy": False,
                "message": f"获取状态失败: {str(e)}"
            }
    
    async def get_server_status(self, server_id: str, user_id: int = None) -> Dict[str, Any]:
        """获取指定服务器状态"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        # 如果提供了user_id，确保用户服务器已加载
        if user_id is not None:
            await self.ensure_user_servers_loaded(user_id)
        
        # 如果传入的是public_id，需要转换为数据库ID
        if server_id.startswith("mcp-"):
            async for db in get_async_session():
                from backend.utils.id_converter import IDConverter
                db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
                if not db_id:
                    raise MCPError(f"无效的服务器ID: {server_id}")
                
                # 如果提供了user_id，验证用户权限
                if user_id is not None:
                    stmt = select(MCPServer).where(
                        MCPServer.id == db_id,
                        MCPServer.user_id == user_id
                    )
                    result = await db.execute(stmt)
                    server = result.scalar_one_or_none()
                    if not server:
                        raise MCPError(f"服务器不存在或无权限访问: {server_id}")
                break
        else:
            # 假设传入的是数据库ID字符串
            try:
                db_id = int(server_id)
            except ValueError:
                raise MCPError(f"无效的服务器ID: {server_id}")
            
            # 如果提供了user_id，验证用户权限
            if user_id is not None:
                async for db in get_async_session():
                    stmt = select(MCPServer).where(
                        MCPServer.id == db_id,
                        MCPServer.user_id == user_id
                    )
                    result = await db.execute(stmt)
                    server = result.scalar_one_or_none()
                    if not server:
                        raise MCPError(f"服务器不存在或无权限访问: {db_id}")
                    break
            
        return await self.session_manager.get_server_status(db_id)
    
    async def reconnect_server(self, server_id: str, user_id: int = None) -> None:
        """重新连接服务器"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
            
        # 如果传入的是public_id，需要转换为数据库ID
        if server_id.startswith("mcp-"):
            async for db in get_async_session():
                from backend.utils.id_converter import IDConverter
                db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
                if not db_id:
                    raise MCPError(f"无效的服务器ID: {server_id}")
                
                # 如果提供了user_id，验证用户权限
                if user_id is not None:
                    stmt = select(MCPServer).where(
                        MCPServer.id == db_id,
                        MCPServer.user_id == user_id
                    )
                    result = await db.execute(stmt)
                    server = result.scalar_one_or_none()
                    if not server:
                        raise MCPError(f"服务器不存在或无权限访问: {server_id}")
                break
        else:
            # 假设传入的是数据库ID字符串
            try:
                db_id = int(server_id)
            except ValueError:
                raise MCPError(f"无效的服务器ID: {server_id}")
            
            # 如果提供了user_id，验证用户权限
            if user_id is not None:
                async for db in get_async_session():
                    stmt = select(MCPServer).where(
                        MCPServer.id == db_id,
                        MCPServer.user_id == user_id
                    )
                    result = await db.execute(stmt)
                    server = result.scalar_one_or_none()
                    if not server:
                        raise MCPError(f"服务器不存在或无权限访问: {db_id}")
                    break
            
        await self.session_manager.reconnect_server(db_id)
    
    # 用户级别的服务器管理方法
    async def get_user_servers(self, user_id: int, skip: int = 0, limit: int = 100) -> List[MCPServer]:
        """获取用户的MCP服务器配置列表"""
        async for db in get_async_session():
            servers = await mcp_server.get_user_servers(db, user_id=user_id, skip=skip, limit=limit)
            
            # 确保用户服务器已加载到会话管理器中
            if self.is_enabled():
                await self.ensure_user_servers_loaded(user_id)
            
            return servers
            break
    
    async def create_user_server(self, user_id: int, server_data: Dict[str, Any]) -> MCPServer:
        """为用户创建MCP服务器配置"""
        async for db in get_async_session():
            # 检查名称是否已存在（用户级别）
            existing = await mcp_server.get_by_name(db, name=server_data["name"], user_id=user_id)
            if existing:
                raise MCPError(f"服务器名称已存在: {server_data['name']}")
            
            # 创建服务器配置
            server = await mcp_server.create_from_config(
                db, 
                user_id=user_id,
                name=server_data["name"], 
                config=server_data
            )
            
            # 如果启用了自动启动，立即连接
            if server.enabled and server.auto_start and self.is_enabled():
                try:
                    await self.session_manager.add_server(server.id, server.to_config_dict())
                except Exception as e:
                    logger.error(f"连接新创建的服务器失败 ID {server.id}: {e}")
            
            return server
            break
    
    async def update_user_server(self, user_id: int, server_id: int, update_data: Dict[str, Any]) -> MCPServer:
        """更新用户的MCP服务器配置"""
        async for db in get_async_session():
            try:
                # 查询服务器
                stmt = select(MCPServer).where(
                    MCPServer.id == server_id,
                    MCPServer.user_id == user_id
                )
                result = await db.execute(stmt)
                server = result.scalar_one_or_none()
                
                if not server:
                    raise MCPError(f"服务器不存在: ID {server_id}")
                
                old_enabled = server.enabled
                old_config = server.to_config_dict()
                
                # 更新服务器配置
                for key, value in update_data.items():
                    if hasattr(server, key):
                        if key == 'env' and server.env:
                            # 对于环境变量，进行合并而不是替换
                            # 保留原有的环境变量，只更新提供的新值
                            merged_env = server.env.copy()
                            merged_env.update(value)
                            setattr(server, key, merged_env)
                        elif key == 'headers' and server.headers:
                            # 对于HTTP头部，也进行合并
                            merged_headers = server.headers.copy()
                            merged_headers.update(value)
                            setattr(server, key, merged_headers)
                        else:
                            setattr(server, key, value)
                
                await db.commit()
                await db.refresh(server)
                
                # 如果MCP服务已启用，同步更新会话管理器
                if self.is_enabled():
                    try:
                        # 如果启用状态改变
                        if "enabled" in update_data:
                            if update_data["enabled"] and server.auto_start:
                                # 启用服务器
                                await self.session_manager.add_server(server.id, server.to_config_dict())
                            elif not update_data["enabled"]:
                                # 禁用服务器
                                await self.session_manager.remove_server(server.id)
                        # 如果其他配置改变且服务器已启用
                        elif old_enabled and server.enabled:
                            # 重新连接服务器
                            await self.session_manager.remove_server(server.id)
                            if server.auto_start:
                                await self.session_manager.add_server(server.id, server.to_config_dict())
                    except Exception as e:
                        logger.error(f"同步会话管理器失败 ID {server.id}: {e}")
                
                logger.info(f"成功更新用户服务器: user_id={user_id}, server_id={server_id}, server={server}")
                return server
            except MCPError:
                # 重新抛出MCPError，让上层处理
                raise
            except Exception as e:
                logger.error(f"更新用户服务器失败: user_id={user_id}, server_id={server_id}, error={e}")
                raise MCPError(f"更新用户服务器失败: {str(e)}")
            finally:
                await db.close()
            break
    
    async def delete_user_server(self, user_id: int, server_id: int) -> Dict[str, Any]:
        """删除用户的MCP服务器配置"""
        async for db in get_async_session():
            try:
                # 查询服务器
                stmt = select(MCPServer).where(
                    MCPServer.id == server_id,
                    MCPServer.user_id == user_id
                )
                result = await db.execute(stmt)
                server = result.scalar_one_or_none()
                
                if not server:
                    raise MCPError(f"服务器不存在: ID {server_id}")
                
                # 如果MCP服务已启用，从会话管理器中移除
                if self.is_enabled():
                    try:
                        await self.session_manager.remove_server(server.id)
                    except Exception as e:
                        logger.error(f"从会话管理器移除服务器失败 ID {server.id}: {e}")
                
                # 删除数据库记录
                await db.delete(server)
                await db.commit()
                
                return {"message": f"服务器 ID {server_id} 删除成功"}
            finally:
                await db.close()
                break
    
    async def toggle_user_server(self, user_id: int, server_id: int) -> Dict[str, Any]:
        """切换用户MCP服务器的启用状态"""
        logger.info(f"toggle_user_server调用: user_id={user_id}, server_id={server_id}")
        
        async for db in get_async_session():
            try:
                # 查询服务器
                stmt = select(MCPServer).where(
                    MCPServer.id == server_id,
                    MCPServer.user_id == user_id
                )
                logger.info(f"执行查询: MCPServer.id={server_id} AND MCPServer.user_id={user_id}")
                
                result = await db.execute(stmt)
                server = result.scalar_one_or_none()
                
                logger.info(f"查询结果: server={server}")
                
                if not server:
                    # 检查服务器是否存在但用户不匹配
                    stmt2 = select(MCPServer).where(MCPServer.id == server_id)
                    result2 = await db.execute(stmt2)
                    server2 = result2.scalar_one_or_none()
                    
                    if server2:
                        logger.error(f"服务器存在但用户不匹配: server.user_id={server2.user_id}, 期望user_id={user_id}")
                    else:
                        logger.error(f"服务器完全不存在: server_id={server_id}")
                    
                    raise MCPError(f"服务器不存在: ID {server_id}")
                
                # 切换启用状态
                old_enabled = server.enabled
                server.enabled = not server.enabled
                
                logger.info(f"切换状态: {old_enabled} -> {server.enabled}")
                
                await db.commit()
                await db.refresh(server)
                
                action = "启用" if server.enabled else "禁用"
                
                # 如果MCP服务已启用，同步更新会话管理器
                if self.is_enabled():
                    try:
                        if server.enabled and server.auto_start:
                            # 启用服务器
                            await self.session_manager.add_server(server.id, server.to_config_dict())
                        elif not server.enabled:
                            # 禁用服务器
                            await self.session_manager.remove_server(server.id)
                    except Exception as e:
                        logger.error(f"同步会话管理器失败 ID {server.id}: {e}")
                
                result_data = {
                    "server": server,
                    "action": action,
                    "message": f"服务器已{action}"
                }
                logger.info(f"toggle_user_server成功: {result_data}")
                return result_data
            except MCPError:
                # 重新抛出MCPError，让上层处理
                raise
            except Exception as e:
                logger.error(f"切换服务器状态失败: {e}")
                raise MCPError(f"切换服务器状态失败: {str(e)}")
            finally:
                await db.close()
    
    async def toggle_user_server_public(self, user_id: int, server_id: int) -> Dict[str, Any]:
        """切换用户MCP服务器的公开状态"""
        logger.info(f"toggle_user_server_public调用: user_id={user_id}, server_id={server_id}")
        
        async for db in get_async_session():
            try:
                # 查询服务器
                stmt = select(MCPServer).where(
                    MCPServer.id == server_id,
                    MCPServer.user_id == user_id
                )
                logger.info(f"执行查询: MCPServer.id={server_id} AND MCPServer.user_id={user_id}")
                
                result = await db.execute(stmt)
                server = result.scalar_one_or_none()
                
                logger.info(f"查询结果: server={server}")
                
                if not server:
                    raise MCPError(f"服务器不存在: ID {server_id}")
                
                # 切换公开状态
                old_is_public = server.is_public
                server.is_public = not server.is_public
                
                # 如果设置为公开，生成分享链接；如果取消公开，清空分享链接
                if server.is_public:
                    from backend.utils.security import generate_random_string
                    if not server.share_link:
                        server.share_link = f"mcp-share-{generate_random_string(16)}"
                else:
                    server.share_link = None
                
                logger.info(f"切换公开状态: {old_is_public} -> {server.is_public}")
                
                await db.commit()
                await db.refresh(server)
                
                action = "设为公开" if server.is_public else "取消公开"
                
                result_data = {
                    "server": server,
                    "action": action,
                    "message": f"服务器已{action}",
                    "is_public": server.is_public,
                    "share_link": server.share_link
                }
                logger.info(f"toggle_user_server_public成功: {result_data}")
                return result_data
            except MCPError:
                # 重新抛出MCPError，让上层处理
                raise
            except Exception as e:
                logger.error(f"切换服务器公开状态失败: {e}")
                raise MCPError(f"切换服务器公开状态失败: {str(e)}")
            finally:
                await db.close()
    
    async def get_public_servers(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取公开的MCP服务器配置"""
        async for db in get_async_session():
            servers = await mcp_server.get_public_servers(db, skip=skip, limit=limit)
            
            result = []
            for server in servers:
                from backend.utils.security import mask_env_variables, mask_headers
                
                result.append({
                    "public_id": server.public_id,
                    "name": server.name,
                    "description": server.description,
                    "transport_type": server.transport_type,
                    "command": server.command,
                    "args": server.args or [],
                    "env": mask_env_variables(server.env or {}),  # 脱敏环境变量
                    "cwd": server.cwd,
                    "url": server.url,
                    "headers": mask_headers(server.headers or {}),  # 脱敏HTTP头部
                    "enabled": server.enabled,
                    "auto_start": server.auto_start,
                    "timeout": server.timeout,
                    "retry_attempts": server.retry_attempts,
                    "retry_delay": server.retry_delay,
                    "config": server.config or {},
                    "tags": server.tags or [],
                    "created_at": server.created_at.isoformat() if server.created_at else None,
                    "user_id": server.user_id,  # 显示创建者
                    "is_public": server.is_public,
                    "share_link": server.share_link
                })
            
            return result
            break
    
    async def import_user_servers(
        self, 
        user_id: int,
        servers_config: Dict[str, Dict[str, Any]], 
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """批量导入用户的服务器配置"""
        async for db in get_async_session():
            results = await mcp_server.bulk_import(
                db, 
                user_id=user_id,
                servers_config=servers_config, 
                overwrite=overwrite
            )
            
            # 对于新创建和更新的服务器，如果启用了自动启动，尝试连接
            if self.is_enabled():
                for server_name in results["created"] + results["updated"]:
                    try:
                        server = await mcp_server.get_by_name(db, name=server_name, user_id=user_id)
                        if server and server.enabled and server.auto_start:
                            await self.session_manager.add_server(server.name, server.to_config_dict())
                    except Exception as e:
                        logger.error(f"连接导入的服务器失败 {server_name}: {e}")
            
            return results
            break
    
    async def export_user_servers(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """导出用户的所有服务器配置"""
        async for db in get_async_session():
            return await mcp_server.export_user_configs(db, user_id=user_id)
            break
    
    async def get_user_servers_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取用户服务器统计信息"""
        async for db in get_async_session():
            db_stats = await mcp_server.get_user_servers_count(db, user_id=user_id)
            
            # 添加运行时状态统计
            if self.is_enabled():
                status = self.get_status()
                db_stats.update({
                    "connected": status.get("connected_count", 0),
                    "runtime_servers": status.get("server_count", 0)
                })
            else:
                db_stats.update({
                    "connected": 0,
                    "runtime_servers": 0
                })
            
            return db_stats
            break
    
    # 系统级方法（保持向后兼容）
    async def _load_system_default_servers(self) -> None:
        """加载系统默认服务器配置（从环境变量）"""
        try:
            if not settings.MCP_SERVERS:
                logger.info("没有找到系统默认MCP服务器配置")
                return
            
            logger.info(f"加载了 {len(settings.MCP_SERVERS)} 个系统默认MCP服务器配置")
            
        except Exception as e:
            logger.error(f"加载系统默认MCP服务器配置失败: {e}")
    
    # 工具调用相关方法（保持不变）
    async def list_tools(self, server_name: Optional[str] = None, force_refresh: bool = False) -> Union[List[Tool], Dict[str, List[Tool]]]:
        """列出可用工具"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        if server_name:
            # 获取指定服务器的工具
            client = self.session_manager.get_client(server_name)
            if not client:
                raise MCPError(f"服务器不存在: {server_name}")
            return await client.list_tools(force_refresh)
        else:
            # 获取所有服务器的工具
            return await self.session_manager.list_all_tools(force_refresh)
    
    async def list_resources(self, server_name: Optional[str] = None, force_refresh: bool = False) -> Union[List[Resource], Dict[str, List[Resource]]]:
        """列出可用资源"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        if server_name:
            # 获取指定服务器的资源
            client = self.session_manager.get_client(server_name)
            if not client:
                raise MCPError(f"服务器不存在: {server_name}")
            return await client.list_resources(force_refresh)
        else:
            # 获取所有服务器的资源
            return await self.session_manager.list_all_resources(force_refresh)
    
    async def list_prompts(self, server_name: Optional[str] = None, force_refresh: bool = False) -> Union[List[Prompt], Dict[str, List[Prompt]]]:
        """列出可用提示"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        if server_name:
            # 获取指定服务器的提示
            client = self.session_manager.get_client(server_name)
            if not client:
                raise MCPError(f"服务器不存在: {server_name}")
            return await client.list_prompts(force_refresh)
        else:
            # 获取所有服务器的提示
            return await self.session_manager.list_all_prompts(force_refresh)
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        """调用指定服务器的工具"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        return await self.session_manager.call_tool(server_name, tool_name, arguments or {})
    
    async def call_tool_auto(self, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        """自动选择服务器调用工具"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        # 查找工具所在的服务器
        result = await self.session_manager.find_tool(tool_name)
        if not result:
            raise MCPError(f"未找到工具: {tool_name}")
        
        server_name, tool = result
        return await self.session_manager.call_tool(server_name, tool_name, arguments or {})
    
    async def read_resource(self, server_name: str, uri: str) -> ResourceContent:
        """读取指定服务器的资源"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        return await self.session_manager.read_resource(server_name, uri)
    
    async def read_resource_auto(self, uri: str) -> ResourceContent:
        """自动选择服务器读取资源"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        # 查找资源所在的服务器
        result = await self.session_manager.find_resource(uri)
        if not result:
            raise MCPError(f"未找到资源: {uri}")
        
        server_name, resource = result
        return await self.session_manager.read_resource(server_name, uri)
    
    async def get_prompt(self, server_name: str, prompt_name: str, arguments: Dict[str, Any] = None) -> PromptResult:
        """获取指定服务器的提示"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        return await self.session_manager.get_prompt(server_name, prompt_name, arguments or {})
    
    async def get_prompt_auto(self, prompt_name: str, arguments: Dict[str, Any] = None) -> PromptResult:
        """自动选择服务器获取提示"""
        if not self.is_enabled():
            raise MCPError("MCP服务未启用")
        
        # 查找提示所在的服务器
        result = await self.session_manager.find_prompt(prompt_name)
        if not result:
            raise MCPError(f"未找到提示: {prompt_name}")
        
        server_name, prompt = result
        return await self.session_manager.get_prompt(server_name, prompt_name, arguments or {})
    
    # 聊天集成方法（保持不变）
    async def get_available_tools_for_chat(self) -> List[Dict[str, Any]]:
        """获取可用于聊天的工具列表 - 返回原生MCP格式"""
        if not self.is_enabled():
            return []
        
        try:
            tools = await self.list_tools()
            
            # 如果返回的是字典（按服务器分组），需要展平
            if isinstance(tools, dict):
                all_tools = []
                for server_name, server_tools in tools.items():
                    for tool in server_tools:
                        # 返回标准OpenAI MCP格式
                        tool_info = {
                            "type": "mcp",
                            "mcp": {
                                "server": server_name,
                                "tool": {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema.__dict__
                                }
                            }
                        }
                        all_tools.append(tool_info)
                return all_tools
            else:
                # 如果是列表，直接转换
                return [
                    {
                        "type": "mcp",
                        "mcp": {
                            "server": "unknown",
                            "tool": {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema.__dict__
                            }
                        }
                    }
                    for tool in tools
                ]
                
        except Exception as e:
            logger.error(f"获取可用工具失败: {e}")
            return []
    
    async def execute_mcp_tool_for_chat(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """为聊天执行MCP工具调用"""
        if not self.is_enabled():
            return {
                "success": False,
                "error": "MCP服务未启用",
                "result": None
            }
        
        try:
            # 尝试自动调用工具
            result = await self.call_tool_auto(tool_name, arguments)
            
            return {
                "success": True,
                "error": None,
                "result": {
                    "content": result.content,
                    "isError": result.isError
                }
            }
            
        except Exception as e:
            logger.error(f"执行MCP工具调用失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = self.get_status()
        
        if not status["enabled"]:
            return {
                "healthy": False,
                "message": "MCP服务未启用",
                "details": status
            }
        
        connected_ratio = status["connected_count"] / max(status["server_count"], 1)
        
        return {
            "healthy": connected_ratio > 0.5,  # 至少一半的服务器连接正常
            "message": f"已连接 {status['connected_count']}/{status['server_count']} 个服务器",
            "details": status
        }

    async def ensure_user_servers_loaded(self, user_id: int) -> None:
        """确保用户的服务器已加载"""
        if not self.is_enabled():
            await self.initialize(user_id)
        else:
            await self.session_manager.load_user_servers_for_user(user_id)


# 全局MCP服务实例
mcp_service = MCPService() 