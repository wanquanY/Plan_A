#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试MCP服务器toggle问题
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from backend.database.session import get_async_session
from backend.utils.id_converter import IDConverter
from backend.models.mcp_server import MCPServer
from backend.services.mcp_service import mcp_service
from sqlalchemy import select

async def debug_toggle_issue():
    """调试toggle问题"""
    
    # 测试的public_id
    test_public_id = "mcp-78TdVWDmZKQU"
    test_user_id = 1
    
    print(f"=== 调试MCP服务器toggle问题 ===")
    print(f"测试public_id: {test_public_id}")
    print(f"测试user_id: {test_user_id}")
    
    async for db in get_async_session():
        try:
            # 1. 检查ID转换
            print(f"\n1. 检查ID转换:")
            db_id = await IDConverter.get_mcp_server_db_id(db, test_public_id)
            print(f"   public_id -> db_id: {test_public_id} -> {db_id}")
            
            if not db_id:
                print("   ❌ ID转换失败，检查数据库中是否存在该public_id")
                
                # 查询所有MCP服务器
                stmt = select(MCPServer).where(MCPServer.user_id == test_user_id)
                result = await db.execute(stmt)
                servers = result.scalars().all()
                
                print(f"\n   用户 {test_user_id} 的所有MCP服务器:")
                for server in servers:
                    print(f"   - ID: {server.id}, public_id: {server.public_id}, name: {server.name}")
                
                return
            
            # 2. 检查服务器是否存在
            print(f"\n2. 检查服务器是否存在:")
            stmt = select(MCPServer).where(
                MCPServer.id == db_id,
                MCPServer.user_id == test_user_id
            )
            result = await db.execute(stmt)
            server = result.scalar_one_or_none()
            
            if not server:
                print(f"   ❌ 服务器不存在: db_id={db_id}, user_id={test_user_id}")
                
                # 检查是否存在但用户不匹配
                stmt2 = select(MCPServer).where(MCPServer.id == db_id)
                result2 = await db.execute(stmt2)
                server2 = result2.scalar_one_or_none()
                
                if server2:
                    print(f"   服务器存在但用户不匹配: server.user_id={server2.user_id}, 期望user_id={test_user_id}")
                else:
                    print(f"   服务器完全不存在: db_id={db_id}")
                return
            
            print(f"   ✅ 服务器存在:")
            print(f"   - ID: {server.id}")
            print(f"   - public_id: {server.public_id}")
            print(f"   - name: {server.name}")
            print(f"   - user_id: {server.user_id}")
            print(f"   - enabled: {server.enabled}")
            
            # 3. 测试toggle操作
            print(f"\n3. 测试toggle操作:")
            try:
                result = await mcp_service.toggle_user_server(
                    user_id=test_user_id,
                    server_id=db_id
                )
                print(f"   ✅ toggle成功: {result}")
            except Exception as e:
                print(f"   ❌ toggle失败: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"调试过程中出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()
            break

if __name__ == "__main__":
    asyncio.run(debug_toggle_issue()) 