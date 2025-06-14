from fastapi import APIRouter, Depends, Request, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from backend.api.deps import get_db, get_current_active_user
from backend.models.user import User
from backend.schemas.user import User as UserSchema, UserUpdate, PasswordChange
from backend.utils.logging import api_logger
from backend.core.response import SuccessResponse
from backend.utils.security import verify_password, get_password_hash
from backend.crud.user import update_user

router = APIRouter()


@router.get("/me")
async def read_users_me(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户信息
    """
    api_logger.info(f"获取用户信息: {current_user.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
    
    # 将UTC时间转换为北京时间（UTC+8）
    def to_beijing_time(dt):
        if dt:
            # 确保datetime有时区信息
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 转换为北京时间
            beijing_tz = timezone(timedelta(hours=8))
            return dt.astimezone(beijing_tz)
        return None
    
    # 转换User对象为可序列化的字典
    user_dict = {
        "id": current_user.public_id,
        "username": current_user.username,
        "phone": current_user.phone,
        "avatar_url": current_user.avatar_url,
        "is_active": current_user.is_active,
        "created_at": to_beijing_time(current_user.created_at).isoformat() if current_user.created_at else None,
        "updated_at": to_beijing_time(current_user.updated_at).isoformat() if current_user.updated_at else None
    }
    
    return SuccessResponse(
        data=user_dict,
        msg="获取用户信息成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.put("/me")
async def update_user_info(
    request: Request,
    user_update: UserUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新当前用户信息
    """
    api_logger.info(f"更新用户信息: {current_user.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
    
    # 将更新数据转换为字典并移除None值
    update_data = user_update.dict(exclude_unset=True)
    
    # 确保不能修改密码，密码有专门的接口修改
    if "password" in update_data:
        del update_data["password"]
    
    if not update_data:
        return SuccessResponse(
            data=None,
            msg="没有要更新的数据",
            request_id=getattr(request.state, "request_id", None)
        )
    
    # 更新用户信息
    updated_user = await update_user(db, current_user.id, **update_data)
    
    # 将UTC时间转换为北京时间
    def to_beijing_time(dt):
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            beijing_tz = timezone(timedelta(hours=8))
            return dt.astimezone(beijing_tz)
        return None
    
    # 转换User对象为可序列化的字典
    user_dict = {
        "id": updated_user.public_id,
        "username": updated_user.username,
        "phone": updated_user.phone,
        "avatar_url": updated_user.avatar_url,
        "is_active": updated_user.is_active,
        "created_at": to_beijing_time(updated_user.created_at).isoformat() if updated_user.created_at else None,
        "updated_at": to_beijing_time(updated_user.updated_at).isoformat() if updated_user.updated_at else None
    }
    
    return SuccessResponse(
        data=user_dict,
        msg="更新用户信息成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.put("/me/password")
async def change_password(
    request: Request,
    password_change: PasswordChange = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    修改用户密码
    """
    api_logger.info(f"修改密码: {current_user.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
    
    # 验证当前密码是否正确
    if not verify_password(password_change.current_password, current_user.hashed_password):
        api_logger.warning(f"当前密码验证失败: {current_user.username}")
        raise HTTPException(status_code=400, detail="当前密码不正确")
    
    # 验证新密码和确认密码是否一致
    if password_change.new_password != password_change.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")
    
    # 生成新密码的哈希
    hashed_password = get_password_hash(password_change.new_password)
    
    # 更新用户密码
    await update_user(db, current_user.id, hashed_password=hashed_password)
    
    return SuccessResponse(
        data=None,
        msg="密码修改成功",
        request_id=getattr(request.state, "request_id", None)
    ) 