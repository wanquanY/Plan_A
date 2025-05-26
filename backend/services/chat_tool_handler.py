from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime

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
        
        api_logger.info(f"为Agent {agent.name} 配置了 {len(tools)} 个工具")
        return tools
    
    @staticmethod
    async def handle_tool_calls(
        tool_calls, 
        agent, 
        db: Optional[AsyncSession] = None, 
        conversation_id: Optional[int] = None, 
        message_id: Optional[int] = None
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
                
                # 更新状态为完成
                tool_call_data["status"] = "completed"
                tool_call_data["result"] = tool_result
                tool_call_data["completed_at"] = datetime.now().isoformat()
                
                # 只在工具调用成功完成时保存到数据库
                if db and conversation_id and message_id:
                    try:
                        await create_tool_call(
                            db=db,
                            message_id=message_id,
                            conversation_id=conversation_id,
                            tool_call_id=tool_call_id,
                            tool_name=function_name,
                            function_name=function_name,
                            arguments=function_args,
                            agent_id=agent.id if agent else None,
                            status="completed",
                            result=tool_result
                        )
                        api_logger.debug(f"工具调用完成记录已保存: {tool_call_id}")
                    except Exception as e:
                        api_logger.error(f"保存工具调用记录失败: {str(e)}")
                
                results.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
                
            except Exception as e:
                api_logger.error(f"工具调用失败: {function_name}, 错误: {str(e)}")
                
                # 更新状态为错误
                tool_call_data["status"] = "error"
                tool_call_data["error"] = str(e)
                tool_call_data["completed_at"] = datetime.now().isoformat()
                
                # 只在工具调用失败时保存错误记录到数据库
                if db and conversation_id and message_id:
                    try:
                        await create_tool_call(
                            db=db,
                            message_id=message_id,
                            conversation_id=conversation_id,
                            tool_call_id=tool_call_id,
                            tool_name=function_name,
                            function_name=function_name,
                            arguments=function_args,
                            agent_id=agent.id if agent else None,
                            status="error",
                            error_message=str(e)
                        )
                        api_logger.debug(f"工具调用错误记录已保存: {tool_call_id}")
                    except Exception as db_e:
                        api_logger.error(f"保存工具调用错误记录失败: {str(db_e)}")
                
                # 返回错误结果
                results.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"error": str(e)}, ensure_ascii=False)
                })
        
        api_logger.info(f"完成 {len(results)} 个工具调用")
        return results, tool_calls_data


# 创建全局工具处理器实例
chat_tool_handler = ChatToolHandler() 