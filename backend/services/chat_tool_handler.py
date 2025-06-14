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
        """根据Agent的配置返回可用工具列表"""
        if not agent or not agent.tools_enabled:
            return []
        
        # 使用工具管理器获取工具列表
        tools = tools_manager.get_agent_tools(agent.tools_enabled)
        
        api_logger.info(f"为Agent AI助手 配置了 {len(tools)} 个工具")
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
                
                elif function_name == "note_reader":
                    # 笔记阅读工具需要特殊处理，因为需要数据库会话
                    if not db:
                        tool_result = {"error": "数据库连接不可用"}
                    else:
                        try:
                            # 创建笔记阅读工具实例
                            note_reader = tools_service.get_tool(
                                "note_reader", 
                                config={"db_session": db, "session_id": session_id}
                            )
                            
                            if note_reader:
                                api_logger.info("笔记阅读工具开始执行")
                                # 确保在正确的异步上下文中执行笔记读取
                                tool_result = await note_reader.read_note(
                                    note_id=function_args.get("note_id"),
                                    search_title=function_args.get("search_title"),
                                    start_line=function_args.get("start_line", 1),
                                    line_count=function_args.get("line_count", -1),
                                    include_metadata=function_args.get("include_metadata", True)
                                )
                                api_logger.info(f"笔记阅读工具执行完成，结果类型: {type(tool_result)}")
                            else:
                                tool_result = {"error": "无法创建笔记阅读工具实例"}
                        except Exception as e:
                            api_logger.error(f"笔记阅读工具执行异常: {str(e)}", exc_info=True)
                            tool_result = {"error": f"笔记阅读失败: {str(e)}"}
                
                elif function_name == "note_editor":
                    # 笔记编辑工具需要特殊处理，因为需要数据库会话
                    if not db:
                        tool_result = {"error": "数据库连接不可用"}
                    else:
                        try:
                            # 创建笔记编辑工具实例
                            note_editor = tools_service.get_tool(
                                "note_editor", 
                                config={"db_session": db, "session_id": session_id}
                            )
                            
                            if note_editor:
                                api_logger.info("笔记编辑工具开始执行")
                                # 确保在正确的异步上下文中执行笔记编辑
                                tool_result = await note_editor.edit_note(
                                    note_id=function_args.get("note_id"),
                                    search_title=function_args.get("search_title"),
                                    edit_type=function_args.get("edit_type", "replace"),
                                    content=function_args.get("content"),
                                    title=function_args.get("title"),
                                    start_line=function_args.get("start_line"),
                                    end_line=function_args.get("end_line"),
                                    insert_position=function_args.get("insert_position"),
                                    search_text=function_args.get("search_text"),
                                    replace_text=function_args.get("replace_text")
                                )
                                api_logger.info(f"笔记编辑工具执行完成，结果类型: {type(tool_result)}")
                            else:
                                tool_result = {"error": "无法创建笔记编辑工具实例"}
                        except Exception as e:
                            api_logger.error(f"笔记编辑工具执行异常: {str(e)}", exc_info=True)
                            tool_result = {"error": f"笔记编辑失败: {str(e)}"}
                
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