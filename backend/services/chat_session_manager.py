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
    async def auto_generate_title_if_needed(db: AsyncSession, session_id: int, user_content: str):
        """
        如果需要，自动为聊天会话生成标题
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            user_content: 用户消息内容
        """
        try:
            # 检查会话是否存在且标题为默认值
            chat = await get_chat(db, session_id)
            
            if not chat:
                api_logger.warning(f"会话不存在: session_id={session_id}")
                return
            
            # 如果标题是默认值或为空，且用户内容不为空，则生成标题
            if (not chat.title or chat.title in ["新对话", "新会话", ""]) and user_content.strip():
                try:
                    # 调用AI生成标题
                    new_title = await generate_title_with_ai(session_id, user_content)
                    
                    # 更新会话标题
                    await update_chat_title(db, session_id, new_title)
                    
                    api_logger.info(f"会话标题已自动生成: session_id={session_id}, title={new_title}")
                    
                except Exception as e:
                    api_logger.error(f"自动生成标题失败: session_id={session_id}, error={str(e)}")
                
        except Exception as e:
            api_logger.error(f"检查并生成标题时出错: {str(e)}")
    
    @staticmethod
    async def clear_memory(session_id: int):
        """
        清空指定会话的记忆
        
        Args:
            session_id: 会话ID
        """
        try:
            memory_service.clear_memory(session_id)
            api_logger.info(f"会话记忆已清空: session_id={session_id}")
        except Exception as e:
            api_logger.error(f"清空记忆失败: session_id={session_id}, error={str(e)}")
    
    @staticmethod
    async def truncate_memory_after_message(session_id: int, message_index: int) -> bool:
        """
        截断指定消息索引之后的记忆
        
        Args:
            session_id: 会话ID
            message_index: 消息索引
        
        Returns:
            bool: 是否截断成功
        """
        try:
            result = memory_service.truncate_memory_after_message(session_id, message_index)
            if result:
                    api_logger.info(f"会话记忆已截断: session_id={session_id}, message_index={message_index}")
            else:
                    api_logger.warning(f"会话记忆截断失败: session_id={session_id}, message_index={message_index}")
            return result
        except Exception as e:
            api_logger.error(f"截断记忆时出错: session_id={session_id}, message_index={message_index}, error={str(e)}")
            return False
    
    @staticmethod
    async def replace_message_and_truncate(session_id: int, message_index: int, new_content: str, role: str = None) -> bool:
        """
        替换指定索引的消息内容并截断后续消息
        
        Args:
            session_id: 会话ID
            message_index: 消息索引
            new_content: 新的消息内容
            role: 消息角色
        
        Returns:
            bool: 是否操作成功
        """
        try:
            result = memory_service.replace_message_and_truncate(session_id, message_index, new_content, role)
            if result:
                api_logger.info(f"会话消息已替换并截断: session_id={session_id}, message_index={message_index}")
            else:
                api_logger.warning(f"会话消息替换截断失败: session_id={session_id}, message_index={message_index}")
            return result
        except Exception as e:
            api_logger.error(f"替换消息并截断时出错: session_id={session_id}, message_index={message_index}, error={str(e)}")
            return False
    
    @staticmethod
    async def get_chat_history(
        db: AsyncSession, 
        session_id: int, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取指定会话的聊天历史记录
        """
        # 验证会话存在且属于当前用户
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在或无权访问"
            )
        
        # 获取聊天消息
        messages = await get_chat_messages(db, session_id)
        
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