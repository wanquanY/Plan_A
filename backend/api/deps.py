from typing import AsyncGenerator

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.session import get_async_session
from backend.models.user import User
from backend.schemas.user import TokenData
from backend.crud.user import get_user_by_username
from backend.utils.logging import auth_logger
from backend.core.exceptions import AuthenticationException, PermissionDeniedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# 获取数据库会话依赖
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


# 获取当前用户依赖
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        if username is None:
            auth_logger.warning(f"Token缺少sub字段: {payload}")
            raise AuthenticationException(msg="无效的认证凭证")
        token_data = TokenData(username=username)
    except JWTError as e:
        auth_logger.warning(f"Token解析失败: {e}")
        raise AuthenticationException(msg="无效的认证凭证")
    
    user = await get_user_by_username(db, username=token_data.username)
    if user is None:
        auth_logger.warning(f"用户不存在: {token_data.username}")
        raise AuthenticationException(msg="无效的认证凭证")
    
    auth_logger.debug(f"用户已认证: {user.username}")
    return user


# 获取当前活跃用户依赖
async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        auth_logger.warning(f"被禁用的用户尝试访问: {current_user.username}")
        raise PermissionDeniedException(msg="用户已被禁用")
    return current_user 