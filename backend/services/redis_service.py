import redis.asyncio as redis
from typing import Optional, Any
from backend.core.config import settings
from backend.utils.logging import app_logger

class RedisService:
    """Redis缓存服务"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    async def init(self):
        """初始化Redis连接"""
        if self._initialized:
            return
        
        try:
            self.client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            # 测试连接
            await self.client.ping()
            self._initialized = True
            app_logger.info("Redis连接初始化成功")
        except Exception as e:
            app_logger.error(f"Redis连接初始化失败: {e}")
            self.client = None
    
    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        if not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as e:
            app_logger.warning(f"Redis GET失败: {e}")
            return None
    
    async def set(self, key: str, value: str) -> bool:
        """设置缓存值"""
        if not self.client:
            return False
        try:
            await self.client.set(key, value)
            return True
        except Exception as e:
            app_logger.warning(f"Redis SET失败: {e}")
            return False
    
    async def setex(self, key: str, ttl: int, value: str) -> bool:
        """设置带过期时间的缓存值"""
        if not self.client:
            return False
        try:
            await self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            app_logger.warning(f"Redis SETEX失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.client:
            return False
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            app_logger.warning(f"Redis DELETE失败: {e}")
            return False
    
    async def close(self):
        """关闭Redis连接"""
        if self.client:
            await self.client.close()
            self._initialized = False

# 全局Redis服务实例
redis_service = RedisService() 