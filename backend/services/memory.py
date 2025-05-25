from typing import Dict, List, Optional, Any, Set
import json
import redis
from backend.schemas.chat import ChatMemory
from backend.utils.logging import api_logger
from backend.core.config import settings

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
    
    def _get_key(self, conversation_id: int) -> str:
        """生成Redis键名"""
        return f"memory:{conversation_id}"
        
    def _get_user_memories_key(self, user_id: int) -> str:
        """生成用户记忆索引的Redis键名"""
        return f"user:memories:{user_id}"
    
    def get_memory(self, conversation_id: int) -> ChatMemory:
        """获取指定会话的记忆，如果不存在则创建新的"""
        messages = self._get_messages_from_redis(conversation_id)
        memory = ChatMemory(messages=messages)
        return memory
    
    def _get_messages_from_redis(self, conversation_id: int) -> List[Dict[str, str]]:
        """从Redis获取消息记录"""
        try:
            key = self._get_key(conversation_id)
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
    
    def _save_messages_to_redis(self, conversation_id: int, messages: List[Dict[str, str]]):
        """保存消息到Redis"""
        try:
            key = self._get_key(conversation_id)
            
            # 限制消息数量
            if len(messages) > self.max_messages:
                messages = messages[-self.max_messages:]
                
            # 保存到Redis
            self.redis.set(key, json.dumps(messages), ex=self.ttl)
        except Exception as e:
            api_logger.error(f"保存消息到Redis失败: {str(e)}", exc_info=True)
            # 即使保存失败也不抛出异常，允许应用继续运行
    
    def _register_memory_to_user(self, user_id: int, conversation_id: int):
        """将会话记忆注册到用户的记忆索引中"""
        try:
            user_key = self._get_user_memories_key(user_id)
            
            # 使用有序集合记录用户的会话记忆，分数为当前时间戳（最近使用的排在前面）
            import time
            current_time = time.time()
            self.redis.zadd(user_key, {str(conversation_id): current_time})
            
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
    
    def _update_memory_usage_time(self, user_id: int, conversation_id: int):
        """更新会话记忆的使用时间（保持最近使用的记忆）"""
        try:
            user_key = self._get_user_memories_key(user_id)
            import time
            current_time = time.time()
            self.redis.zadd(user_key, {str(conversation_id): current_time})
        except Exception as e:
            api_logger.error(f"更新用户记忆会话使用时间失败: {str(e)}", exc_info=True)
            # 即使失败也继续，不影响主要功能
    
    def add_user_message(self, conversation_id: int, content: str, user_id: Optional[int] = None):
        """添加用户消息到指定会话的记忆中"""
        messages = self._get_messages_from_redis(conversation_id)
        messages.append({"role": "user", "content": content})
        self._save_messages_to_redis(conversation_id, messages)
        api_logger.debug(f"会话 {conversation_id} 添加用户消息: {content[:50]}...")
        
        # 如果提供了用户ID，更新用户的记忆索引
        if user_id:
            self._register_memory_to_user(user_id, conversation_id)
    
    def add_assistant_message(self, conversation_id: int, content: str, user_id: Optional[int] = None):
        """添加助手消息到指定会话的记忆中"""
        messages = self._get_messages_from_redis(conversation_id)
        messages.append({"role": "assistant", "content": content})
        self._save_messages_to_redis(conversation_id, messages)
        api_logger.debug(f"会话 {conversation_id} 添加助手消息: {content[:50]}...")
        
        # 如果提供了用户ID，更新用户的记忆索引
        if user_id:
            self._update_memory_usage_time(user_id, conversation_id)
    
    def get_messages(self, conversation_id: int) -> List[Dict[str, str]]:
        """获取指定会话的所有消息"""
        return self._get_messages_from_redis(conversation_id)
    
    def clear_memory(self, conversation_id: int):
        """清空指定会话的记忆"""
        try:
            key = self._get_key(conversation_id)
            self.redis.delete(key)
            api_logger.info(f"已清空会话 {conversation_id} 的记忆")
        except Exception as e:
            api_logger.error(f"清空会话记忆失败: {str(e)}", exc_info=True)
            # 即使清空失败也不抛出异常
    
    def truncate_memory_after_message(self, conversation_id: int, message_index: int) -> bool:
        """
        截断特定消息后的所有记忆
        
        Args:
            conversation_id: 会话ID
            message_index: 消息索引，保留该索引及之前的消息，删除之后的消息
            
        Returns:
            bool: 是否截断成功
        """
        try:
            key = self._get_key(conversation_id)
            messages = self._get_messages_from_redis(conversation_id)
            
            if not messages or message_index < 0 or message_index >= len(messages):
                api_logger.warning(f"截断记忆失败: 会话 {conversation_id} 的消息索引 {message_index} 无效")
                return False
            
            # 保留到指定索引的消息（包含该索引）
            truncated_messages = messages[:message_index + 1]
            self._save_messages_to_redis(conversation_id, truncated_messages)
            
            api_logger.info(f"会话 {conversation_id} 已截断记忆，保留 {len(truncated_messages)} 条消息，删除 {len(messages) - len(truncated_messages)} 条消息")
            return True
        except Exception as e:
            api_logger.error(f"截断记忆失败: {str(e)}", exc_info=True)
            return False
            
    def replace_message_and_truncate(self, conversation_id: int, message_index: int, new_content: str, role: str = None) -> bool:
        """
        替换特定消息的内容，并截断该消息之后的所有记忆
        
        Args:
            conversation_id: 会话ID
            message_index: 消息索引
            new_content: 新的消息内容
            role: 消息角色，如果为None则保持原角色
            
        Returns:
            bool: 是否操作成功
        """
        try:
            key = self._get_key(conversation_id)
            messages = self._get_messages_from_redis(conversation_id)
            
            if not messages or message_index < 0 or message_index >= len(messages):
                api_logger.warning(f"替换消息失败: 会话 {conversation_id} 的消息索引 {message_index} 无效")
                return False
            
            # 获取原始消息的角色
            current_role = messages[message_index]["role"]
            # 使用指定角色或者保持原角色
            message_role = role if role else current_role
            
            # 保留到指定索引之前的消息
            modified_messages = messages[:message_index]
            # 添加替换后的消息
            modified_messages.append({"role": message_role, "content": new_content})
            
            # 保存修改后的消息
            self._save_messages_to_redis(conversation_id, modified_messages)
            
            api_logger.info(f"会话 {conversation_id} 已替换消息索引 {message_index} 并截断后续消息，现有消息数量 {len(modified_messages)}，原始消息数量 {len(messages)}")
            return True
        except Exception as e:
            api_logger.error(f"替换消息失败: {str(e)}", exc_info=True)
            return False
    
    def delete_memory(self, conversation_id: int):
        """删除指定会话的记忆（与clear_memory相同）"""
        self.clear_memory(conversation_id)
        
    def restore_memory_from_db(self, conversation_id: int, db_messages: List[Dict[str, Any]], user_id: Optional[int] = None):
        """从数据库记录恢复记忆到Redis
        
        Args:
            conversation_id: 会话ID
            db_messages: 从数据库获取的消息列表，格式为[{"role": "user", "content": "内容"}, ...]
            user_id: 用户ID，用于管理用户的记忆数量限制
        """
        if not db_messages:
            api_logger.warning(f"会话 {conversation_id} 没有可恢复的数据库消息")
            return False
            
        # 格式化消息为Redis需要的格式
        redis_messages = []
        for msg in db_messages:
            if "role" in msg and "content" in msg:
                redis_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 保存到Redis
        if redis_messages:
            self._save_messages_to_redis(conversation_id, redis_messages)
            
            # 如果提供了用户ID，更新用户的记忆索引
            if user_id:
                self._register_memory_to_user(user_id, conversation_id)
                
            api_logger.info(f"会话 {conversation_id} 从数据库恢复了 {len(redis_messages)} 条消息到Redis")
            return True
        return False
            
    def update_message_content(self, conversation_id: int, message_index: int, new_content: str) -> bool:
        """
        更新指定消息的内容，不截断后续消息
        
        Args:
            conversation_id: 会话ID
            message_index: 消息索引
            new_content: 新的消息内容
            
        Returns:
            bool: 是否操作成功
        """
        try:
            key = self._get_key(conversation_id)
            messages = self._get_messages_from_redis(conversation_id)
            
            if not messages or message_index < 0 or message_index >= len(messages):
                api_logger.warning(f"更新消息失败: 会话 {conversation_id} 的消息索引 {message_index} 无效")
                return False
            
            # 保存原始角色
            original_role = messages[message_index]["role"]
            
            # 更新指定消息的内容
            messages[message_index]["content"] = new_content
            
            # 保存更新后的消息列表
            self._save_messages_to_redis(conversation_id, messages)
            
            api_logger.info(f"会话 {conversation_id} 已更新消息索引 {message_index} 的内容，角色: {original_role}")
            return True
        except Exception as e:
            api_logger.error(f"更新消息内容失败: {str(e)}", exc_info=True)
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