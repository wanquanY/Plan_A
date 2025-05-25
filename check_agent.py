import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.models.agent import Agent
from sqlalchemy import select
import json

async def check_agent_tools():
    engine = create_async_engine(settings.DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 查询ID为1的Agent（小助理）
        stmt = select(Agent).where(Agent.id == 1)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if agent:
            print(f'Agent名称: {agent.name}')
            print(f'系统提示词: {agent.system_prompt[:100]}...')
            print(f'工具配置类型: {type(agent.tools_enabled)}')
            if agent.tools_enabled:
                print(f'工具配置内容:')
                print(json.dumps(agent.tools_enabled, indent=2, ensure_ascii=False))
            else:
                print('工具配置为空')
        else:
            print('未找到ID为1的Agent')

if __name__ == "__main__":
    asyncio.run(check_agent_tools()) 