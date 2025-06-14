#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ID转换工具类
用于在数据库内部ID和对外暴露的public_id之间进行转换
"""

from typing import Optional, Union, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from backend.models.user import User
from backend.models.chat import Chat, ChatMessage
from backend.models.note import Note
from backend.models.agent import Agent
from backend.models.note_session import NoteSession
from backend.models.tool_call import ToolCallHistory
from backend.utils.logging import api_logger
import redis
import json
from backend.core.config import settings

# Redis客户端初始化
redis_client = redis.Redis.from_url(settings.REDIS_URL) if hasattr(settings, 'REDIS_URL') else None

class IDConverter:
    """ID转换器 - 支持Redis缓存优化"""
    
    # 缓存配置
    CACHE_TTL = 3600  # 1小时缓存
    CACHE_PREFIX = "id_conv:"
    
    @staticmethod
    def _get_cache_key(model_name: str, id_value: str, direction: str) -> str:
        """生成缓存键"""
        return f"{IDConverter.CACHE_PREFIX}{model_name}:{direction}:{id_value}"
    
    @staticmethod
    async def _get_from_cache(cache_key: str) -> Optional[str]:
        """从缓存获取值"""
        if not redis_client:
            return None
        try:
            cached_value = redis_client.get(cache_key)
            return cached_value.decode('utf-8') if cached_value else None
        except Exception:
            return None
    
    @staticmethod
    async def _set_cache(cache_key: str, value: str):
        """设置缓存值"""
        if not redis_client:
            return
        try:
            redis_client.setex(cache_key, IDConverter.CACHE_TTL, value)
        except Exception:
            pass
    
    @staticmethod
    async def _batch_set_cache(cache_pairs: Dict[str, str]):
        """批量设置缓存"""
        if not redis_client or not cache_pairs:
            return
        try:
            pipe = redis_client.pipeline()
            for cache_key, value in cache_pairs.items():
                pipe.setex(cache_key, IDConverter.CACHE_TTL, value)
            pipe.execute()
        except Exception:
            pass
    
    @staticmethod
    async def public_id_to_db_id(db: AsyncSession, public_id: str, model_class) -> Optional[int]:
        """将public_id转换为数据库ID - 带缓存优化"""
        if not public_id:
            return None
        
        model_name = model_class.__tablename__
        cache_key = IDConverter._get_cache_key(model_name, public_id, "pub_to_db")
        
        # 先查缓存
        cached_result = await IDConverter._get_from_cache(cache_key)
        if cached_result:
            return int(cached_result) if cached_result != "None" else None
        
        # 缓存未命中，查询数据库
        try:
            stmt = select(model_class.id).where(model_class.public_id == public_id)
            result = await db.execute(stmt)
            db_id = result.scalar_one_or_none()
            
            # 设置缓存
            cache_value = str(db_id) if db_id else "None"
            await IDConverter._set_cache(cache_key, cache_value)
            
            return db_id
        except Exception as e:
            api_logger.error(f"转换public_id到db_id失败: {public_id}, 错误: {str(e)}")
            return None
    
    @staticmethod
    async def db_id_to_public_id(db: AsyncSession, db_id: int, model_class) -> Optional[str]:
        """将数据库ID转换为public_id - 带缓存优化"""
        if not db_id:
            return None
        
        model_name = model_class.__tablename__
        cache_key = IDConverter._get_cache_key(model_name, str(db_id), "db_to_pub")
        
        # 先查缓存
        cached_result = await IDConverter._get_from_cache(cache_key)
        if cached_result:
            return cached_result if cached_result != "None" else None
        
        # 缓存未命中，查询数据库
        try:
            stmt = select(model_class.public_id).where(model_class.id == db_id)
            result = await db.execute(stmt)
            public_id = result.scalar_one_or_none()
            
            # 设置缓存
            cache_value = public_id if public_id else "None"
            await IDConverter._set_cache(cache_key, cache_value)
            
            return public_id
        except Exception as e:
            api_logger.error(f"转换db_id到public_id失败: {db_id}, 错误: {str(e)}")
            return None
    
    @staticmethod
    async def get_chat_db_id(db: AsyncSession, public_id: str) -> Optional[int]:
        """获取聊天会话的数据库ID"""
        return await IDConverter.public_id_to_db_id(db, public_id, Chat)
    
    @staticmethod
    async def get_chat_public_id(db: AsyncSession, db_id: int) -> Optional[str]:
        """获取聊天会话的public_id"""
        return await IDConverter.db_id_to_public_id(db, db_id, Chat)
    
    @staticmethod
    async def get_note_db_id(db: AsyncSession, public_id: str) -> Optional[int]:
        """获取笔记的数据库ID"""
        return await IDConverter.public_id_to_db_id(db, public_id, Note)
    
    @staticmethod
    async def get_note_public_id(db: AsyncSession, db_id: int) -> Optional[str]:
        """获取笔记的public_id"""
        return await IDConverter.db_id_to_public_id(db, db_id, Note)
    
    @staticmethod
    async def get_agent_db_id(db: AsyncSession, public_id: str) -> Optional[int]:
        """获取Agent的数据库ID"""
        return await IDConverter.public_id_to_db_id(db, public_id, Agent)
    
    @staticmethod
    async def get_agent_public_id(db: AsyncSession, db_id: int) -> Optional[str]:
        """获取Agent的public_id"""
        return await IDConverter.db_id_to_public_id(db, db_id, Agent)
    
    @staticmethod
    async def get_user_db_id(db: AsyncSession, public_id: str) -> Optional[int]:
        """获取用户的数据库ID"""
        return await IDConverter.public_id_to_db_id(db, public_id, User)
    
    @staticmethod
    async def get_user_public_id(db: AsyncSession, db_id: int) -> Optional[str]:
        """获取用户的public_id"""
        return await IDConverter.db_id_to_public_id(db, db_id, User)
    
    @staticmethod
    async def get_message_db_id(db: AsyncSession, public_id: str) -> Optional[int]:
        """获取消息的数据库ID"""
        return await IDConverter.public_id_to_db_id(db, public_id, ChatMessage)
    
    @staticmethod
    async def get_message_public_id(db: AsyncSession, db_id: int) -> Optional[str]:
        """获取消息的public_id"""
        return await IDConverter.db_id_to_public_id(db, db_id, ChatMessage)
    
    @staticmethod
    def convert_response_ids(data: Union[Dict, List], id_mappings: Dict[str, str]) -> Union[Dict, List]:
        """
        转换响应数据中的ID字段
        
        Args:
            data: 响应数据
            id_mappings: ID映射字典，格式为 {字段名: public_id}
            
        Returns:
            转换后的数据
        """
        if isinstance(data, dict):
            result = data.copy()
            for field, public_id in id_mappings.items():
                if field in result and public_id:
                    result[field] = public_id
            return result
        elif isinstance(data, list):
            return [IDConverter.convert_response_ids(item, id_mappings) for item in data]
        else:
            return data
    
    @staticmethod
    async def convert_chat_response(db: AsyncSession, chat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换聊天会话响应数据中的ID
        
        Args:
            db: 数据库会话
            chat_data: 聊天会话数据
            
        Returns:
            转换后的数据
        """
        result = chat_data.copy()
        
        # 转换会话ID
        if 'id' in result:
            public_id = await IDConverter.get_chat_public_id(db, result['id'])
            if public_id:
                result['id'] = public_id
        
        # 转换用户ID
        if 'user_id' in result:
            user_public_id = await IDConverter.get_user_public_id(db, result['user_id'])
            if user_public_id:
                result['user_id'] = user_public_id
        
        # 转换Agent ID
        if 'agent_id' in result and result['agent_id']:
            agent_public_id = await IDConverter.get_agent_public_id(db, result['agent_id'])
            if agent_public_id:
                result['agent_id'] = agent_public_id
        
        # 转换消息列表中的ID
        if 'messages' in result and isinstance(result['messages'], list):
            for message in result['messages']:
                if 'id' in message:
                    msg_public_id = await IDConverter.get_message_public_id(db, message['id'])
                    if msg_public_id:
                        message['id'] = msg_public_id
                
                if 'session_id' in message:
                    session_public_id = await IDConverter.get_chat_public_id(db, message['session_id'])
                    if session_public_id:
                        message['session_id'] = session_public_id
                
                if 'agent_id' in message and message['agent_id']:
                    agent_public_id = await IDConverter.get_agent_public_id(db, message['agent_id'])
                    if agent_public_id:
                        message['agent_id'] = agent_public_id
        
        return result
    
    @staticmethod
    async def convert_note_response(db: AsyncSession, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换笔记响应数据中的ID
        
        Args:
            db: 数据库会话
            note_data: 笔记数据
            
        Returns:
            转换后的数据
        """
        result = note_data.copy()
        
        # 转换笔记ID
        if 'id' in result:
            public_id = await IDConverter.get_note_public_id(db, result['id'])
            if public_id:
                result['id'] = public_id
        
        # 转换用户ID
        if 'user_id' in result:
            user_public_id = await IDConverter.get_user_public_id(db, result['user_id'])
            if user_public_id:
                result['user_id'] = user_public_id
        
        # 转换会话ID
        if 'session_id' in result and result['session_id']:
            session_public_id = await IDConverter.get_chat_public_id(db, result['session_id'])
            if session_public_id:
                result['session_id'] = session_public_id
        
        return result
    
    @staticmethod
    async def convert_agent_response(db: AsyncSession, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换Agent响应数据中的ID
        
        Args:
            db: 数据库会话
            agent_data: Agent数据
            
        Returns:
            转换后的数据
        """
        result = agent_data.copy()
        
        # 转换Agent ID
        if 'id' in result:
            public_id = await IDConverter.get_agent_public_id(db, result['id'])
            if public_id:
                result['id'] = public_id
        
        # 转换用户ID
        if 'user_id' in result:
            user_public_id = await IDConverter.get_user_public_id(db, result['user_id'])
            if user_public_id:
                result['user_id'] = user_public_id
        
        return result 
    
    @staticmethod
    async def batch_get_public_ids(db: AsyncSession, db_ids: list, model_class) -> Dict[int, str]:
        """批量获取public_id - 优化性能"""
        if not db_ids:
            return {}
        
        model_name = model_class.__tablename__
        result_map = {}
        uncached_ids = []
        cache_keys_map = {}
        
        # 批量检查缓存
        for db_id in db_ids:
            cache_key = IDConverter._get_cache_key(model_name, str(db_id), "db_to_pub")
            cache_keys_map[db_id] = cache_key
            cached_result = await IDConverter._get_from_cache(cache_key)
            
            if cached_result:
                if cached_result != "None":
                    result_map[db_id] = cached_result
            else:
                uncached_ids.append(db_id)
        
        # 批量查询未命中缓存的ID
        if uncached_ids:
            try:
                stmt = select(model_class.id, model_class.public_id).where(
                    model_class.id.in_(uncached_ids)
                )
                db_result = await db.execute(stmt)
                db_rows = db_result.fetchall()
                
                # 准备批量缓存数据
                cache_pairs = {}
                for row in db_rows:
                    db_id, public_id = row
                    result_map[db_id] = public_id
                    cache_key = cache_keys_map[db_id]
                    cache_pairs[cache_key] = public_id
                
                # 为未找到的ID设置None缓存
                for db_id in uncached_ids:
                    if db_id not in result_map:
                        cache_key = cache_keys_map[db_id]
                        cache_pairs[cache_key] = "None"
                
                # 批量设置缓存
                await IDConverter._batch_set_cache(cache_pairs)
                
            except Exception as e:
                pass
        
        return result_map
    
    @staticmethod
    async def invalidate_cache(model_class, public_id: str = None, db_id: int = None):
        """失效缓存 - 在数据更新时调用"""
        if not redis_client:
            return
        
        model_name = model_class.__tablename__
        try:
            keys_to_delete = []
            
            if public_id:
                keys_to_delete.append(IDConverter._get_cache_key(model_name, public_id, "pub_to_db"))
            if db_id:
                keys_to_delete.append(IDConverter._get_cache_key(model_name, str(db_id), "db_to_pub"))
            
            if keys_to_delete:
                redis_client.delete(*keys_to_delete)
        except Exception:
            pass
    
    # 工具调用相关方法
    @staticmethod
    async def get_tool_call_db_id(db: AsyncSession, public_id: str) -> Optional[int]:
        """获取工具调用的数据库内部ID"""
        return await IDConverter.public_id_to_db_id(db, public_id, ToolCallHistory)
    
    @staticmethod
    async def get_tool_call_public_id(db: AsyncSession, db_id: int) -> Optional[str]:
        """获取工具调用的public_id"""
        return await IDConverter.db_id_to_public_id(db, db_id, ToolCallHistory) 