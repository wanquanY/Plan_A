#!/usr/bin/env python3
"""
测试Agent工具格式的脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.agent_service import agent_service
from backend.services.mcp_service import mcp_service
from backend.crud.agent import agent as agent_crud
from backend.core.database import get_db
from backend.utils.logging import app_logger as logger

async def test_agent_tools():
    """测试Agent工具获取"""
    try:
        # 初始化MCP服务
        await mcp_service.initialize(user_id=8)
        
        # 获取数据库会话
        async for db in get_db():
            # 获取用户的Agent
            agent = await agent_crud.get_user_agent(db, 8)
            if not agent:
                print("❌ 用户没有Agent")
                return
            
            print(f"✅ 找到Agent: {agent.public_id}")
            
            # 获取Agent工具
            tools = await agent_service.get_agent_tools_for_chat(agent, 8)
            
            print(f"📊 总工具数量: {len(tools)}")
            
            # 分析工具类型
            mcp_tools = [t for t in tools if t.get("type") == "function" and "maps_" in t.get("function", {}).get("name", "")]
            builtin_tools = [t for t in tools if t.get("type") == "function" and "maps_" not in t.get("function", {}).get("name", "")]
            
            print(f"🔧 内置工具: {len(builtin_tools)}")
            print(f"🌐 MCP工具: {len(mcp_tools)}")
            
            # 显示前几个工具的格式
            print("\n📋 工具格式示例:")
            for i, tool in enumerate(tools[:3]):
                print(f"  {i+1}. {tool.get('function', {}).get('name', 'Unknown')}")
                print(f"     类型: {tool.get('type')}")
                print(f"     描述: {tool.get('function', {}).get('description', '')[:50]}...")
                if tool.get('function', {}).get('parameters'):
                    param_count = len(tool.get('function', {}).get('parameters', {}).get('properties', {}))
                    print(f"     参数数量: {param_count}")
                print()
            
            # 检查高德地图工具
            maps_tools = [t for t in tools if "maps_" in t.get("function", {}).get("name", "")]
            if maps_tools:
                print(f"🗺️  高德地图工具: {len(maps_tools)} 个")
                for tool in maps_tools[:3]:
                    name = tool.get("function", {}).get("name", "")
                    desc = tool.get("function", {}).get("description", "")
                    print(f"   - {name}: {desc[:50]}...")
            else:
                print("❌ 没有找到高德地图工具")
            
            break
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_tools()) 