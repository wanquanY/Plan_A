from fastapi import APIRouter, Depends, HTTPException, Path, Body, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.db.session import get_async_session
from backend.api.deps import get_current_active_user, get_db
from backend.models.user import User
from backend.core.response import SuccessResponse
from backend.crud.agent import agent
from backend.schemas.agent import AgentCreate, AgentUpdate, AgentInDB, AgentListResponse
from backend.utils.logging import api_logger
from backend.core.config import settings

router = APIRouter()

def agent_to_dict(db_agent) -> Dict[str, Any]:
    """将Agent模型转换为字典"""
    return {
        "id": db_agent.id,
        "user_id": db_agent.user_id,
        "name": db_agent.name,
        "avatar_url": db_agent.avatar_url,
        "system_prompt": db_agent.system_prompt,
        "model": db_agent.model,
        "max_memory": db_agent.max_memory,
        "model_settings": db_agent.model_settings,
        "tools_enabled": db_agent.tools_enabled,
        "is_public": db_agent.is_public,
        "created_at": db_agent.created_at.isoformat() if db_agent.created_at else None,
        "updated_at": db_agent.updated_at.isoformat() if db_agent.updated_at else None
    }


@router.get("/models")
async def list_models(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    获取可用的模型列表
    """
    api_logger.info(f"获取可用模型列表: {current_user.username}")
    
    # 返回一些常用模型作为参考，但不再限制用户使用的模型
    suggested_models = [
        "gpt-4o", 
        "claude-3-7-sonnet-20250219",
        'anthropic/claude-sonnet-4',
        'deepseek-r1-vol',
        # 添加默认模型
        settings.OPENAI_MODEL
    ]
    
    # 去除重复项
    suggested_models = list(set(suggested_models))
    
    return SuccessResponse(
        data=suggested_models,
        msg="获取模型列表成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/agents", response_model=AgentInDB)
async def create_agent(
    request: Request,
    agent_in: AgentCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建新的Agent
    """
    api_logger.info(f"创建新Agent: {agent_in.name}, 用户: {current_user.username}, 模型: {agent_in.model}")
    
    # 移除模型验证逻辑，允许使用任何模型
    
    db_agent = await agent.create_agent(db, user_id=current_user.id, obj_in=agent_in)
    
    # 转换为字典以确保JSON可序列化
    agent_dict = agent_to_dict(db_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="Agent创建成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/agents", response_model=List[AgentListResponse])
async def list_agents(
    request: Request,
    is_public: Optional[bool] = Query(None, description="是否只查询公开的Agent。不传返回用户能看到的所有Agent（包括自己的和公开的），true返回所有公开的，false返回用户自己的Agent"),
    skip: int = Query(0, description="分页起始位置"),
    limit: int = Query(100, description="分页大小，最大100条"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取Agent列表
    
    - 不传入is_public：返回用户能看到的所有Agent（包括自己的和所有公开的）
    - is_public=true：返回所有公开的Agent
    - is_public=false：返回用户自己的Agent（包括私有和公开的）
    """
    if is_public is True:
        api_logger.info(f"获取所有公开Agent列表, 用户: {current_user.username}")
        agents_list = await agent.get_public_agents(db, skip=skip, limit=limit)
    elif is_public is False:
        api_logger.info(f"获取用户自己的所有Agent列表: {current_user.username}")
        agents_list = await agent.get_user_agents(db, user_id=current_user.id)
    else:
        api_logger.info(f"获取用户能看到的所有Agent列表: {current_user.username}")
        # 获取用户自己的Agent
        user_agents = await agent.get_user_agents(db, user_id=current_user.id)
        # 获取所有公开的Agent
        public_agents = await agent.get_public_agents(db, skip=skip, limit=limit)
        
        # 合并并去重
        user_agent_ids = set(a.id for a in user_agents)
        agents_list = list(user_agents)
        
        for public_agent in public_agents:
            if public_agent.id not in user_agent_ids:
                agents_list.append(public_agent)
    
    # 转换为字典列表
    agent_list = [agent_to_dict(a) for a in agents_list]
    
    return SuccessResponse(
        data=agent_list,
        msg="获取Agent列表成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/agents/{agent_id}", response_model=AgentInDB)
async def get_agent_detail(
    request: Request,
    agent_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取Agent详情
    """
    api_logger.info(f"获取Agent详情: {agent_id}, 用户: {current_user.username}")
    
    # 检查权限 - 只能查看自己的或公开的Agent
    db_agent = await agent.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
    
    if not db_agent:
        api_logger.warning(f"Agent不存在或无权访问: {agent_id}, 用户: {current_user.username}")
        raise HTTPException(status_code=404, detail="Agent不存在或无权访问")
    
    # 转换为字典
    agent_dict = agent_to_dict(db_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="获取Agent详情成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.put("/agents/{agent_id}", response_model=AgentInDB)
async def update_agent_detail(
    request: Request,
    agent_id: int = Path(...),
    agent_in: AgentUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新Agent信息
    """
    api_logger.info(f"更新Agent: {agent_id}, 用户: {current_user.username}")
    
    # 检查Agent是否存在且属于当前用户
    db_agent = await agent.get_agent_by_id(db, agent_id=agent_id)
    if not db_agent or db_agent.user_id != current_user.id:
        api_logger.warning(f"Agent不存在或无权更新: {agent_id}, 用户: {current_user.username}")
        raise HTTPException(status_code=404, detail="Agent不存在或无权更新")
    
    # 移除模型验证逻辑，允许使用任何模型
    
    updated_agent = await agent.update_agent(db, agent_id=agent_id, obj_in=agent_in)
    
    # 转换为字典
    agent_dict = agent_to_dict(updated_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="更新Agent成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.delete("/agents/{agent_id}")
async def delete_agent(
    request: Request,
    agent_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除Agent
    """
    api_logger.info(f"删除Agent: {agent_id}, 用户: {current_user.username}")
    
    # 检查Agent是否存在且属于当前用户
    db_agent = await agent.get_agent_by_id(db, agent_id=agent_id)
    if not db_agent or db_agent.user_id != current_user.id:
        api_logger.warning(f"Agent不存在或无权删除: {agent_id}, 用户: {current_user.username}")
        raise HTTPException(status_code=404, detail="Agent不存在或无权删除")
    
    # 软删除Agent
    removed_agent = await agent.remove(db, id=agent_id)
    
    return SuccessResponse(
        data={"success": removed_agent is not None},
        msg="删除Agent成功" if removed_agent else "删除Agent失败",
        request_id=getattr(request.state, "request_id", None)
    ) 