from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json

from backend.utils.logging import api_logger
from backend.services.openai_client import openai_client_service
from backend.services.chat_tool_handler import chat_tool_handler


class ChatToolProcessor:
    """聊天工具调用递归处理器"""
    
    @staticmethod
    async def process_tool_calls_recursively(
        content: str, 
        tool_calls: List[Dict[str, Any]], 
        messages: List[Dict[str, Any]], 
        agent, 
        use_model: str, 
        max_tokens: int, 
        temperature: float, 
        top_p: float, 
        tools: List[Dict[str, Any]], 
        has_tools: bool, 
        conversation_id: int,
        db: Optional[AsyncSession] = None,
        message_id: Optional[int] = None,
        max_iterations: int = 10  # 防止无限循环
    ) -> str:
        """
        递归处理工具调用，支持无限次调用
        """
        iteration = 0
        current_content = content
        current_tool_calls = tool_calls
        
        while current_tool_calls and iteration < max_iterations:
            iteration += 1
            api_logger.info(f"开始第 {iteration} 轮工具调用处理，共 {len(current_tool_calls)} 个工具调用")
            
            # 验证工具调用参数的完整性
            valid_tool_calls = []
            for tc in current_tool_calls:
                # 跳过None值（可能由索引填充产生）
                if tc is None:
                    continue
                    
                # 检查函数名是否有效
                if not tc['function']['name']:
                    api_logger.warning(f"工具调用 {tc['id']} 函数名为空，跳过")
                    continue
                
                # 检查参数是否有效
                if tc['function']['arguments'].strip():
                    try:
                        # 验证JSON格式
                        json.loads(tc['function']['arguments'])
                        valid_tool_calls.append(tc)
                        api_logger.info(f"工具调用 {tc['function']['name']} 参数完整: {tc['function']['arguments']}")
                    except json.JSONDecodeError as e:
                        api_logger.error(f"工具调用 {tc['function']['name']} 参数JSON格式错误: {tc['function']['arguments']}, 错误: {e}")
                else:
                    api_logger.warning(f"工具调用 {tc['function']['name']} 参数为空，跳过")
            
            if not valid_tool_calls:
                api_logger.warning("没有有效的工具调用，结束工具处理")
                break
            
            # 构造工具调用对象
            class ToolCall:
                def __init__(self, id, type, function):
                    self.id = id
                    self.type = type
                    self.function = function
            
            class Function:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = arguments
            
            tool_call_objects = []
            for tc in valid_tool_calls:
                func = Function(tc['function']['name'], tc['function']['arguments'])
                tool_call_obj = ToolCall(tc['id'], tc['type'], func)
                tool_call_objects.append(tool_call_obj)
            
            # 处理工具调用（不保存到数据库，因为上面已经保存过了）
            tool_results, tool_calls_data = await chat_tool_handler.handle_tool_calls(
                tool_call_objects, 
                agent, 
                None,  # 不传递数据库连接，避免重复保存
                conversation_id,
                message_id=None  # 不保存到数据库
            )
            
            # 将工具调用和结果添加到消息列表
            messages.append({
                "role": "assistant",
                "content": current_content,
                "tool_calls": [
                    {
                        "id": tc['id'],
                        "type": "function",
                        "function": {
                            "name": tc['function']['name'],
                            "arguments": tc['function']['arguments']
                        }
                    } for tc in valid_tool_calls
                ]
            })
            
            # 添加工具结果
            for tool_result in tool_results:
                messages.append(tool_result)
            
            api_logger.info(f"第 {iteration} 轮工具调用完成，调用下一次API")
            
            # 调用API获取下一次响应
            next_response = await openai_client_service.async_client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
                tools=tools if has_tools else None  # 确保每次调用都包含工具配置
            )
            
            # 提取响应
            assistant_message = next_response.choices[0].message
            current_content = assistant_message.content or ""
            
            # 检查是否有新的工具调用
            new_tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
            
            if new_tool_calls:
                api_logger.info(f"第 {iteration} 轮响应中检测到新的工具调用: {len(new_tool_calls)} 个")
                
                # 转换工具调用格式
                current_tool_calls = []
                for tc in new_tool_calls:
                    current_tool_calls.append({
                        'id': tc.id,
                        'type': tc.type,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments
                        }
                    })
            else:
                api_logger.info(f"第 {iteration} 轮响应中没有新的工具调用，结束处理")
                current_tool_calls = None
        
        if iteration >= max_iterations:
            api_logger.warning(f"工具调用达到最大迭代次数 {max_iterations}，强制结束")
        
        api_logger.info(f"工具调用处理完成，共进行了 {iteration} 轮，最终内容长度: {len(current_content)}")
        return current_content 
    
    @staticmethod
    async def process_tool_calls_recursively_stream(
        content: str, 
        tool_calls: List[Dict[str, Any]], 
        messages: List[Dict[str, Any]], 
        agent, 
        use_model: str, 
        max_tokens: int, 
        temperature: float, 
        top_p: float, 
        tools: List[Dict[str, Any]], 
        has_tools: bool, 
        conversation_id: int,
        db: Optional[AsyncSession] = None,
        message_id: Optional[int] = None,
        max_iterations: int = 10  # 防止无限循环
    ):
        """
        递归处理工具调用，支持无限次调用（流式版本）
        """
        iteration = 0
        current_content = content
        current_tool_calls = tool_calls
        
        # 进行递归处理
        while current_tool_calls and iteration < max_iterations:
            iteration += 1
            api_logger.info(f"开始第 {iteration} 轮工具调用处理，共 {len(current_tool_calls)} 个工具调用")
            
            # 验证工具调用参数的完整性
            valid_tool_calls = []
            for tc in current_tool_calls:
                # 跳过None值（可能由索引填充产生）
                if tc is None:
                    continue
                    
                # 检查函数名是否有效
                if not tc['function']['name']:
                    api_logger.warning(f"工具调用 {tc['id']} 函数名为空，跳过")
                    continue
                
                # 检查参数是否有效
                arguments_str = tc['function']['arguments'].strip()
                
                # 对于某些工具（如note_reader），空参数是合法的
                if arguments_str or tc['function']['name'] in ['note_reader']:
                    try:
                        # 验证JSON格式，空字符串默认为空对象
                        if not arguments_str:
                            arguments_str = '{}'
                            tc['function']['arguments'] = arguments_str
                        
                        json.loads(arguments_str)
                        valid_tool_calls.append(tc)
                        
                        if arguments_str == '{}':
                            api_logger.info(f"工具调用 {tc['function']['name']} 使用默认参数（空参数）")
                        else:
                            api_logger.info(f"工具调用 {tc['function']['name']} 参数完整: {arguments_str}")
                    except json.JSONDecodeError as e:
                        api_logger.error(f"工具调用 {tc['function']['name']} 参数JSON格式错误: {arguments_str}, 错误: {e}")
                else:
                    api_logger.warning(f"工具调用 {tc['function']['name']} 参数为空，跳过")
            
            if not valid_tool_calls:
                api_logger.warning("没有有效的工具调用，结束工具处理")
                break
            
            # 构造工具调用对象
            class ToolCall:
                def __init__(self, id, type, function):
                    self.id = id
                    self.type = type
                    self.function = function
            
            class Function:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = arguments
            
            # 处理当前的工具调用
            tool_results = []
            for tc in valid_tool_calls:
                # 构造工具调用对象
                func = Function(tc['function']['name'], tc['function']['arguments'])
                tool_call_obj = ToolCall(tc['id'], tc['type'], func)
                
                # 发送工具调用执行状态
                tool_status = {
                    "type": "tool_call_executing",
                    "tool_call_id": tool_call_obj.id,
                    "tool_name": tool_call_obj.function.name,
                    "status": "executing"
                }
                yield ("", conversation_id, tool_status)
                
                # 执行单个工具调用（传递message_id关联到特定消息）
                single_result, single_tool_data = await chat_tool_handler.handle_tool_calls(
                    [tool_call_obj], 
                    agent, 
                    db,  # 传递数据库连接，保存工具调用记录
                    conversation_id,
                    message_id=message_id  # 关联到特定消息
                )
                
                # 收集工具结果
                tool_results.extend(single_result)
                
                # 发送工具调用完成状态，包含结果内容
                tool_result_content = single_result[0]["content"] if single_result else ""
                tool_status = {
                    "type": "tool_call_completed",
                    "tool_call_id": tool_call_obj.id,
                    "tool_name": tool_call_obj.function.name,
                    "status": "completed",
                    "result": tool_result_content
                }
                yield ("", conversation_id, tool_status)
            
            # 将工具调用和结果添加到消息列表
            messages.append({
                "role": "assistant",
                "content": current_content,
                "tool_calls": [
                    {
                        "id": tc['id'],
                        "type": "function",
                        "function": {
                            "name": tc['function']['name'],
                            "arguments": tc['function']['arguments']
                        }
                    } for tc in valid_tool_calls
                ]
            })
            
            # 添加工具结果
            for tool_result in tool_results:
                messages.append(tool_result)
            
            api_logger.info(f"第 {iteration} 轮工具调用完成，调用下一次流式API")
            
            # 调用API获取下一次响应（流式）
            next_response = await openai_client_service.async_client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
                tools=tools if has_tools else None  # 确保每次调用都包含工具配置
            )
            
            # 处理流式响应
            next_collected_content = ""
            next_collected_tool_calls = []
            next_chunk_count = 0
            
            async for chunk in next_response:
                next_chunk_count += 1
                api_logger.debug(f"第 {iteration} 轮流式响应块 #{next_chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
                
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    
                    # 检查是否有工具调用
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        api_logger.debug(f"第 {iteration} 轮流式响应中检测到工具调用: {len(delta.tool_calls)} 个")
                        
                        # 收集工具调用信息
                        for tool_call in delta.tool_calls:
                            # 获取工具调用的索引（如果有）
                            tool_index = getattr(tool_call, 'index', None)
                            
                            # 查找是否已存在相同索引的工具调用
                            existing_call = None
                            if tool_index is not None:
                                # 使用索引查找
                                if tool_index < len(next_collected_tool_calls):
                                    existing_call = next_collected_tool_calls[tool_index]
                            else:
                                # 使用ID查找
                                for existing in next_collected_tool_calls:
                                    if existing and existing.get('id') == tool_call.id:
                                        existing_call = existing
                                        break
                            
                            if existing_call:
                                # 更新现有的工具调用
                                if tool_call.function and tool_call.function.arguments:
                                    existing_call['function']['arguments'] += tool_call.function.arguments
                                    api_logger.debug(f"第 {iteration} 轮累积工具调用参数: {existing_call['id']}, 当前参数: {existing_call['function']['arguments']}")
                                    
                                # 更新函数名（如果提供）
                                if tool_call.function and tool_call.function.name:
                                    existing_call['function']['name'] = tool_call.function.name
                                    
                                # 更新ID（如果提供）
                                if tool_call.id:
                                    existing_call['id'] = tool_call.id
                            else:
                                # 添加新的工具调用
                                new_call = {
                                    'id': tool_call.id if tool_call.id else f"call_iter_{iteration}_{len(next_collected_tool_calls)}",
                                    'type': tool_call.type if tool_call.type else 'function',
                                    'function': {
                                        'name': tool_call.function.name if tool_call.function and tool_call.function.name else '',
                                        'arguments': tool_call.function.arguments if tool_call.function and tool_call.function.arguments else ''
                                    }
                                }
                                
                                # 如果有索引，确保列表足够大
                                if tool_index is not None:
                                    while len(next_collected_tool_calls) <= tool_index:
                                        next_collected_tool_calls.append(None)
                                    next_collected_tool_calls[tool_index] = new_call
                                else:
                                    next_collected_tool_calls.append(new_call)
                                
                                api_logger.debug(f"第 {iteration} 轮新增工具调用: {new_call['id']}, 名称: {new_call['function']['name']}, 初始参数: {new_call['function']['arguments']}")
                                
                                # 发送工具调用开始的状态信息
                                tool_status = {
                                    "type": "tool_call_start",
                                    "tool_call_id": new_call['id'],
                                    "tool_name": new_call['function']['name'],
                                    "status": "preparing"
                                }
                                yield ("", conversation_id, tool_status)
                    
                    content_chunk = delta.content or ""
                    next_collected_content += content_chunk
                    
                    if content_chunk:
                        yield content_chunk
            
            # 更新当前内容和工具调用
            current_content = next_collected_content
            
            # 检查是否有新的工具调用需要处理
            if next_collected_tool_calls:
                # 过滤掉None值
                current_tool_calls = [tc for tc in next_collected_tool_calls if tc is not None]
                api_logger.info(f"第 {iteration} 轮响应中检测到 {len(current_tool_calls)} 个新的工具调用")
            else:
                api_logger.info(f"第 {iteration} 轮响应中没有新的工具调用，结束处理")
                current_tool_calls = None
        
        if iteration >= max_iterations:
            api_logger.warning(f"工具调用达到最大迭代次数 {max_iterations}，强制结束")
        
        api_logger.info(f"流式工具调用处理完成，共进行了 {iteration} 轮，最终内容长度: {len(current_content)}")
        
        # 发送工具处理完成状态
        if iteration > 0:
            tool_status = {
                "type": "tools_completed",
                "status": "completed"
            }
            yield ("", conversation_id, tool_status)


# 创建全局工具处理器实例
chat_tool_processor = ChatToolProcessor() 