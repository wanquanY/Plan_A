from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from backend.api.deps import get_db
from backend.core.config import settings
from backend.models.user import User
from backend.schemas.user import UserCreate, User as UserSchema, Token
from backend.services.user import register_user, authenticate_user
from backend.utils.security import create_access_token
from backend.utils.logging import auth_logger
from backend.core.response import SuccessResponse
from backend.core.exceptions import AuthenticationException, BusinessException

router = APIRouter()


@router.post("/register")
async def create_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册
    """
    try:
        auth_logger.info(f"用户注册请求: {user_data.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
        user, default_note = await register_user(user_data, db)
        auth_logger.info(f"用户注册成功: {user.username}")
        
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
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "is_active": user.is_active,
            "created_at": to_beijing_time(user.created_at).isoformat() if user.created_at else None,
            "updated_at": to_beijing_time(user.updated_at).isoformat() if user.updated_at else None
        }
        
        # 添加默认笔记信息到响应中
        response_data = {
            "user": user_dict
        }
        
        if default_note:
            response_data["default_note"] = {
                "id": default_note.id,
                "title": default_note.title
            }
        
        return SuccessResponse(
            data=response_data,
            msg="注册成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except ValueError as e:
        auth_logger.warning(f"用户注册失败: {user_data.username}, 错误: {str(e)}")
        raise BusinessException(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录获取JWT令牌
    """
    auth_logger.info(f"用户登录请求: {form_data.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
    
    user = await authenticate_user(
        db, form_data.username, form_data.password
    )
    if not user:
        auth_logger.warning(f"用户登录失败: {form_data.username}, 凭证无效")
        raise AuthenticationException(msg="用户名/手机号或密码不正确")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    auth_logger.info(f"用户登录成功: {user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"} 