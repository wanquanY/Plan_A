from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.models.agent import Agent
from backend.crud.base import CRUDBase
from backend.schemas.agent import AgentCreate, AgentUpdate


class CRUDAgent(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    """Agent CRUD操作类"""
    
    async def create_agent(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        obj_in: AgentCreate
    ) -> Agent:
        """创建新的Agent"""
        # 将obj_in.model_settings转换为字典，确保JSON可序列化
        model_settings = obj_in.model_settings.dict() if obj_in.model_settings else None
        
        db_obj = Agent(
            user_id=user_id,
            name=obj_in.name,
            avatar_url=obj_in.avatar_url,
            system_prompt=obj_in.system_prompt,
            model=obj_in.model,
            max_memory=obj_in.max_memory,
            model_settings=model_settings,
            is_public=obj_in.is_public
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update_agent(
        self,
        db: AsyncSession,
        *,
        agent_id: int,
        obj_in: Union[AgentUpdate, Dict[str, Any]]
    ) -> Optional[Agent]:
        """更新Agent信息"""
        agent = await self.get(db, agent_id)
        if not agent:
            return None
        
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
        
        # 处理model_settings特殊字段，确保是字典类型
        if "model_settings" in update_data and update_data["model_settings"] is not None:
            if hasattr(update_data["model_settings"], "dict"):
                update_data["model_settings"] = update_data["model_settings"].dict()
        
        for field in update_data:
            if hasattr(agent, field) and field != "id" and field != "user_id":
                setattr(agent, field, update_data[field])
        
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent
    
    async def get_user_agents(
        self,
        db: AsyncSession,
        user_id: int
    ) -> List[Agent]:
        """获取用户的所有Agent"""
        query = select(Agent).filter(
            Agent.user_id == user_id,
            Agent.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_public_agents(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """获取所有公开的Agent"""
        query = select(Agent).filter(
            Agent.is_public == True,
            Agent.is_deleted == False
        ).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_agent_by_id(
        self, 
        db: AsyncSession, 
        agent_id: int
    ) -> Optional[Agent]:
        """根据ID获取Agent（包括非公开的）"""
        query = select(Agent).filter(
            Agent.id == agent_id,
            Agent.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_agent_for_user(
        self,
        db: AsyncSession,
        agent_id: int,
        user_id: int
    ) -> Optional[Agent]:
        """获取用户可以使用的Agent（包括自己的和公开的）"""
        query = select(Agent).filter(
            Agent.id == agent_id,
            Agent.is_deleted == False,
            (Agent.user_id == user_id) | (Agent.is_public == True)
        )
        result = await db.execute(query)
        return result.scalars().first()


agent = CRUDAgent(Agent) 