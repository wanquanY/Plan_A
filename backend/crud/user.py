from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """通过ID获取用户"""
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """通过用户名获取用户"""
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
    """通过手机号获取用户"""
    result = await db.execute(select(User).filter(User.phone == phone))
    return result.scalars().first()


async def create_user(
    db: AsyncSession, username: str, phone: str, hashed_password: str
) -> User:
    """创建新用户"""
    from datetime import datetime
    
    db_user = User(
        username=username,
        phone=phone,
        hashed_password=hashed_password,
        is_active=True,
        updated_at=datetime.now()  # 手动设置updated_at
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


async def update_user(
    db: AsyncSession, user_id: int, **kwargs
) -> Optional[User]:
    """更新用户信息"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


async def delete_user(
    db: AsyncSession, user_id: int
) -> bool:
    """删除用户"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    
    return True 