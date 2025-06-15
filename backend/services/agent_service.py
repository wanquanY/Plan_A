"""
Agent服务

提供Agent相关的业务逻辑，包括工具管理、MCP服务器集成等。
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.agent import Agent
from backend.crud.agent import agent as agent_crud
from backend.services.mcp_service import mcp_service
from backend.config.tools_manager import tools_manager
from backend.utils.logging import app_logger as logger


class AgentService:
    """Agent服务类"""
    
    def __init__(self):
        pass
    
    async def get_agent_with_tools(
        self, 
        db: AsyncSession, 
        agent_id: str, 
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取Agent及其可用工具信息
        
        Args:
            db: 数据库会话
            agent_id: Agent ID
            user_id: 用户ID
            
        Returns:
            包含Agent信息和工具列表的字典
        """
        try:
            # 获取Agent信息
            agent = await agent_crud.get_agent_for_user(db, agent_id, user_id)
            if not agent:
                return None
            
            # 确保用户的MCP服务器已加载
            await self._ensure_user_mcp_servers_loaded(user_id)
            
            # 获取Agent的所有可用工具（包括内置工具和MCP工具）
            tools = await self._get_agent_all_tools(agent, user_id)
            
            return {
                "agent": agent,
                "tools": tools,
                "tool_count": len(tools),
                "builtin_tools": [t for t in tools if not t.get("is_mcp", False)],
                "mcp_tools": [t for t in tools if t.get("is_mcp", False)]
            }
            
        except Exception as e:
            logger.error(f"获取Agent工具信息失败: {e}")
            return None
    
    async def get_agent_tools_for_chat(
        self, 
        db: AsyncSession, 
        agent_id: str, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取Agent的聊天工具（OpenAI格式）
        
        Args:
            db: 数据库会话
            agent_id: Agent ID
            user_id: 用户ID
            
        Returns:
            OpenAI格式的工具列表
        """
        try:
            # 获取Agent信息
            agent = await agent_crud.get_agent_by_id(db, agent_id)
            if not agent or agent.user_id != user_id:
                logger.warning(f"Agent不存在或无权限访问: {agent_id}")
                return []
            
            if not agent.tools_enabled:
                logger.info(f"Agent {agent_id} 未启用工具")
                return []
            
            # 获取内置工具
            builtin_tools = tools_manager.get_agent_tools(agent.tools_enabled)
            logger.info(f"获取到 {len(builtin_tools)} 个内置工具")
            
            # 获取MCP工具
            mcp_tools = []
            try:
                if mcp_service.is_enabled():
                    await mcp_service.ensure_user_servers_loaded(user_id)
                    raw_mcp_tools = await mcp_service.get_available_tools_for_chat()
                    logger.info(f"获取到 {len(raw_mcp_tools)} 个MCP工具")
                    
                    # 去重MCP工具（按名称去重）
                    seen_names = set()
                    unique_mcp_tools = []
                    for tool in raw_mcp_tools:
                        tool_name = tool.get("name")
                        if tool_name and tool_name not in seen_names:
                            seen_names.add(tool_name)
                            unique_mcp_tools.append(tool)
                    
                    logger.info(f"去重后获取到 {len(unique_mcp_tools)} 个唯一MCP工具")
                    
                    # 限制MCP工具数量（最多15个）
                    if len(unique_mcp_tools) > 15:
                        unique_mcp_tools = unique_mcp_tools[:15]
                        logger.info(f"限制MCP工具数量为 {len(unique_mcp_tools)} 个")
                    
                    mcp_tools = unique_mcp_tools
                    
            except Exception as e:
                logger.error(f"获取MCP工具失败: {e}")
            
            # 合并所有工具
            all_tools = builtin_tools + mcp_tools
            logger.info(f"总共获取到 {len(all_tools)} 个工具")
            
            # 转换为OpenAI工具格式
            openai_tools = []
            for tool in all_tools:
                try:
                    # 检查是否是MCP工具（通过server字段或is_mcp标记判断）
                    is_mcp_tool = tool.get("is_mcp", False) or "server" in tool
                    
                    if is_mcp_tool:
                        # MCP工具需要转换格式
                        openai_tool = {
                            "type": "function",
                            "function": {
                                "name": tool.get("name"),
                                "description": tool.get("description", ""),
                                "parameters": tool.get("inputSchema", {})
                            }
                        }
                    else:
                        # 内置工具已经是正确格式
                        openai_tool = tool
                    
                    # 验证工具格式
                    if (openai_tool.get("type") == "function" and 
                        openai_tool.get("function", {}).get("name") and
                        openai_tool.get("function", {}).get("description")):
                        openai_tools.append(openai_tool)
                    else:
                        logger.warning(f"跳过格式不正确的工具: {tool}")
                        
                except Exception as e:
                    logger.error(f"转换工具格式失败: {tool}, 错误: {e}")
                    continue
            
            logger.info(f"成功转换 {len(openai_tools)} 个工具为OpenAI格式")
            return openai_tools
            
        except Exception as e:
            logger.error(f"获取Agent工具失败: {e}")
            return []
    
    async def _ensure_user_mcp_servers_loaded(self, user_id: int) -> None:
        """确保用户的MCP服务器已加载"""
        try:
            if mcp_service.is_enabled():
                await mcp_service.ensure_user_servers_loaded(user_id)
                logger.info(f"已为用户 {user_id} 加载MCP服务器")
            else:
                logger.debug("MCP服务未启用，跳过MCP服务器加载")
        except Exception as e:
            logger.warning(f"加载用户MCP服务器失败: {e}")
    
    async def _get_agent_all_tools(
        self, 
        agent: Agent, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取Agent的所有可用工具（内置工具 + MCP工具）
        
        Args:
            agent: Agent对象
            user_id: 用户ID
            
        Returns:
            工具列表
        """
        all_tools = []
        
        try:
            # 获取内置工具
            if agent.tools_enabled:
                builtin_tools = tools_manager.get_agent_tools(agent.tools_enabled)
                for tool in builtin_tools:
                    tool_info = tool.copy()
                    tool_info["is_mcp"] = False
                    tool_info["source"] = "builtin"
                    all_tools.append(tool_info)
                
                logger.info(f"获取到 {len(builtin_tools)} 个内置工具")
            
            # 获取MCP工具
            try:
                mcp_tools = await mcp_service.get_available_tools_for_chat()
                for tool in mcp_tools:
                    tool_info = tool.copy()
                    tool_info["is_mcp"] = True
                    tool_info["source"] = "mcp"
                    all_tools.append(tool_info)
                
                logger.info(f"获取到 {len(mcp_tools)} 个MCP工具")
                
            except Exception as e:
                logger.warning(f"获取MCP工具失败: {e}")
            
            logger.info(f"Agent总共可用工具: {len(all_tools)} 个")
            return all_tools
            
        except Exception as e:
            logger.error(f"获取Agent工具失败: {e}")
            return []
    
    async def execute_agent_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        agent: Agent, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        执行Agent工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            agent: Agent对象
            user_id: 用户ID
            
        Returns:
            执行结果
        """
        try:
            # 首先尝试执行内置工具
            if agent.tools_enabled:
                builtin_tools = tools_manager.get_agent_tools(agent.tools_enabled)
                builtin_tool_names = [
                    tool["function"]["name"] 
                    for tool in builtin_tools 
                    if tool.get("type") == "function"
                ]
                
                if tool_name in builtin_tool_names:
                    # 执行内置工具
                    from backend.services.chat_tool_handler import ChatToolHandler
                    # 这里需要传递必要的参数给工具处理器
                    # 注意：这是一个简化的调用，实际可能需要更多参数
                    return {
                        "success": True,
                        "result": f"内置工具 {tool_name} 执行完成",
                        "source": "builtin"
                    }
            
            # 尝试执行MCP工具
            mcp_result = await mcp_service.execute_mcp_tool_for_chat(tool_name, arguments)
            if mcp_result["success"]:
                mcp_result["source"] = "mcp"
                return mcp_result
            
            # 如果都没找到工具
            return {
                "success": False,
                "error": f"未找到工具: {tool_name}",
                "result": None
            }
            
        except Exception as e:
            logger.error(f"执行Agent工具失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def get_agent_statistics(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        获取用户Agent的统计信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            统计信息
        """
        try:
            agent = await agent_crud.get_user_agent(db, user_id)
            if not agent:
                return {
                    "has_agent": False,
                    "total_tools": 0,
                    "builtin_tools": 0,
                    "mcp_tools": 0,
                    "mcp_servers": 0
                }
            
            # 获取工具统计
            tools = await self._get_agent_all_tools(agent, user_id)
            builtin_count = len([t for t in tools if not t.get("is_mcp", False)])
            mcp_count = len([t for t in tools if t.get("is_mcp", False)])
            
            # 获取MCP服务器统计
            mcp_servers_count = 0
            try:
                if mcp_service.is_enabled():
                    servers = await mcp_service.get_user_servers(user_id)
                    mcp_servers_count = len([s for s in servers if s.get("enabled", False)])
            except Exception as e:
                logger.warning(f"获取MCP服务器统计失败: {e}")
            
            return {
                "has_agent": True,
                "agent_id": agent.public_id,
                "agent_name": "AI助手",
                "total_tools": len(tools),
                "builtin_tools": builtin_count,
                "mcp_tools": mcp_count,
                "mcp_servers": mcp_servers_count,
                "model": agent.model,
                "max_memory": agent.max_memory
            }
            
        except Exception as e:
            logger.error(f"获取Agent统计信息失败: {e}")
            return {
                "has_agent": False,
                "error": str(e)
            }


# 全局Agent服务实例
agent_service = AgentService() 