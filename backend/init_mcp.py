#!/usr/bin/env python3
"""
初始化MCP服务器配置脚本

将环境变量中的MCP服务器配置导入到数据库中。
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import get_async_session
from backend.crud.mcp_server import mcp_server
from backend.core.config import settings
from backend.utils.logging import app_logger


async def init_default_servers():
    """初始化默认的MCP服务器配置"""
    
    if not settings.MCP_SERVERS:
        app_logger.info("没有找到MCP服务器配置，跳过初始化")
        return
    
    async for db in get_async_session():
        imported_count = 0
        skipped_count = 0
        
        for server_name, server_config in settings.MCP_SERVERS.items():
            try:
                # 检查是否已存在
                existing = await mcp_server.get_by_name(db, name=server_name)
                
                if existing:
                    app_logger.info(f"服务器配置已存在，跳过: {server_name}")
                    skipped_count += 1
                    continue
                
                # 创建新的服务器配置
                new_server = await mcp_server.create_from_config(
                    db, 
                    name=server_name, 
                    config=server_config
                )
                
                app_logger.info(f"成功导入服务器配置: {server_name}")
                imported_count += 1
                
            except Exception as e:
                app_logger.error(f"导入服务器配置失败 {server_name}: {e}")
        
        app_logger.info(f"MCP服务器配置初始化完成: 导入 {imported_count} 个，跳过 {skipped_count} 个")
        break  # 退出async for循环


async def main():
    """主函数"""
    try:
        app_logger.info("开始初始化MCP服务器配置...")
        await init_default_servers()
        app_logger.info("MCP服务器配置初始化完成")
    except Exception as e:
        app_logger.error(f"初始化MCP服务器配置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 