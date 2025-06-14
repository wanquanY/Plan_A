from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.utils.logging import api_logger
from backend.crud.chat import get_chat, get_chat_messages, update_chat_title
from backend.services.memory import memory_service
from backend.services.title_generator import generate_title_with_ai
from backend.utils.id_converter import IDConverter


class ChatSessionManager:
    """聊天会话管理器"""
    
    @staticmethod
    async def auto_generate_title_if_needed(db: AsyncSession, session_id: str, user_content: str):
        """
        如果会话标题为默认标题，自动生成新标题
        
        Args:
            db: 数据库会话
            session_id: 会话public_id
            user_content: 用户消息内容
        """
        try:
            # 获取会话信息
            chat = await get_chat(db, session_id)
            if not chat:
                api_logger.warning(f"会话不存在: {session_id}")
                return
            
            # 如果标题是默认标题，则自动生成新标题
            if chat.title in ["新对话", "新会话", "新聊天", None, ""]:
                api_logger.info(f"检测到默认标题，开始生成新标题: session_id={session_id}")
                
                try:
                    # 使用AI生成标题
                    new_title = await generate_title_with_ai(session_id, user_content, db)
                    
                    # 更新会话标题
                    updated_chat = await update_chat_title(db, session_id, new_title)
                    if updated_chat:
                        api_logger.info(f"自动生成标题成功: session_id={session_id}, new_title={new_title}")
                    else:
                        api_logger.warning(f"更新标题失败: session_id={session_id}")
                        
                except Exception as e:
                    api_logger.error(f"自动生成标题失败: session_id={session_id}, error={str(e)}")
            else:
                api_logger.debug(f"会话已有自定义标题，跳过自动生成: session_id={session_id}, title={chat.title}")
                
        except Exception as e:
            api_logger.error(f"自动生成标题过程失败: session_id={session_id}, error={str(e)}")
    
    @staticmethod
    async def clear_memory(session_id: str):
        """
        清空会话记忆
        
        Args:
            session_id: 会话public_id
        """
        try:
            memory_service.clear_memory(session_id)
            api_logger.info(f"清空会话记忆成功: session_id={session_id}")
        except Exception as e:
            api_logger.error(f"清空会话记忆失败: session_id={session_id}, error={str(e)}")
    
    @staticmethod
    async def truncate_memory_after_message(session_id: str, message_index: int) -> bool:
        """
        截断指定消息之后的记忆
        
        Args:
            session_id: 会话public_id
            message_index: 消息索引
        
        Returns:
            是否成功
        """
        try:
            result = memory_service.truncate_memory_after_message(session_id, message_index)
            if result:
                api_logger.info(f"截断会话记忆成功: session_id={session_id}, message_index={message_index}")
            else:
                api_logger.warning(f"截断会话记忆失败: session_id={session_id}, message_index={message_index}")
            return result
        except Exception as e:
            api_logger.error(f"截断会话记忆异常: session_id={session_id}, message_index={message_index}, error={str(e)}")
            return False
    
    @staticmethod
    async def replace_message_and_truncate(session_id: str, message_index: int, new_content: str, role: str = None) -> bool:
        """
        替换指定消息并截断后续消息
        
        Args:
            session_id: 会话public_id
            message_index: 消息索引
            new_content: 新内容
            role: 消息角色（可选）
        
        Returns:
            是否成功
        """
        try:
            result = memory_service.replace_message_and_truncate(session_id, message_index, new_content, role)
            if result:
                api_logger.info(f"替换消息并截断成功: session_id={session_id}, message_index={message_index}")
            else:
                api_logger.warning(f"替换消息并截断失败: session_id={session_id}, message_index={message_index}")
            return result
        except Exception as e:
            api_logger.error(f"替换消息并截断异常: session_id={session_id}, message_index={message_index}, error={str(e)}")
            return False
    
    @staticmethod
    async def get_chat_history(
        db: AsyncSession, 
        session_id: str, 
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
        result = []
        for msg in messages:
            # 转换消息ID为public_id
            msg_public_id = await IDConverter.get_message_public_id(db, msg.id)
            result.append({
                "id": msg_public_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        return result


# 创建全局会话管理器实例
chat_session_manager = ChatSessionManager() 