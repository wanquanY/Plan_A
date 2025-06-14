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
from backend.utils.id_converter import IDConverter

router = APIRouter()

def agent_to_dict(db_agent) -> Dict[str, Any]:
    """将Agent模型转换为字典"""
    return {
        "id": db_agent.public_id,
        "user_id": db_agent.user.public_id if db_agent.user else None,
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
    updated_agent = await agent.update_agent(db, agent_id=user_agent.public_id, obj_in=agent_in)
    
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
        data={"deleted_agent_id": user_agent.public_id},
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
    agent_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取指定Agent的详细信息
    """
    api_logger.info(f"获取Agent详情: 用户: {current_user.username}, Agent ID: {agent_id}")
    
    # 直接使用public_id获取Agent（CRUD层已支持）
    user_agent = await agent.get_agent_by_id(db, agent_id=agent_id)
    
    if not user_agent:
        api_logger.warning(f"Agent不存在: {agent_id}")
        raise HTTPException(status_code=404, detail="Agent不存在")
    
    # 检查Agent是否属于当前用户或是公开的
    if user_agent.user_id != current_user.id:
        api_logger.warning(f"用户无权访问Agent: 用户: {current_user.username}, Agent ID: {agent_id}")
        raise HTTPException(status_code=403, detail="无权访问此Agent")
    
    # 转换为字典
    agent_dict = agent_to_dict(user_agent)
    
    return SuccessResponse(
        data=agent_dict,
        msg="获取Agent详情成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.put("/agents/{agent_id}", response_model=AgentInDB)
async def update_agent_detail(
    request: Request,
    agent_id: str = Path(...),
    agent_in: AgentUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新指定Agent的信息
    """
    api_logger.info(f"更新Agent: 用户: {current_user.username}, Agent ID: {agent_id}")
    
    try:
        # 检查Agent是否属于当前用户（CRUD层已支持public_id）
        ownership_check = await agent.check_agent_ownership(db, agent_id=agent_id, user_id=current_user.id)
        if not ownership_check:
            api_logger.warning(f"用户无权更新Agent: 用户: {current_user.username}, Agent ID: {agent_id}")
            raise HTTPException(status_code=403, detail="无权更新此Agent")
        
        # 更新Agent（CRUD层已支持public_id）
        updated_agent = await agent.update_agent(db, agent_id=agent_id, obj_in=agent_in)
        
        if not updated_agent:
            raise HTTPException(status_code=404, detail="Agent不存在")
        
        # 转换为字典
        agent_dict = agent_to_dict(updated_agent)
        
        return SuccessResponse(
            data=agent_dict,
            msg="Agent更新成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except ValueError as e:
        api_logger.error(f"更新Agent失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/agents/{agent_id}")
async def delete_agent_detail(
    request: Request,
    agent_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除指定Agent
    """
    api_logger.info(f"删除Agent: 用户: {current_user.username}, Agent ID: {agent_id}")
    
    # 检查Agent是否属于当前用户（CRUD层已支持public_id）
    ownership_check = await agent.check_agent_ownership(db, agent_id=agent_id, user_id=current_user.id)
    if not ownership_check:
        api_logger.warning(f"用户无权删除Agent: 用户: {current_user.username}, Agent ID: {agent_id}")
        raise HTTPException(status_code=403, detail="无权删除此Agent")
    
    # 转换为数据库内部ID进行删除（删除操作仍需要内部ID）
    db_agent_id = await IDConverter.get_agent_db_id(db, agent_id)
    if not db_agent_id:
        raise HTTPException(status_code=404, detail="Agent不存在")
    
    # 删除Agent
    success = await agent.remove(db, id=db_agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent不存在")
    
    return SuccessResponse(
        data={"deleted_agent_id": agent_id},  # 返回public_id
        msg="Agent删除成功", 
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