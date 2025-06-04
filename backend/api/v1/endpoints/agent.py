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
        "system_prompt": db_agent.system_prompt,
        "model": db_agent.model,
        "max_memory": db_agent.max_memory,
        "model_settings": db_agent.model_settings,
        "tools_enabled": db_agent.tools_enabled,
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


@router.get("/my-agent", response_model=AgentInDB)
async def get_my_agent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前用户的AI助手
    """
    api_logger.info(f"获取用户AI助手: {current_user.username}")
    
    user_agent = await agent.get_user_agent(db, user_id=current_user.id)
    
    if not user_agent:
        api_logger.warning(f"用户没有AI助手: {current_user.username}")
        raise HTTPException(status_code=404, detail="您还没有AI助手，请先创建")
    
    # 转换为字典
    agent_dict = agent_to_dict(user_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="获取AI助手成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/my-agent", response_model=AgentInDB)
async def create_or_update_my_agent(
    request: Request,
    agent_in: AgentCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建或更新当前用户的AI助手
    """
    api_logger.info(f"创建或更新AI助手: 用户: {current_user.username}, 模型: {agent_in.model}")
    
    try:
        # 创建或更新用户的Agent
        db_agent = await agent.create_or_update_agent(db, user_id=current_user.id, obj_in=agent_in)
        
        # 转换为字典以确保JSON可序列化
        agent_dict = agent_to_dict(db_agent)
        
        return SuccessResponse(
            data=agent_dict,
            msg="AI助手保存成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except ValueError as e:
        api_logger.error(f"创建或更新AI助手失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/my-agent", response_model=AgentInDB)
async def update_my_agent(
    request: Request,
    agent_in: AgentUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新当前用户的AI助手
    """
    api_logger.info(f"更新AI助手, 用户: {current_user.username}")
    
    # 获取用户的Agent
    user_agent = await agent.get_user_agent(db, user_id=current_user.id)
    if not user_agent:
        api_logger.warning(f"用户没有AI助手: {current_user.username}")
        raise HTTPException(status_code=404, detail="您还没有AI助手，请先创建")
    
    # 更新Agent
    updated_agent = await agent.update_agent(db, agent_id=user_agent.id, obj_in=agent_in)
    
    # 转换为字典
    agent_dict = agent_to_dict(updated_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="AI助手更新成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.delete("/my-agent")
async def delete_my_agent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除当前用户的AI助手
    """
    api_logger.info(f"删除AI助手, 用户: {current_user.username}")
    
    # 获取用户的Agent
    user_agent = await agent.get_user_agent(db, user_id=current_user.id)
    if not user_agent:
        api_logger.warning(f"用户没有AI助手: {current_user.username}")
        raise HTTPException(status_code=404, detail="您还没有AI助手")
    
    # 软删除Agent
    await agent.remove(db, id=user_agent.id)
    
    return SuccessResponse(
        data={"deleted_agent_id": user_agent.id},
        msg="AI助手删除成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/public-agents", response_model=List[AgentListResponse])
async def list_public_agents(
    request: Request,
    skip: int = Query(0, description="分页起始位置"),
    limit: int = Query(100, description="分页大小，最大100条"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取公开的AI助手列表
    """
    api_logger.info(f"获取公开AI助手列表, 用户: {current_user.username}")
    
    public_agents = await agent.get_public_agents(db, skip=skip, limit=limit)
    
    # 转换为字典列表
    agent_list = [agent_to_dict(a) for a in public_agents]
    
    return SuccessResponse(
        data=agent_list,
        msg="获取公开AI助手列表成功",
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
    获取AI助手详情（只能查看自己的或公开的）
    """
    api_logger.info(f"获取AI助手详情: {agent_id}, 用户: {current_user.username}")
    
    # 检查权限 - 只能查看自己的或公开的Agent
    db_agent = await agent.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
    
    if not db_agent:
        api_logger.warning(f"AI助手不存在或无权访问: {agent_id}, 用户: {current_user.username}")
        raise HTTPException(status_code=404, detail="AI助手不存在或无权访问")
    
    # 转换为字典
    agent_dict = agent_to_dict(db_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="获取AI助手详情成功",
        request_id=getattr(request.state, "request_id", None)
    )


# 保留旧的API端点以向后兼容，但限制功能

@router.post("/agents", response_model=AgentInDB)
async def create_agent(
    request: Request,
    agent_in: AgentCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建新的Agent（已弃用，请使用 POST /my-agent）
    """
    api_logger.warning(f"使用已弃用的创建Agent接口: {current_user.username}")
    # 重定向到新接口
    return await create_or_update_my_agent(request, agent_in, db, current_user)


@router.get("/agents", response_model=List[AgentListResponse])
async def list_agents(
    request: Request,
    skip: int = Query(0, description="分页起始位置"),
    limit: int = Query(100, description="分页大小，最大100条"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取Agent列表（只返回用户自己的agent）
    """
    api_logger.info(f"获取用户的Agent列表: {current_user.username}")
    
    # 获取用户自己的Agent
    user_agent = await agent.get_user_agent(db, user_id=current_user.id)
    agents_list = [user_agent] if user_agent else []
    
    # 转换为字典列表
    agent_list = [agent_to_dict(a) for a in agents_list]
    
    return SuccessResponse(
        data=agent_list,
        msg="获取Agent列表成功",
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
    更新Agent信息（只能更新自己的agent）
    """
    api_logger.info(f"更新Agent: {agent_id}, 用户: {current_user.username}")
    
    # 检查Agent是否属于当前用户
    if not await agent.check_agent_ownership(db, agent_id, current_user.id):
        api_logger.warning(f"Agent不存在或无权更新: {agent_id}, 用户: {current_user.username}")
        raise HTTPException(status_code=404, detail="Agent不存在或无权更新")
    
    updated_agent = await agent.update_agent(db, agent_id=agent_id, obj_in=agent_in)
    
    # 转换为字典
    agent_dict = agent_to_dict(updated_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="更新Agent成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.delete("/agents/{agent_id}")
async def delete_agent_detail(
    request: Request,
    agent_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除Agent（只能删除自己的agent）
    """
    api_logger.info(f"删除Agent: {agent_id}, 用户: {current_user.username}")
    
    # 检查Agent是否属于当前用户
    if not await agent.check_agent_ownership(db, agent_id, current_user.id):
        api_logger.warning(f"Agent不存在或无权删除: {agent_id}, 用户: {current_user.username}")
        raise HTTPException(status_code=404, detail="Agent不存在或无权删除")
    
    await agent.remove(db, id=agent_id)
    
    return SuccessResponse(
        data={"deleted_agent_id": agent_id},
        msg="删除Agent成功",
        request_id=getattr(request.state, "request_id", None)
    ) 