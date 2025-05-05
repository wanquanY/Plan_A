from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.schemas.user import UserCreate, UserLogin, TokenData
from backend.crud.user import get_user_by_username, get_user_by_phone, create_user
from backend.utils.security import get_password_hash, verify_password, create_access_token
from backend.utils.logging import auth_logger


# 用户注册服务
async def register_user(user_data: UserCreate, db: AsyncSession) -> User:
    # 检查用户名是否已存在
    existing_username = await get_user_by_username(db, user_data.username)
    if existing_username:
        auth_logger.warning(f"注册失败：用户名已存在 - {user_data.username}")
        raise ValueError("用户名已存在")
    
    # 检查手机号是否已存在
    existing_phone = await get_user_by_phone(db, user_data.phone)
    if existing_phone:
        auth_logger.warning(f"注册失败：手机号已被注册 - {user_data.phone}")
        raise ValueError("手机号已被注册")
    
    # 生成密码哈希
    hashed_password = get_password_hash(user_data.password)
    
    # 创建用户
    auth_logger.info(f"创建新用户 - 用户名: {user_data.username}, 手机号: {user_data.phone}")
    return await create_user(
        db=db,
        username=user_data.username,
        phone=user_data.phone,
        hashed_password=hashed_password
    )


# 验证用户登录
async def authenticate_user(db: AsyncSession, username_or_phone: str, password: str) -> Optional[User]:
    # 尝试通过用户名查找用户
    user = await get_user_by_username(db, username_or_phone)
    auth_source = "username"
    
    # 如果未找到，尝试通过手机号查找
    if not user:
        user = await get_user_by_phone(db, username_or_phone)
        auth_source = "phone"
    
    # 如果用户不存在或密码不匹配，返回None
    if not user:
        auth_logger.warning(f"认证失败：用户不存在 - {username_or_phone}")
        return None
    
    if not verify_password(password, user.hashed_password):
        auth_logger.warning(f"认证失败：密码不匹配 - 用户: {user.username}")
        return None
    
    auth_logger.info(f"用户认证成功 - {user.username} (通过{auth_source})")
    return user 