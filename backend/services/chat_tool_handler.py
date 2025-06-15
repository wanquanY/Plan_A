from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
import asyncio

from backend.utils.logging import api_logger
from backend.services.tools import tools_service
from backend.config.tools_manager import tools_manager
from backend.crud.tool_call import create_tool_call


class ChatToolHandler:
    """聊天工具调用处理器"""
    
    @staticmethod
    def get_agent_tools(agent):
        """根据Agent的配置返回可用工具列表（仅内置工具，向后兼容）"""
        if not agent or not agent.tools_enabled:
            return []
        
        # 使用工具管理器获取工具列表
        tools = tools_manager.get_agent_tools(agent.tools_enabled)
        
        api_logger.info(f"为Agent AI助手 配置了 {len(tools)} 个内置工具")
        return tools
    
    @staticmethod
    async def get_agent_tools_async(agent, user_id: Optional[int] = None, db: Optional[AsyncSession] = None):
        """根据Agent的配置返回可用工具列表（包括内置工具和MCP工具）"""
        if not agent or not agent.tools_enabled:
            return []
        
        try:
            # 如果没有提供数据库会话，创建一个新的
            if db is None:
                from backend.core.database import get_db
                async for db_session in get_db():
                    db = db_session
                    break
            
            # 使用Agent服务获取工具
            from backend.services.agent_service import agent_service
            tools = await agent_service.get_agent_tools_for_chat(db, agent.public_id, user_id)
            
            api_logger.info(f"为Agent {agent.public_id} 配置了 {len(tools)} 个工具（包括MCP工具）")
            return tools
            
        except Exception as e:
            api_logger.error(f"获取Agent工具失败: {e}")
            # 降级到内置工具
            tools = tools_manager.get_agent_tools(agent.tools_enabled)
            api_logger.info(f"降级为Agent {agent.public_id} 配置了 {len(tools)} 个内置工具")
            return tools
    
    @staticmethod
    async def handle_tool_calls(
        tool_calls, 
        agent, 
        db: Optional[AsyncSession] = None, 
        session_id: Optional[int] = None, 
        message_id: Optional[int] = None,
        user_id: Optional[int] = None,
        agent_id: Optional[int] = None
    ):
        """处理工具调用请求并返回结果"""
        results = []
        tool_calls_data = []  # 用于兼容性，保留原有的返回格式
        
        for tool_call in tool_calls:
            tool_call_id = tool_call.id
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            api_logger.info(f"处理工具调用: {function_name}, 参数: {function_args}")
            
            # 初始化工具调用数据（用于兼容性）
            tool_call_data = {
                "id": tool_call_id,
                "name": function_name,
                "arguments": function_args,
                "status": "preparing",
                "result": None,
                "error": None,
                "started_at": datetime.now().isoformat()
            }
            tool_calls_data.append(tool_call_data)
            
            # 使用工具管理器获取API密钥
            api_key = None
            if agent and agent.tools_enabled:
                api_key = tools_manager.get_tool_api_key(function_name, agent.tools_enabled)
            
            try:
                # 更新状态为执行中
                tool_call_data["status"] = "executing"
                
                # 根据函数名执行相应的工具
                tool_result = None
                if function_name == "tavily_search":
                    tool_result = tools_service.execute_tool(
                        tool_name="tavily",
                        action="search",
                        params={
                            "query": function_args.get("query"),
                            "max_results": function_args.get("max_results", 10)
                        },
                        config={"api_key": api_key} if api_key else None
                    )
                    
                elif function_name == "tavily_extract":
                    tool_result = tools_service.execute_tool(
                        tool_name="tavily",
                        action="extract",
                        params={
                            "urls": function_args.get("urls"),
                            "include_images": function_args.get("include_images", False)
                        },
                        config={"api_key": api_key} if api_key else None
                    )
                
                elif function_name == "serper_search":
                    tool_result = tools_service.execute_tool(
                        tool_name="serper",
                        action="search",
                        params={
                            "query": function_args.get("query"),
                            "max_results": function_args.get("max_results", 10),
                            "gl": function_args.get("gl", "cn"),
                            "hl": function_args.get("hl", "zh-cn")
                        },
                        config={"api_key": api_key} if api_key else None
                    )
                
                elif function_name == "serper_news":
                    tool_result = tools_service.execute_tool(
                        tool_name="serper",
                        action="news_search",
                        params={
                            "query": function_args.get("query"),
                            "max_results": function_args.get("max_results", 10),
                            "gl": function_args.get("gl", "cn"),
                            "hl": function_args.get("hl", "zh-cn")
                        },
                        config={"api_key": api_key} if api_key else None
                    )
                
                elif function_name == "serper_scrape":
                    tool_result = tools_service.execute_tool(
                        tool_name="serper",
                        action="scrape_url",
                        params={
                            "url": function_args.get("url"),
                            "include_markdown": function_args.get("include_markdown", True)
                        },
                        config={"api_key": api_key} if api_key else None
                    )
                
                else:
                    # 尝试通过MCP服务执行工具
                    try:
                        from backend.services.mcp_service import MCPService
                        mcp_service = MCPService()
                        
                        # 确保MCP服务已初始化，并加载用户特定的服务器
                        if not mcp_service.is_enabled():
                            await mcp_service.initialize(user_id=user_id)
                        else:
                            # 确保用户的MCP服务器已加载
                            if user_id:
                                await mcp_service.ensure_user_servers_loaded(user_id)
                        
                        # 为MCP工具添加session_id参数（如果工具支持的话）
                        mcp_arguments = function_args.copy()
                        if session_id:
                            mcp_arguments["session_id"] = session_id
                        
                        # 尝试通过MCP执行工具
                        mcp_result = await mcp_service.execute_mcp_tool_for_chat(
                            tool_name=function_name,
                            arguments=mcp_arguments
                        )
                        
                        if mcp_result["success"]:
                            tool_result = mcp_result["result"]
                            api_logger.info(f"MCP工具 {function_name} 执行成功")
                        else:
                            tool_result = {"error": f"MCP工具执行失败: {mcp_result.get('error', '未知错误')}"}
                            api_logger.error(f"MCP工具 {function_name} 执行失败: {mcp_result.get('error')}")
                    
                    except Exception as mcp_error:
                        api_logger.error(f"MCP工具 {function_name} 执行异常: {str(mcp_error)}", exc_info=True)
                        tool_result = {"error": f"工具不存在或MCP服务不可用: {str(mcp_error)}"}
                
                # 更新状态为完成
                tool_call_data["status"] = "completed"
                tool_call_data["result"] = tool_result
                tool_call_data["completed_at"] = datetime.now().isoformat()
                
                # 保存工具调用记录到数据库
                if db and session_id and message_id:
                    try:
                        # 将public_id转换为数据库内部ID
                        from backend.utils.id_converter import IDConverter
                        
                        # 转换message_id和session_id为数据库ID
                        db_message_id = await IDConverter.get_message_db_id(db, message_id) if isinstance(message_id, str) else message_id
                        db_session_id = await IDConverter.get_chat_db_id(db, session_id) if isinstance(session_id, str) else session_id
                        
                        if not db_message_id or not db_session_id:
                            api_logger.warning(f"无法转换ID: message_id={message_id} -> {db_message_id}, session_id={session_id} -> {db_session_id}")
                            raise ValueError("无法转换public_id为数据库ID")
                        
                        # 使用传入的agent_id，避免懒加载
                        agent_db_id = agent_id
                        
                        # 创建工具调用记录
                        await create_tool_call(
                            db=db,
                            user_id=user_id,
                            message_id=db_message_id,  # 使用数据库ID
                            session_id=db_session_id,  # 使用数据库ID
                            tool_call_id=tool_call_id,
                            tool_name=function_name,  # 使用function_name作为tool_name
                            function_name=function_name,
                            arguments=function_args,
                            agent_id=agent_db_id,
                            status="completed",
                            result=tool_result
                        )
                        api_logger.info(f"工具调用记录已保存到数据库: {tool_call_id}")
                    except Exception as e:
                        api_logger.error(f"保存工具调用记录失败: {str(e)}", exc_info=True)
                else:
                    api_logger.debug(f"跳过工具调用数据库记录（缺少必要参数）: db={bool(db)}, session_id={session_id}, message_id={message_id}")
                
                results.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
                
                api_logger.info(f"工具 {function_name} 执行完成: {type(tool_result)}")
            
            except Exception as e:
                api_logger.error(f"工具 {function_name} 执行失败: {str(e)}", exc_info=True)
                
                # 保存工具调用错误记录到数据库
                if db and session_id and message_id:
                    try:
                        # 将public_id转换为数据库内部ID
                        from backend.utils.id_converter import IDConverter
                        
                        # 转换message_id和session_id为数据库ID
                        db_message_id = await IDConverter.get_message_db_id(db, message_id) if isinstance(message_id, str) else message_id
                        db_session_id = await IDConverter.get_chat_db_id(db, session_id) if isinstance(session_id, str) else session_id
                        
                        if not db_message_id or not db_session_id:
                            api_logger.warning(f"无法转换ID: message_id={message_id} -> {db_message_id}, session_id={session_id} -> {db_session_id}")
                            raise ValueError("无法转换public_id为数据库ID")
                        
                        # 使用传入的agent_id，避免懒加载
                        agent_db_id = agent_id
                        
                        # 创建工具调用错误记录
                        await create_tool_call(
                            db=db,
                            user_id=user_id,
                            message_id=db_message_id,  # 使用数据库ID
                            session_id=db_session_id,  # 使用数据库ID
                            tool_call_id=tool_call_id,
                            tool_name=function_name,  # 使用function_name作为tool_name
                            function_name=function_name,
                            arguments=function_args,
                            agent_id=agent_db_id,
                            status="error",
                            error_message=str(e)
                        )
                        api_logger.info(f"工具调用错误记录已保存到数据库: {tool_call_id}")
                    except Exception as db_error:
                        api_logger.error(f"保存工具调用错误记录失败: {str(db_error)}", exc_info=True)
                else:
                    api_logger.debug(f"跳过工具调用错误记录（缺少必要参数）: db={bool(db)}, session_id={session_id}, message_id={message_id}")
                
                results.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "content": json.dumps({
                        "error": f"工具执行失败: {str(e)}",
                        "tool_name": function_name
                    }, ensure_ascii=False)
                })
        
        api_logger.info(f"完成 {len(results)} 个工具调用")
        return results, tool_calls_data


# 创建全局工具处理器实例
chat_tool_handler = ChatToolHandler() 