# 重构后的聊天服务 - 使用拆分的服务模块
# 保持向后兼容性，导入所有新服务的功能

from backend.services.openai_client import openai_client_service
from backend.services.chat_response_service import chat_response_service
from backend.services.chat_stream_service import chat_stream_service
from backend.services.chat_session_manager import chat_session_manager
from backend.services.chat_tool_handler import chat_tool_handler
from backend.services.chat_tool_processor import chat_tool_processor

# 导入CRUD函数以保持向后兼容性
from backend.crud.chat import get_chat_messages

# 为了保持向后兼容性，导出原有的函数名
generate_chat_response = chat_response_service.generate_chat_response
generate_chat_stream = chat_stream_service.generate_chat_stream

# 会话管理相关函数
auto_generate_title_if_needed = chat_session_manager.auto_generate_title_if_needed
clear_memory = chat_session_manager.clear_memory
truncate_memory_after_message = chat_session_manager.truncate_memory_after_message
replace_message_and_truncate = chat_session_manager.replace_message_and_truncate
get_chat_history = chat_session_manager.get_chat_history

# 工具相关函数
get_agent_tools = chat_tool_handler.get_agent_tools
handle_tool_calls = chat_tool_handler.handle_tool_calls
process_tool_calls_recursively = chat_tool_processor.process_tool_calls_recursively
process_tool_calls_recursively_stream = chat_tool_processor.process_tool_calls_recursively_stream

# 导出客户端实例（为了兼容性）
client = openai_client_service.client
async_client = openai_client_service.async_client
model = openai_client_service.model

# 导出CRUD函数（为了兼容性）
# get_chat_messages 已在上面导入，这里直接可用 