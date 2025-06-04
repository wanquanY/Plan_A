from openai import AsyncOpenAI
from typing import Optional
from backend.core.config import settings
from backend.utils.logging import api_logger
import json

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

async def generate_title_with_ai(session_id: int, user_message: str) -> str:
    """
    使用AI为聊天会话生成标题
    
    Args:
        session_id: 会话ID
        user_message: 用户消息内容
    
    Returns:
        str: 生成的标题
        
    Raises:
        Exception: 当AI请求失败时抛出异常
    """
    try:
        api_logger.info(f"开始调用AI生成会话标题, 会话ID: {session_id}")
        
        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专门提取内容主题的助手。请根据用户的输入内容，生成一个简短、精确的标题，不超过15个字。不要使用引号，直接返回标题文本。"},
            {"role": "user", "content": user_message}
        ]
        
        # 调用AI API
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=30,  # 标题很短，不需要太多token
            temperature=0.3,  # 低温度，保持一致性
            stream=False
        )
        
        # 获取生成的标题
        title = response.choices[0].message.content.strip()
        
        api_logger.info(f"[标题生成响应] 生成标题长度: {len(title)}")
        
        # 如果标题太长，截断
        if len(title) > 20:
            title = title[:20] + "..."
            
        api_logger.info(f"AI生成标题成功: {title}, 会话ID: {session_id}")
        return title
        
    except Exception as e:
        api_logger.error(f"调用AI生成标题失败: {str(e)}", exc_info=True)
        # 失败时返回默认标题，使用原来的逻辑截取前20个字符
        default_title = user_message[:20] + ("..." if len(user_message) > 20 else "")
        return default_title 