from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import BaseModel as DBBaseModel

ModelType = TypeVar("ModelType", bound=DBBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    基础CRUD操作类
    """
    def __init__(self, model: Type[ModelType]):
        """
        初始化CRUD对象
        
        Args:
            model: SQLAlchemy模型类
        """
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """
        根据ID获取对象
        
        Args:
            db: 数据库会话
            id: 对象ID
            
        Returns:
            查询到的对象或None
        """
        query = select(self.model).filter(self.model.id == id, self.model.is_deleted == False)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        获取多个对象
        
        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 返回记录数限制
            
        Returns:
            对象列表
        """
        query = select(self.model).filter(self.model.is_deleted == False).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        创建对象
        
        Args:
            db: 数据库会话
            obj_in: 创建对象的schema
            
        Returns:
            创建的对象
        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        更新对象
        
        Args:
            db: 数据库会话
            db_obj: 要更新的数据库对象
            obj_in: 更新对象的schema或字典
            
        Returns:
            更新后的对象
        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        执行软删除
        
        Args:
            db: 数据库会话
            id: 要删除的对象ID
            
        Returns:
            被删除的对象或None
        """
        obj = await self.get(db, id)
        if obj:
            # 软删除
            obj.soft_delete()
            db.add(obj)
            await db.commit()
        return obj

    async def hard_remove(self, db: AsyncSession, *, id: int) -> bool:
        """
        执行硬删除（物理删除）
        
        Args:
            db: 数据库会话
            id: 要删除的对象ID
            
        Returns:
            是否成功删除
        """
        obj = await db.get(self.model, id)
        if obj:
            await db.delete(obj)
            await db.commit()
            return True
        return False
    
    async def restore(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        恢复被软删除的对象
        
        Args:
            db: 数据库会话
            id: 要恢复的对象ID
            
        Returns:
            恢复的对象或None
        """
        # 查询被标记为删除的对象
        query = select(self.model).filter(self.model.id == id, self.model.is_deleted == True)
        result = await db.execute(query)
        obj = result.scalars().first()
        
        if obj:
            # 恢复对象
            obj.restore()
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
        
        return obj 