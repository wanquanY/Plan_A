from typing import Optional, Tuple
import os
import json

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.models.note import Note
from backend.models.agent import Agent
from backend.schemas.user import UserCreate, UserLogin, TokenData
from backend.schemas.agent import AgentCreate, ModelSettings
from backend.crud.user import get_user_by_username, get_user_by_phone, create_user
from backend.crud.agent import agent as agent_crud
from backend.utils.security import get_password_hash, verify_password, create_access_token
from backend.utils.logging import auth_logger
from backend.core.config import settings


# 读取用户手册模板
def get_user_manual_content():
    """读取用户手册HTML模板"""
    try:
        manual_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'user_manual.html')
        with open(manual_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        auth_logger.error(f"读取用户手册模板失败: {str(e)}")
        # 如果无法读取模板，返回简单的欢迎信息
        return "<h1>欢迎使用FreeWrite!</h1><p>这是一个简洁高效的笔记和写作应用。</p>"


# 创建默认用户手册笔记
async def create_default_manual_note(db: AsyncSession, user_id: int) -> Optional[Note]:
    """为新用户创建默认的用户手册笔记"""
    try:
        # 获取用户手册内容
        manual_content = get_user_manual_content()
        
        # 创建笔记
        default_note = Note(
            user_id=user_id,
            title="欢迎使用Plan_A - 用户指南",
            content=manual_content,
            is_public=False
        )
        
        db.add(default_note)
        await db.commit()
        await db.refresh(default_note)
        
        auth_logger.info(f"成功为用户ID {user_id} 创建默认用户手册笔记")
        return default_note
    except Exception as e:
        auth_logger.error(f"创建默认用户手册笔记失败: {str(e)}")
        await db.rollback()
        return None


# 创建默认AI助手
async def create_default_agent(db: AsyncSession, user_id: int) -> Optional[Agent]:
    """为新用户创建默认的AI助手"""
    try:
        # 检查用户是否已有Agent
        existing_agent = await agent_crud.get_user_agent(db, user_id)
        if existing_agent:
            auth_logger.info(f"用户ID {user_id} 已有AI助手，跳过创建")
            return existing_agent
        
        # 从环境变量解析JSON字符串，并为每个工具添加name字段
        # 解析默认工具配置
        try:
            raw_tools_config = json.loads(settings.DEFAULT_AGENT_TOOLS_ENABLED) if hasattr(settings, 'DEFAULT_AGENT_TOOLS_ENABLED') else {}
            # 为每个工具添加name字段
            tools_enabled_config = {}
            for tool_name, tool_config in raw_tools_config.items():
                tools_enabled_config[tool_name] = {
                    "enabled": tool_config.get("enabled", True),
                    "name": tool_name  # 添加name字段
                }
        except (json.JSONDecodeError, AttributeError):
            tools_enabled_config = {}
        
        # 解析默认模型设置
        try:
            model_settings_config = json.loads(settings.DEFAULT_AGENT_MODEL_SETTINGS) if hasattr(settings, 'DEFAULT_AGENT_MODEL_SETTINGS') else {}
        except (json.JSONDecodeError, AttributeError):
            model_settings_config = {"temperature": 0.7, "top_p": 0.95, "presence_penalty": 0, "frequency_penalty": 0}
        
        # 创建默认的模型设置
        default_model_settings = ModelSettings(**model_settings_config)
        
        # 创建默认agent的配置，使用配置文件中的值
        default_agent_data = AgentCreate(
            system_prompt=getattr(settings, 'DEFAULT_AGENT_SYSTEM_PROMPT', '你是一个有用的AI助手'),
            model=getattr(settings, 'DEFAULT_AGENT_MODEL', settings.OPENAI_MODEL),
            max_memory=getattr(settings, 'DEFAULT_AGENT_MAX_MEMORY', 10),
            model_settings=default_model_settings,
            tools_enabled=tools_enabled_config
        )
        
        # 创建或更新agent
        default_agent = await agent_crud.create_or_update_agent(
            db=db,
            user_id=user_id,
            obj_in=default_agent_data
        )
        
        auth_logger.info(f"成功为用户ID {user_id} 创建默认AI助手")
        return default_agent
    except Exception as e:
        auth_logger.error(f"创建默认AI助手失败: {str(e)}")
        await db.rollback()
        return None


# 用户注册服务
async def register_user(user_data: UserCreate, db: AsyncSession) -> Tuple[User, Optional[Note], Optional[Agent]]:
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
    user = await create_user(
        db=db,
        username=user_data.username,
        phone=user_data.phone,
        hashed_password=hashed_password
    )
    
    # 为新用户创建默认用户手册笔记
    default_note = await create_default_manual_note(db, user.id)
    
    # 为新用户创建默认AI助手
    default_agent = await create_default_agent(db, user.id)
    
    return user, default_note, default_agent


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