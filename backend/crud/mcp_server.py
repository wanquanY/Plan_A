"""
MCP服务器配置的CRUD操作

提供MCP服务器配置的数据库操作方法。
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from backend.crud.base import CRUDBase
from backend.models.mcp_server import MCPServer
from backend.schemas.mcp_server import MCPServerCreate, MCPServerUpdate


class CRUDMCPServer(CRUDBase[MCPServer, MCPServerCreate, MCPServerUpdate]):
    """MCP服务器配置CRUD操作类"""
    
    async def get_by_name(self, db: AsyncSession, *, name: str, user_id: int) -> Optional[MCPServer]:
        """根据名称和用户ID获取服务器配置"""
        result = await db.execute(
            select(self.model).where(
                and_(
                    self.model.name == name,
                    self.model.user_id == user_id,
                    self.model.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_public_id(self, db: AsyncSession, *, public_id: str) -> Optional[MCPServer]:
        """根据公开ID获取服务器配置"""
        result = await db.execute(
            select(self.model).where(
                and_(
                    self.model.public_id == public_id,
                    self.model.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_servers(
        self, 
        db: AsyncSession, 
        *, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[MCPServer]:
        """获取用户的服务器配置列表"""
        query = select(self.model).where(self.model.user_id == user_id)
        
        if not include_deleted:
            query = query.where(self.model.is_deleted == False)
        
        query = query.offset(skip).limit(limit).order_by(desc(self.model.created_at))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_public_servers(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[MCPServer]:
        """获取公开的服务器配置列表"""
        result = await db.execute(
            select(self.model).where(
                and_(
                    self.model.is_public == True,
                    self.model.is_deleted == False
                )
            ).offset(skip).limit(limit).order_by(desc(self.model.created_at))
        )
        return result.scalars().all()
    
    async def get_auto_start_servers(self, db: AsyncSession, *, user_id: int) -> List[MCPServer]:
        """获取用户的自动启动服务器配置"""
        result = await db.execute(
            select(self.model).where(
                and_(
                    self.model.user_id == user_id,
                    self.model.enabled == True,
                    self.model.auto_start == True,
                    self.model.is_deleted == False
                )
            ).order_by(self.model.name)
        )
        return result.scalars().all()
    
    async def create_from_config(
        self, 
        db: AsyncSession, 
        *, 
        user_id: int,
        name: str, 
        config: Dict[str, Any]
    ) -> MCPServer:
        """从配置字典创建服务器"""
        server = MCPServer.from_config_dict(user_id=user_id, name=name, config=config)
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return server
    
    async def update_config(
        self, 
        db: AsyncSession, 
        *, 
        server: MCPServer, 
        config: Dict[str, Any]
    ) -> MCPServer:
        """更新服务器配置"""
        # 更新字段
        for key, value in config.items():
            if hasattr(server, key):
                setattr(server, key, value)
        
        await db.commit()
        await db.refresh(server)
        return server
    
    async def search_servers(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        name: Optional[str] = None,
        transport_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        is_public: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[MCPServer]:
        """搜索服务器配置"""
        query = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.is_deleted == False
            )
        )
        
        # 添加搜索条件
        if name:
            query = query.where(self.model.name.ilike(f"%{name}%"))
        
        if transport_type:
            query = query.where(self.model.transport_type == transport_type)
        
        if enabled is not None:
            query = query.where(self.model.enabled == enabled)
        
        if is_public is not None:
            query = query.where(self.model.is_public == is_public)
        
        if tags:
            # 搜索包含任一标签的服务器
            tag_conditions = [self.model.tags.contains([tag]) for tag in tags]
            query = query.where(or_(*tag_conditions))
        
        query = query.offset(skip).limit(limit).order_by(desc(self.model.created_at))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def bulk_import(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        servers_config: Dict[str, Dict[str, Any]],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """批量导入服务器配置"""
        results = {
            "created": [],
            "updated": [],
            "skipped": [],
            "errors": {}
        }
        
        for server_name, server_config in servers_config.items():
            try:
                # 检查是否已存在
                existing = await self.get_by_name(db, name=server_name, user_id=user_id)
                
                if existing:
                    if overwrite:
                        # 更新现有配置
                        await self.update_config(db, server=existing, config=server_config)
                        results["updated"].append(server_name)
                    else:
                        results["skipped"].append(server_name)
                else:
                    # 创建新配置
                    await self.create_from_config(
                        db, 
                        user_id=user_id,
                        name=server_name, 
                        config=server_config
                    )
                    results["created"].append(server_name)
                    
            except Exception as e:
                results["errors"][server_name] = str(e)
        
        return results
    
    async def export_user_configs(self, db: AsyncSession, *, user_id: int) -> Dict[str, Dict[str, Any]]:
        """导出用户的所有服务器配置"""
        servers = await self.get_user_servers(db, user_id=user_id, limit=1000)
        
        configs = {}
        for server in servers:
            configs[server.name] = server.to_config_dict()
        
        return configs
    
    async def get_user_servers_count(self, db: AsyncSession, *, user_id: int) -> Dict[str, int]:
        """获取用户服务器统计信息"""
        # 总数
        total_result = await db.execute(
            select(func.count(self.model.id)).where(
                and_(
                    self.model.user_id == user_id,
                    self.model.is_deleted == False
                )
            )
        )
        total = total_result.scalar()
        
        # 启用数量
        enabled_result = await db.execute(
            select(func.count(self.model.id)).where(
                and_(
                    self.model.user_id == user_id,
                    self.model.enabled == True,
                    self.model.is_deleted == False
                )
            )
        )
        enabled = enabled_result.scalar()
        
        # 按传输类型统计
        stdio_result = await db.execute(
            select(func.count(self.model.id)).where(
                and_(
                    self.model.user_id == user_id,
                    self.model.transport_type == "stdio",
                    self.model.is_deleted == False
                )
            )
        )
        stdio_count = stdio_result.scalar()
        
        sse_result = await db.execute(
            select(func.count(self.model.id)).where(
                and_(
                    self.model.user_id == user_id,
                    self.model.transport_type == "sse",
                    self.model.is_deleted == False
                )
            )
        )
        sse_count = sse_result.scalar()
        
        # 公开数量
        public_result = await db.execute(
            select(func.count(self.model.id)).where(
                and_(
                    self.model.user_id == user_id,
                    self.model.is_public == True,
                    self.model.is_deleted == False
                )
            )
        )
        public_count = public_result.scalar()
        
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "stdio_count": stdio_count,
            "sse_count": sse_count,
            "public_count": public_count,
            "private_count": total - public_count
        }
    
    async def soft_delete_by_name(self, db: AsyncSession, *, name: str, user_id: int) -> bool:
        """软删除服务器配置"""
        server = await self.get_by_name(db, name=name, user_id=user_id)
        if server:
            server.soft_delete()
            await db.commit()
            return True
        return False
    
    async def restore_by_name(self, db: AsyncSession, *, name: str, user_id: int) -> bool:
        """恢复软删除的服务器配置"""
        result = await db.execute(
            select(self.model).where(
                and_(
                    self.model.name == name,
                    self.model.user_id == user_id,
                    self.model.is_deleted == True
                )
            )
        )
        server = result.scalar_one_or_none()
        
        if server:
            server.restore()
            await db.commit()
            return True
        return False


# 创建CRUD实例
mcp_server = CRUDMCPServer(MCPServer) 