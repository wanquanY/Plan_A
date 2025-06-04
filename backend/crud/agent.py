from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.models.agent import Agent
from backend.crud.base import CRUDBase
from backend.schemas.agent import AgentCreate, AgentUpdate


class CRUDAgent(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    """Agent CRUD操作类"""
    
    async def get_user_agent(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[Agent]:
        """获取用户的唯一Agent"""
        query = select(Agent).filter(
            Agent.user_id == user_id,
            Agent.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    async def create_agent(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        obj_in: AgentCreate
    ) -> Agent:
        """创建新的Agent - 每个用户只能有一个"""
        # 检查用户是否已有Agent
        existing_agent = await self.get_user_agent(db, user_id)
        if existing_agent:
            raise ValueError("每个用户只能拥有一个AI助手，请先删除现有助手")
        
        # 将obj_in.model_settings转换为字典，确保JSON可序列化
        model_settings = obj_in.model_settings.dict() if obj_in.model_settings else None
        
        # 将工具配置转换为字典
        tools_enabled = {}
        if obj_in.tools_enabled:
            for tool_name, tool_config in obj_in.tools_enabled.items():
                tools_enabled[tool_name] = tool_config.dict() if hasattr(tool_config, 'dict') else tool_config
        
        db_obj = Agent(
            user_id=user_id,
            system_prompt=obj_in.system_prompt,
            model=obj_in.model,
            max_memory=obj_in.max_memory,
            model_settings=model_settings,
            tools_enabled=tools_enabled if tools_enabled else None
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def create_or_update_agent(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        obj_in: AgentCreate
    ) -> Agent:
        """创建或更新用户的Agent - 如果已存在则更新，否则创建"""
        existing_agent = await self.get_user_agent(db, user_id)
        
        if existing_agent:
            # 如果已存在，则更新
            update_data = obj_in.dict(exclude_unset=True)
            return await self.update_agent(db, agent_id=existing_agent.id, obj_in=update_data)
        else:
            # 如果不存在，则创建
            return await self.create_agent(db, user_id=user_id, obj_in=obj_in)
    
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
        
        # 处理tools_enabled特殊字段，确保是字典类型
        if "tools_enabled" in update_data and update_data["tools_enabled"] is not None:
            if isinstance(update_data["tools_enabled"], dict):
                tools_dict = {}
                for tool_name, tool_config in update_data["tools_enabled"].items():
                    tools_dict[tool_name] = tool_config.dict() if hasattr(tool_config, 'dict') else tool_config
                update_data["tools_enabled"] = tools_dict
        
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
        """获取用户的所有Agent - 保持向后兼容"""
        agent = await self.get_user_agent(db, user_id)
        return [agent] if agent else []
    
    async def get_public_agents(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """获取所有Agent"""
        query = select(Agent).filter(
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
        """获取用户可以使用的Agent（只能是自己的agent）"""
        query = select(Agent).filter(
            Agent.id == agent_id,
            Agent.is_deleted == False,
            Agent.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    async def check_agent_ownership(
        self,
        db: AsyncSession,
        agent_id: int,
        user_id: int
    ) -> bool:
        """检查agent是否属于指定用户"""
        query = select(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == user_id,
            Agent.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalars().first() is not None


agent = CRUDAgent(Agent) 