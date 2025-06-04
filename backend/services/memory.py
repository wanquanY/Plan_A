from typing import Dict, List, Optional, Any, Set
import json
import redis
import time
from backend.schemas.chat import ChatMemory
from backend.utils.logging import api_logger
from backend.core.config import settings
from functools import lru_cache

# 创建Redis客户端
redis_client = redis.Redis.from_url(
    url=settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

class MemoryService:
    """聊天记忆服务，使用Redis管理不同会话的聊天记忆"""
    
    def __init__(self):
        self.redis = redis_client
        self.ttl = settings.REDIS_TTL  # 记忆有效期，单位秒
        self.max_messages = settings.REDIS_MAX_MEMORY_MESSAGES  # 每个会话的最大消息数
        self.max_user_memories = settings.REDIS_MAX_USER_MEMORIES  # 每个用户的最大记忆会话数
        api_logger.info(f"记忆服务初始化完成 - 使用Redis存储，TTL={self.ttl}秒，最大消息数={self.max_messages}，每用户最大会话数={self.max_user_memories}")
    
    def _get_key(self, session_id: int) -> str:
        """生成Redis中记忆的key"""
        return f"memory:{session_id}"
        
    def _get_user_memories_key(self, user_id: int) -> str:
        """生成用户记忆索引的Redis键名"""
        return f"user:memories:{user_id}"
    
    @lru_cache(maxsize=100)
    def get_memory(self, session_id: int) -> ChatMemory:
        """获取会话记忆，带LRU缓存"""
        messages = self._get_messages_from_redis(session_id)
        return ChatMemory(messages=messages)
    
    def _get_messages_from_redis(self, session_id: int) -> List[Dict[str, str]]:
        """从Redis获取消息记录"""
        try:
            key = self._get_key(session_id)
            data = self.redis.get(key)
            
            if data:
                try:
                    # 刷新过期时间
                    self.redis.expire(key, self.ttl)
                    return json.loads(data)
                except json.JSONDecodeError:
                    api_logger.error(f"解析Redis数据失败: {data}")
                    return []
            return []
        except Exception as e:
            api_logger.error(f"从Redis获取消息记录失败: {str(e)}", exc_info=True)
            return []  # 返回空列表，确保即使Redis出错也能继续工作
    
    def _save_messages_to_redis(self, session_id: int, messages: List[Dict[str, str]]):
        """保存消息记录到Redis"""
        try:
            key = self._get_key(session_id)
            
            # 限制消息数量
            if len(messages) > self.max_messages:
                messages = messages[-self.max_messages:]
                
            # 保存到Redis
            self.redis.set(key, json.dumps(messages), ex=self.ttl)
        except Exception as e:
            api_logger.error(f"保存消息到Redis失败: {str(e)}", exc_info=True)
            # 即使保存失败也不抛出异常，允许应用继续运行
    
    def _register_memory_to_user(self, user_id: int, session_id: int):
        """将记忆关联到用户，用于用户记忆管理"""
        try:
            if not user_id:
                return
            
            # 用户记忆集合的key
            user_key = self._get_user_memories_key(user_id)
            current_time = time.time()
            
            # 将会话ID添加到用户的记忆集合中，分数为时间戳
            self.redis.zadd(user_key, {str(session_id): current_time})
            
            # 获取用户所有记忆会话
            all_memories = self.redis.zrevrange(user_key, 0, -1)
            
            # 如果超过限制，清理最旧的会话记忆
            if len(all_memories) > self.max_user_memories:
                # 获取需要清理的会话ID列表
                memories_to_remove = all_memories[self.max_user_memories:]
                
                # 过滤和转换有效的会话ID
                valid_memories_to_remove = []
                for mem_id in memories_to_remove:
                    try:
                        # 处理字节串和字符串
                        if isinstance(mem_id, bytes):
                            mem_id_str = mem_id.decode('utf-8')
                        else:
                            mem_id_str = str(mem_id)
                        
                        # 跳过无效的ID
                        if mem_id_str == 'None' or not mem_id_str.strip():
                            continue
                            
                        # 尝试转换为整数
                        mem_id_int = int(mem_id_str)
                        valid_memories_to_remove.append(mem_id_int)
                    except (ValueError, AttributeError) as e:
                        api_logger.warning(f"跳过无效的会话ID: {mem_id}, 错误: {e}")
                        continue
                
                if valid_memories_to_remove:
                    api_logger.info(f"用户 {user_id} 记忆会话数超过限制，清理 {len(valid_memories_to_remove)} 个旧会话: {', '.join(map(str, valid_memories_to_remove))}")
                    
                    # 删除这些会话的记忆
                    for mem_id in valid_memories_to_remove:
                        self.clear_memory(mem_id)
                    
                    # 从用户索引中移除（移除所有超出限制的项，包括无效的）
                    self.redis.zremrangebyrank(user_key, 0, len(memories_to_remove) - 1)
                else:
                    api_logger.warning(f"用户 {user_id} 没有有效的会话ID需要清理")
                    
        except Exception as e:
            api_logger.error(f"注册用户记忆会话失败: {str(e)}", exc_info=True)
            # 即使失败也继续，不影响主要功能
    
    def _update_memory_usage_time(self, user_id: int, session_id: int):
        """更新记忆的使用时间"""
        try:
            if not user_id:
                return            
            user_key = self._get_user_memories_key(user_id)
            current_time = time.time()
            self.redis.zadd(user_key, {str(session_id): current_time})
        except Exception as e:
            api_logger.warning(f"更新记忆使用时间失败: {e}")
    
    def add_user_message(self, session_id: int, content: str, user_id: Optional[int] = None):
        """添加用户消息到会话记忆中"""
        messages = self._get_messages_from_redis(session_id)
        messages.append({"role": "user", "content": content})
        self._save_messages_to_redis(session_id, messages)
        api_logger.debug(f"会话 {session_id} 添加用户消息: {content[:50]}...")
        
        # 关联到用户
        if user_id:
            self._register_memory_to_user(user_id, session_id)
    
    def add_assistant_message(self, session_id: int, content: str, user_id: Optional[int] = None):
        """添加助手消息到会话记忆中"""
        messages = self._get_messages_from_redis(session_id)
        messages.append({"role": "assistant", "content": content})
        self._save_messages_to_redis(session_id, messages)
        api_logger.debug(f"会话 {session_id} 添加助手消息: {content[:50]}...")
        
        # 更新使用时间
        if user_id:
            self._update_memory_usage_time(user_id, session_id)
    
    def get_messages(self, session_id: int) -> List[Dict[str, str]]:
        """获取会话中的所有消息"""
        return self._get_messages_from_redis(session_id)
    
    def clear_memory(self, session_id: int):
        """清空指定会话的记忆"""
        try:
            key = self._get_key(session_id)
            self.redis.delete(key)
            api_logger.info(f"已清空会话 {session_id} 的记忆")
        except Exception as e:
            api_logger.error(f"清空记忆失败: {e}")
    
    def truncate_memory_after_message(self, session_id: int, message_index: int) -> bool:
        """
        截断指定消息索引之后的记忆
        
        Args:
            session_id: 会话ID
            message_index: 消息索引，从该索引后的消息将被删除（不包括该索引）
            
        Returns:
            bool: 是否成功截断
        """
        try:
            key = self._get_key(session_id)
            messages = self._get_messages_from_redis(session_id)
            
            if message_index < 0 or message_index >= len(messages):
                api_logger.warning(f"截断记忆失败: 会话 {session_id} 的消息索引 {message_index} 无效")
                return False
            
            # 保留索引之前的消息（包括该索引）
            truncated_messages = messages[:message_index + 1]
            self._save_messages_to_redis(session_id, truncated_messages)
            
            api_logger.info(f"会话 {session_id} 已截断记忆，保留 {len(truncated_messages)} 条消息，删除 {len(messages) - len(truncated_messages)} 条消息")
            return True
            
        except Exception as e:
            api_logger.error(f"截断记忆失败: {e}")
            return False
            
    def replace_message_and_truncate(self, session_id: int, message_index: int, new_content: str, role: str = None) -> bool:
        """
        替换指定索引的消息内容，并截断后续消息
        
        Args:
            session_id: 会话ID
            message_index: 要替换的消息索引
            new_content: 新的消息内容
            role: 消息角色，如果为None则保持原角色
            
        Returns:
            bool: 是否成功替换和截断
        """
        try:
            key = self._get_key(session_id)
            messages = self._get_messages_from_redis(session_id)
            
            if message_index < 0 or message_index >= len(messages):
                api_logger.warning(f"替换消息失败: 会话 {session_id} 的消息索引 {message_index} 无效")
                return False
            
            # 替换指定索引的消息
            original_role = messages[message_index].get("role", "user")
            messages[message_index] = {
                "role": role if role is not None else original_role,
                "content": new_content
            }
            
            # 截断后续消息
            modified_messages = messages[:message_index + 1]
            self._save_messages_to_redis(session_id, modified_messages)
            
            api_logger.info(f"会话 {session_id} 已替换消息索引 {message_index} 并截断后续消息，现有消息数量 {len(modified_messages)}，原始消息数量 {len(messages)}")
            return True
            
        except Exception as e:
            api_logger.error(f"替换消息失败: {e}")
            return False
    
    def delete_memory(self, session_id: int):
        """删除指定会话的记忆（别名，同clear_memory）"""
        self.clear_memory(session_id)
        
    def restore_memory_from_db(self, session_id: int, db_messages: List[Dict[str, Any]], user_id: Optional[int] = None):
        """
        从数据库消息恢复Redis记忆
        
        Args:
            session_id: 会话ID
            db_messages: 从数据库查询的消息列表
            user_id: 可选的用户ID，用于关联记忆
        """
        try:
            if not db_messages:
                api_logger.warning(f"会话 {session_id} 没有可恢复的数据库消息")
                return False
                
            # 转换数据库消息格式为Redis格式
            redis_messages = []
            for msg in db_messages:
                redis_msg = {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                }
                # 保留其他可能的字段
                for key in ["tokens", "prompt_tokens", "total_tokens", "agent_id"]:
                    if key in msg and msg[key] is not None:
                        redis_msg[key] = msg[key]
                redis_messages.append(redis_msg)
            
            # 保存到Redis
            self._save_messages_to_redis(session_id, redis_messages)
            
            # 关联到用户
            if user_id:
                self._register_memory_to_user(user_id, session_id)
                
            api_logger.info(f"会话 {session_id} 从数据库恢复了 {len(redis_messages)} 条消息到Redis")
            return True
            
        except Exception as e:
            api_logger.error(f"从数据库恢复记忆失败: {e}")
            return False
            
    def update_message_content(self, session_id: int, message_index: int, new_content: str) -> bool:
        """
        更新指定索引消息的内容（不截断后续消息）
        
        Args:
            session_id: 会话ID
            message_index: 要更新的消息索引
            new_content: 新的消息内容
            
        Returns:
            bool: 是否成功更新
        """
        try:
            key = self._get_key(session_id)
            messages = self._get_messages_from_redis(session_id)
            
            if message_index < 0 or message_index >= len(messages):
                api_logger.warning(f"更新消息失败: 会话 {session_id} 的消息索引 {message_index} 无效")
                return False
            
            # 更新消息内容，保持原角色
            original_role = messages[message_index].get("role", "user")
            messages[message_index]["content"] = new_content
            
            # 保存更新后的消息列表
            self._save_messages_to_redis(session_id, messages)
            
            api_logger.info(f"会话 {session_id} 已更新消息索引 {message_index} 的内容，角色: {original_role}")
            return True
            
        except Exception as e:
            api_logger.error(f"更新消息内容失败: {e}")
            return False
    
    def get_user_memory_sessions(self, user_id: int) -> List[int]:
        """获取用户当前的记忆会话ID列表（按最近使用时间排序）"""
        try:
            user_key = self._get_user_memories_key(user_id)
            memory_ids = self.redis.zrevrange(user_key, 0, -1)
            return [int(mem_id) for mem_id in memory_ids]
        except Exception as e:
            api_logger.error(f"获取用户记忆会话列表失败: {str(e)}", exc_info=True)
            return []  # 返回空列表，确保API不会因为Redis错误而中断
        
    def count_user_memories(self, user_id: int) -> int:
        """获取用户当前的记忆会话数量"""
        try:
            user_key = self._get_user_memories_key(user_id)
            return self.redis.zcard(user_key)
        except Exception as e:
            api_logger.error(f"获取用户记忆会话数量失败: {str(e)}", exc_info=True)
            return 0  # 返回0，确保API不会因为Redis错误而中断

# 创建全局记忆服务实例
memory_service = MemoryService() 