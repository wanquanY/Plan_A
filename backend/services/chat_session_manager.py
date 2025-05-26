from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.utils.logging import api_logger
from backend.crud.chat import get_chat, get_chat_messages, update_chat_title
from backend.services.memory import memory_service
from backend.services.title_generator import generate_title_with_ai


class ChatSessionManager:
    """聊天会话管理器"""
    
    @staticmethod
    async def auto_generate_title_if_needed(db: AsyncSession, conversation_id: int, user_content: str):
        """
        如果需要，自动生成会话标题
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            user_content: 用户消息内容
        """
        try:
            # 获取当前会话信息
            current_chat = await get_chat(db, conversation_id)
            if current_chat and current_chat.title == "新对话":
                # 获取会话的消息数量，判断是否是第一次对话
                messages_count = await get_chat_messages(db, conversation_id)
                # 只要是新会话（标题为"新对话"）且有用户消息，就生成标题
                user_messages = [msg for msg in messages_count if msg.role == "user"]
                if len(user_messages) == 1:  # 只有一条用户消息，说明是第一次对话
                    api_logger.info(f"检测到第一次对话，开始自动生成标题，会话ID: {conversation_id}")
                    
                    # 使用用户的第一条消息生成标题
                    generated_title = await generate_title_with_ai(conversation_id, user_content)
                    
                    # 更新会话标题
                    await update_chat_title(db, conversation_id, generated_title)
                    api_logger.info(f"自动生成标题成功: {generated_title}, 会话ID: {conversation_id}")
        except Exception as title_error:
            api_logger.error(f"自动生成标题失败: {str(title_error)}")
            # 标题生成失败不影响主要功能，继续执行
    
    @staticmethod
    async def clear_memory(conversation_id: int):
        """
        清空指定会话的记忆
        """
        memory_service.clear_memory(conversation_id)
        api_logger.info(f"已清空会话 {conversation_id} 的记忆")
    
    @staticmethod
    async def truncate_memory_after_message(conversation_id: int, message_index: int) -> bool:
        """
        截断指定消息后的所有记忆
        
        Args:
            conversation_id: 会话ID
            message_index: 消息索引，保留该索引及之前的消息，删除之后的消息
        
        Returns:
            bool: 是否截断成功
        """
        result = memory_service.truncate_memory_after_message(conversation_id, message_index)
        if result:
            api_logger.info(f"已截断会话 {conversation_id} 的记忆，保留到索引 {message_index}")
        else:
            api_logger.warning(f"截断会话 {conversation_id} 的记忆失败")
        return result
    
    @staticmethod
    async def replace_message_and_truncate(conversation_id: int, message_index: int, new_content: str, role: str = None) -> bool:
        """
        替换指定消息的内容，并截断该消息之后的所有记忆
        
        Args:
            conversation_id: 会话ID
            message_index: 消息索引
            new_content: 新的消息内容
            role: 消息角色，如果为None则保持原角色
        
        Returns:
            bool: 是否操作成功
        """
        result = memory_service.replace_message_and_truncate(conversation_id, message_index, new_content, role)
        if result:
            api_logger.info(f"已替换会话 {conversation_id} 的消息 {message_index} 并截断后续消息")
        else:
            api_logger.warning(f"替换会话 {conversation_id} 的消息失败")
        return result
    
    @staticmethod
    async def get_chat_history(
        db: AsyncSession, 
        conversation_id: int, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取指定会话的聊天历史记录
        """
        # 验证会话存在且属于当前用户
        chat = await get_chat(db, conversation_id)
        if not chat or chat.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在或无权访问"
            )
        
        # 获取聊天消息
        messages = await get_chat_messages(db, conversation_id)
        
        # 转换为前端需要的格式
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]


# 创建全局会话管理器实例
chat_session_manager = ChatSessionManager() 