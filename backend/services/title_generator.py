import asyncio
from typing import Optional
from openai import AsyncOpenAI

from backend.core.config import settings
from backend.utils.logging import api_logger
from backend.utils.id_converter import IDConverter
from sqlalchemy.ext.asyncio import AsyncSession

# 获取配置
api_key = settings.OPENAI_API_KEY
base_url = settings.OPENAI_BASE_URL
model = settings.OPENAI_MODEL

# 确保base_url以/v1结尾
if base_url and not base_url.endswith('/v1'):
    base_url = base_url.rstrip() + '/v1'

# 配置OpenAI客户端
client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url
)

async def generate_title_with_ai(session_id: str, user_message: str, db: Optional[AsyncSession] = None) -> str:
    """
    使用AI生成会话标题
    
    Args:
        session_id: 会话public_id
        user_message: 用户消息内容
        db: 数据库会话（可选，用于ID转换）
        
    Returns:
        生成的标题
    """
    try:
        api_logger.info(f"开始调用AI生成会话标题, session_id: {session_id}")
        
        # 构建提示词
        prompt = f"""请为以下对话生成一个简洁的标题（不超过20个字符）：

用户消息：{user_message[:200]}...

要求：
1. 标题要简洁明了
2. 能体现对话主题
3. 不超过20个字符
4. 使用中文
5. 不要包含特殊字符

直接返回标题，不要其他内容。"""

        # 调用AI生成标题
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的标题生成助手，擅长为对话生成简洁明了的标题。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        title = response.choices[0].message.content.strip()
        
        api_logger.info(f"[标题生成响应] 生成标题长度: {len(title)}")
        
        # 确保标题不超过20个字符
        if len(title) > 20:
            title = title[:17] + "..."
        
        api_logger.info(f"AI生成标题成功: session_id={session_id}, title={title}")
        return title
        
    except Exception as e:
        api_logger.error(f"调用AI生成标题失败: session_id={session_id}, error={str(e)}", exc_info=True)
        # 如果AI生成失败，返回基于用户消息的简单标题
        if len(user_message) > 20:
            fallback_title = user_message[:17] + "..."
        else:
            fallback_title = user_message or "新对话"
        
        api_logger.info(f"使用备用标题: session_id={session_id}, title={fallback_title}")
        return fallback_title

def generate_simple_title(user_message: str) -> str:
    """
    生成简单标题（不使用AI）
    
    Args:
        user_message: 用户消息内容
        
    Returns:
        生成的标题
    """
    if not user_message or not user_message.strip():
        return "新对话"
    
    # 清理消息内容
    cleaned_message = user_message.strip()
    
    # 如果消息过长，截取前面部分
    if len(cleaned_message) > 20:
        title = cleaned_message[:17] + "..."
    else:
        title = cleaned_message
    
    # 替换换行符为空格
    title = title.replace('\n', ' ').replace('\r', ' ')
    
    # 移除多余的空格
    title = ' '.join(title.split())
    
    return title 