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
        if not agent:
            return []
        
        # 修复：避免在异步上下文中访问SQLAlchemy关系属性
        tools_enabled = getattr(agent, 'tools_enabled', None)
        if not tools_enabled:
            return []
        
        # 使用工具管理器获取工具列表
        tools = tools_manager.get_agent_tools(tools_enabled)
        
        api_logger.info(f"为Agent AI助手 配置了 {len(tools)} 个内置工具")
        return tools
    
    @staticmethod
    async def get_agent_tools_async(agent, user_id: Optional[int] = None, db: Optional[AsyncSession] = None):
        """根据Agent的配置返回可用工具列表（包括内置工具和MCP工具）"""
        if not agent:
            return []
        
        # 修复：避免在异步上下文中访问SQLAlchemy关系属性
        tools_enabled = getattr(agent, 'tools_enabled', None)
        if not tools_enabled:
            return []
        
        try:
            # 如果没有提供数据库会话，创建一个新的
            if db is None:
                from backend.db.session import get_async_session
                async for db_session in get_async_session():
                    db = db_session
                    break
            
            # 使用Agent服务获取工具
            from backend.services.agent_service import agent_service
            # 修复：使用getattr安全获取public_id
            agent_public_id = getattr(agent, 'public_id', None)
            if not agent_public_id:
                api_logger.warning("Agent没有public_id，无法获取工具")
                return []
            
            tools = await agent_service.get_agent_tools_for_chat(db, agent_public_id, user_id)
            
            api_logger.info(f"为Agent {agent_public_id} 配置了 {len(tools)} 个工具（包括MCP工具）")
            return tools
            
        except Exception as e:
            api_logger.error(f"获取Agent工具失败: {e}")
            # 降级到内置工具
            tools = tools_manager.get_agent_tools(tools_enabled)
            api_logger.info(f"降级为Agent配置了 {len(tools)} 个内置工具")
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
        """处理工具调用请求并返回结果 - 支持转换后的MCP工具"""
        results = []
        tool_calls_data = []  # 用于兼容性，保留原有的返回格式
        
        # 获取工具配置，用于识别MCP工具
        tools_config = {}
        try:
            from backend.services.agent_service import agent_service
            tools = await agent_service.get_agent_tools_for_chat(db, agent.public_id, user_id) if agent else []
            for tool in tools:
                if tool.get("_mcp_metadata"):
                    # 这是转换后的MCP工具
                    function_name = tool.get("function", {}).get("name")
                    tools_config[function_name] = tool.get("_mcp_metadata")
        except Exception as e:
            api_logger.warning(f"获取工具配置失败: {e}")
        
        for tool_call in tool_calls:
            tool_call_id = tool_call.id
            
            # 检查是否是原生MCP工具调用（向后兼容）
            if hasattr(tool_call, 'mcp') and tool_call.mcp:
                # 原生MCP工具调用
                server_name = tool_call.mcp.get("server", "unknown")
                mcp_tool = tool_call.mcp.get("tool", {})
                function_name = mcp_tool.get("name")
                function_args = mcp_tool.get("arguments", {})
                
                api_logger.info(f"处理原生MCP工具调用: {function_name} (服务器: {server_name}), 参数: {function_args}")
                
                # 初始化工具调用数据
                tool_call_data = {
                    "id": tool_call_id,
                    "name": function_name,
                    "server": server_name,
                    "arguments": function_args,
                    "status": "preparing",
                    "result": None,
                    "error": None,
                    "started_at": datetime.now().isoformat(),
                    "type": "mcp"
                }
                tool_calls_data.append(tool_call_data)
                
                try:
                    # 更新状态为执行中
                    tool_call_data["status"] = "executing"
                    
                    # 通过MCP服务执行工具
                    from backend.services.mcp_service import mcp_service
                    
                    # 确保MCP服务已初始化，并加载用户特定的服务器
                    if not mcp_service.is_enabled():
                        await mcp_service.initialize(user_id=user_id)
                    else:
                        # 确保用户的MCP服务器已加载
                        if user_id:
                            await mcp_service.ensure_user_servers_loaded(user_id)
                    
                    # 为MCP工具添加session_id参数（如果工具支持的话）
                    mcp_arguments = function_args.copy() if isinstance(function_args, dict) else {}
                    if session_id:
                        mcp_arguments["session_id"] = session_id
                    
                    # 直接调用指定服务器的工具
                    mcp_result = await mcp_service.call_tool(
                        server_name=server_name,
                        tool_name=function_name,
                        arguments=mcp_arguments
                    )
                    
                    # 转换MCP结果格式
                    tool_result = {
                        "content": mcp_result.content,
                        "isError": mcp_result.isError,
                        "source": "mcp",
                        "server": server_name
                    }
                    
                    # 更新状态为完成
                    tool_call_data["status"] = "completed"
                    tool_call_data["result"] = tool_result
                    tool_call_data["completed_at"] = datetime.now().isoformat()
                    
                    api_logger.info(f"原生MCP工具 {function_name} 执行成功")
                    
                except Exception as e:
                    api_logger.error(f"原生MCP工具 {function_name} 执行失败: {str(e)}", exc_info=True)
                    
                    tool_result = {
                        "error": f"MCP工具执行失败: {str(e)}",
                        "source": "mcp",
                        "server": server_name
                    }
                    
                    # 更新状态为错误
                    tool_call_data["status"] = "error"
                    tool_call_data["error"] = str(e)
                    tool_call_data["completed_at"] = datetime.now().isoformat()
            
            else:
                # OpenAI function调用格式（包括转换后的MCP工具）
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # 检查是否是转换后的MCP工具
                mcp_metadata = tools_config.get(function_name)
                is_converted_mcp_tool = mcp_metadata is not None
                
                if is_converted_mcp_tool:
                    api_logger.info(f"处理转换后的MCP工具调用: {function_name} (服务器: {mcp_metadata.get('server')}), 参数: {function_args}")
                else:
                    api_logger.info(f"处理内置工具调用: {function_name}, 参数: {function_args}")
                
                # 初始化工具调用数据
                tool_call_data = {
                    "id": tool_call_id,
                    "name": function_name,
                    "arguments": function_args,
                    "status": "preparing",
                    "result": None,
                    "error": None,
                    "started_at": datetime.now().isoformat(),
                    "type": "mcp" if is_converted_mcp_tool else "function"
                }
                
                if is_converted_mcp_tool:
                    tool_call_data["server"] = mcp_metadata.get("server")
                
                tool_calls_data.append(tool_call_data)
                
                try:
                    # 更新状态为执行中
                    tool_call_data["status"] = "executing"
                    
                    if is_converted_mcp_tool:
                        # 处理转换后的MCP工具
                        from backend.services.mcp_service import mcp_service
                        
                        # 确保MCP服务已初始化
                        if not mcp_service.is_enabled():
                            await mcp_service.initialize(user_id=user_id)
                        else:
                            if user_id:
                                await mcp_service.ensure_user_servers_loaded(user_id)
                        
                        # 为MCP工具添加session_id参数
                        mcp_arguments = function_args.copy() if isinstance(function_args, dict) else {}
                        if session_id:
                            mcp_arguments["session_id"] = session_id
                        
                        # 调用MCP工具
                        server_name = mcp_metadata.get("server")
                        mcp_result = await mcp_service.call_tool(
                            server_name=server_name,
                            tool_name=function_name,
                            arguments=mcp_arguments
                        )
                        
                        # 转换MCP结果格式
                        tool_result = {
                            "content": mcp_result.content,
                            "isError": mcp_result.isError,
                            "source": "mcp",
                            "server": server_name
                        }
                        
                        api_logger.info(f"转换后的MCP工具 {function_name} 执行成功")
                        
                    else:
                        # 处理内置工具
                        api_logger.info(f"开始执行内置工具: {function_name}")
                        
                        # 使用工具管理器获取API密钥
                        api_key = None
                        if agent:
                            # 修复：避免在异步上下文中访问SQLAlchemy关系属性
                            tools_enabled = getattr(agent, 'tools_enabled', None)
                            if tools_enabled:
                                api_key = tools_manager.get_tool_api_key(function_name, tools_enabled)
                        
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
                        
                        elif function_name == "note_reader":
                            # 处理笔记阅读工具
                            api_logger.info(f"正在执行笔记阅读操作: {function_args}")
                            
                            # 会话ID通过配置传递给工具构造函数，而不是作为参数
                            session_public_id = None
                            if session_id:
                                # 将内部session_id转换为public_id
                                from backend.utils.id_converter import IDConverter
                                session_public_id = await IDConverter.get_chat_public_id(db, session_id) if isinstance(session_id, int) else session_id
                            
                            # 为每次工具调用创建新的数据库会话，避免会话状态污染
                            from backend.db.session import get_async_session
                            async for fresh_db_session in get_async_session():
                                try:
                                    tool_result = await tools_service.execute_tool_async(
                                        tool_name="note_reader",
                                        action="read_note",
                                        params=function_args,  # 只传递函数的原始参数
                                        config={
                                            "db_session": fresh_db_session,
                                            "session_id": session_public_id
                                        }
                                    )
                                    break  # 成功执行后退出循环
                                except Exception as e:
                                    api_logger.error(f"笔记阅读工具执行失败: {e}")
                                    # 确保数据库会话被正确关闭
                                    try:
                                        await fresh_db_session.close()
                                    except:
                                        pass
                                    raise e
                                finally:
                                    # 确保数据库会话被正确关闭
                                    try:
                                        await fresh_db_session.close()
                                    except:
                                        pass
                        
                        elif function_name == "note_editor":
                            # 处理笔记编辑工具 - 为每次调用创建新的数据库会话
                            api_logger.info(f"正在执行笔记编辑操作: {function_args}")
                            
                            # 会话ID通过配置传递给工具构造函数，而不是作为参数
                            session_public_id = None
                            if session_id:
                                # 将内部session_id转换为public_id
                                from backend.utils.id_converter import IDConverter
                                session_public_id = await IDConverter.get_chat_public_id(db, session_id) if isinstance(session_id, int) else session_id
                            
                            # 为每次工具调用创建新的数据库会话，避免会话状态污染
                            from backend.db.session import get_async_session
                            async for fresh_db_session in get_async_session():
                                try:
                                    api_logger.info(f"笔记编辑工具准备完成，使用新的数据库会话，开始执行编辑操作...")
                                    tool_result = await tools_service.execute_tool_async(
                                        tool_name="note_editor",
                                        action="edit_note",
                                        params=function_args,  # 只传递函数的原始参数
                                        config={
                                            "db_session": fresh_db_session,
                                            "session_id": session_public_id
                                        }
                                    )
                                    api_logger.info(f"笔记编辑工具执行完成")
                                    break  # 成功执行后退出循环
                                except Exception as e:
                                    api_logger.error(f"笔记编辑工具执行失败: {e}")
                                    # 确保数据库会话被正确关闭
                                    try:
                                        await fresh_db_session.close()
                                    except:
                                        pass
                                    raise e
                                finally:
                                    # 确保数据库会话被正确关闭
                                    try:
                                        await fresh_db_session.close()
                                    except:
                                        pass
                        
                        elif function_name == "get_time":
                            # 处理时间工具
                            api_logger.info(f"正在执行时间查询操作: {function_args}")
                            tool_result = tools_service.execute_tool(
                                tool_name="get_time",
                                action="get_current_time",
                                params=function_args,
                                config=None  # 时间工具不需要特殊配置
                            )
                        
                        else:
                            # 未知工具
                            tool_result = {"error": f"未知工具: {function_name}"}
                    
                    # 更新状态为完成
                    tool_call_data["status"] = "completed"
                    tool_call_data["result"] = tool_result
                    tool_call_data["completed_at"] = datetime.now().isoformat()
                    
                except Exception as e:
                    api_logger.error(f"工具 {function_name} 执行失败: {str(e)}", exc_info=True)
                    
                    tool_result = {
                        "error": f"工具执行失败: {str(e)}",
                        "source": "mcp" if is_converted_mcp_tool else "builtin"
                    }
                    
                    # 更新状态为错误
                    tool_call_data["status"] = "error"
                    tool_call_data["error"] = str(e)
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
                    
                    # 获取工具名称和参数
                    tool_name = tool_call_data["name"]
                    tool_arguments = tool_call_data["arguments"]
                    
                    # 创建工具调用记录
                    await create_tool_call(
                        db=db,
                        user_id=user_id,
                        message_id=db_message_id,  # 使用数据库ID
                        session_id=db_session_id,  # 使用数据库ID
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        function_name=tool_name,
                        arguments=tool_arguments,
                        agent_id=agent_db_id,
                        status=tool_call_data["status"],
                        result=tool_result if tool_call_data["status"] == "completed" else None,
                        error_message=tool_call_data.get("error") if tool_call_data["status"] == "error" else None
                    )
                    api_logger.info(f"工具调用记录已保存到数据库: {tool_call_id}")
                except Exception as e:
                    api_logger.error(f"保存工具调用记录失败: {str(e)}", exc_info=True)
            else:
                api_logger.debug(f"跳过工具调用数据库记录（缺少必要参数）: db={bool(db)}, session_id={session_id}, message_id={message_id}")
            
            # 添加到结果列表
            results.append({
                "tool_call_id": tool_call_id,
                "role": "tool",
                "content": json.dumps(tool_result, ensure_ascii=False)
            })
            
            api_logger.info(f"工具 {tool_call_data['name']} 执行完成: {type(tool_result)}")
        
        api_logger.info(f"完成 {len(results)} 个工具调用")
        return results, tool_calls_data


# 创建全局工具处理器实例
chat_tool_handler = ChatToolHandler() 