"""
MCP API路由

提供MCP相关的API端点，主要用于管理用户的MCP服务器配置。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.mcp_service import mcp_service
from backend.core.response import SuccessResponse, ErrorResponse
from backend.utils.logging import api_logger
from backend.api.deps import get_current_user, get_current_active_user, get_db
from backend.models.user import User
from backend.utils.id_converter import IDConverter


router = APIRouter()


# 导入schemas
from backend.schemas.mcp_server import (
    MCPServerCreate, MCPServerUpdate, MCPServerResponse, 
    MCPServerListResponse, MCPServerConfigImport, MCPServerConfigExport,
    MCPServerImportResult, MCPServerStatistics, MCPServerPublicResponse,
    MCPServerDeleteResponse, MCPServerToggleResponse, MCPServerCreateResponse
)


# ==================== 系统状态接口（需要认证） ====================

@router.get("/status")
async def get_mcp_status(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """获取MCP服务整体状态"""
    try:
        api_logger.info(f"用户 {current_user.username} 获取MCP服务状态, 请求ID: {getattr(request.state, 'request_id', '')}")
        status = mcp_service.get_status()
        return SuccessResponse(
            data=status,
            msg="获取MCP服务状态成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 获取MCP服务状态失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"获取MCP服务状态失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/health")
async def health_check(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """MCP服务健康检查"""
    try:
        api_logger.info(f"用户 {current_user.username} 执行MCP健康检查, 请求ID: {getattr(request.state, 'request_id', '')}")
        health = await mcp_service.health_check()
        return SuccessResponse(
            data=health,
            msg="健康检查完成",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} MCP健康检查失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"健康检查失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


# ==================== 用户服务器配置管理接口 ====================

@router.get("/servers")
async def get_user_servers(
    request: Request,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的MCP服务器配置列表"""
    try:
        api_logger.info(f"用户 {current_user.username} 获取MCP服务器列表, 请求ID: {getattr(request.state, 'request_id', '')}")
        servers = await mcp_service.get_user_servers(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        # 使用schema转换为公开响应格式
        from backend.schemas.mcp_server import MCPServerPublicResponse
        from backend.utils.serialization import serialize_pydantic_models
        public_servers = [MCPServerPublicResponse.from_orm_model(server) for server in servers]
        
        return SuccessResponse(
            data={
                "servers": serialize_pydantic_models(public_servers),
                "total": len(public_servers),
                "skip": skip,
                "limit": limit
            },
            msg="获取服务器列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 获取MCP服务器列表失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"获取服务器列表失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/servers")
async def create_user_server(
    request: Request,
    server_data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 创建MCP服务器配置: {server_data.name}, 请求ID: {getattr(request.state, 'request_id', '')}")
        server = await mcp_service.create_user_server(
            user_id=current_user.id,
            server_data=server_data.dict()
        )
        
        # 使用schema构建响应
        from backend.schemas.mcp_server import MCPServerCreateResponse
        from backend.utils.serialization import serialize_pydantic_model
        response_data = MCPServerCreateResponse(
            id=server.public_id,
            name=server.name,
            message="服务器配置创建成功"
        )
        
        return SuccessResponse(
            data=serialize_pydantic_model(response_data),
            msg="服务器配置创建成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 创建MCP服务器配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"创建服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/servers/{server_id}")
async def get_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定的MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 获取MCP服务器配置: {server_id}, 请求ID: {getattr(request.state, 'request_id', '')}")
        
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        servers = await mcp_service.get_user_servers(
            user_id=current_user.id,
            skip=0,
            limit=1000
        )
        
        # 查找指定public_id的服务器
        server = None
        for s in servers:
            if s.public_id == server_id:
                server = s
                break
        
        if not server:
            return ErrorResponse(
                msg=f"服务器不存在: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 使用schema转换为公开响应格式
        from backend.schemas.mcp_server import MCPServerPublicResponse
        from backend.utils.serialization import serialize_pydantic_model
        public_server = MCPServerPublicResponse.from_orm_model(server)
        
        return SuccessResponse(
            data=serialize_pydantic_model(public_server),
            msg="获取服务器配置成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 获取MCP服务器配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"获取服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.put("/servers/{server_id}")
async def update_user_server(
    request: Request,
    server_id: str,
    update_data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 更新MCP服务器配置: {server_id}, 请求ID: {getattr(request.state, 'request_id', '')}")
        
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 只更新非空字段
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        server = await mcp_service.update_user_server(
            user_id=current_user.id,
            server_id=db_id,  # 使用数据库ID
            update_data=update_dict
        )
        
        # 使用schema转换为公开响应格式
        from backend.schemas.mcp_server import MCPServerPublicResponse
        from backend.utils.serialization import serialize_pydantic_model
        public_server = MCPServerPublicResponse.from_orm_model(server)
        
        return SuccessResponse(
            data=serialize_pydantic_model(public_server),
            msg="服务器配置更新成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 更新MCP服务器配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"更新服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.delete("/servers/{server_id}")
async def delete_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 删除MCP服务器配置: {server_id}, 请求ID: {getattr(request.state, 'request_id', '')}")
        
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        await mcp_service.delete_user_server(
            user_id=current_user.id,
            server_id=db_id  # 使用数据库ID
        )
        
        # 使用schema构建响应
        from backend.schemas.mcp_server import MCPServerDeleteResponse
        from backend.utils.serialization import serialize_pydantic_model
        response_data = MCPServerDeleteResponse(
            id=server_id,
            message="服务器配置删除成功"
        )
        
        return SuccessResponse(
            data=serialize_pydantic_model(response_data),
            msg="服务器配置删除成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 删除MCP服务器配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"删除服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/servers/{server_id}/toggle")
async def toggle_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """切换MCP服务器启用状态"""
    try:
        api_logger.info(f"用户 {current_user.username} (ID: {current_user.id}) 切换MCP服务器状态: {server_id}, 请求ID: {getattr(request.state, 'request_id', '')}")
        
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            api_logger.error(f"无效的服务器ID: {server_id}")
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        api_logger.info(f"转换后的数据库ID: {db_id}, 当前用户ID: {current_user.id}")
        
        result = await mcp_service.toggle_user_server(
            user_id=current_user.id,
            server_id=db_id  # 使用数据库ID
        )
        
        # 确保result不为None
        if result is None:
            api_logger.error(f"toggle_user_server返回None: user_id={current_user.id}, server_id={db_id}")
            return ErrorResponse(
                msg=f"切换服务器状态失败: 服务器不存在",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 使用schema构建响应
        from backend.utils.serialization import serialize_pydantic_model
        response_data = MCPServerToggleResponse(
            id=server_id,
            action=result["action"],
            message=result["message"]
        )
        
        return SuccessResponse(
            data=serialize_pydantic_model(response_data),
            msg=result["message"],
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 切换MCP服务器状态失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"切换服务器状态失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/servers/{server_id}/status")
async def get_user_server_status(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取用户服务器的运行时状态"""
    try:
        api_logger.info(f"用户 {current_user.username} 获取MCP服务器状态: {server_id}, 请求ID: {getattr(request.state, 'request_id', '')}")
        
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 获取运行时状态（mcp_service会验证用户权限）
        if mcp_service.is_enabled():
            try:
                runtime_status = await mcp_service.get_server_status(server_id, current_user.id)
                return SuccessResponse(
                    data=runtime_status,
                    msg="获取服务器状态成功",
                    request_id=getattr(request.state, "request_id", None)
                )
            except Exception as e:
                return SuccessResponse(
                    data={
                        "connected": False,
                        "initialized": False,
                        "error": str(e),
                        "tools": [],
                        "resources": [],
                        "prompts": []
                    },
                    msg="服务器未连接",
                    request_id=getattr(request.state, "request_id", None)
                )
        else:
            return SuccessResponse(
                data={
                    "connected": False,
                    "initialized": False,
                    "error": "MCP服务未启用",
                    "tools": [],
                    "resources": [],
                    "prompts": []
                },
                msg="MCP服务未启用",
                request_id=getattr(request.state, "request_id", None)
            )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 获取MCP服务器状态失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"获取服务器状态失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/servers/{server_id}/reconnect")
async def reconnect_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """重新连接用户的MCP服务器"""
    try:
        api_logger.info(f"用户 {current_user.username} 重连MCP服务器: {server_id}, 请求ID: {getattr(request.state, 'request_id', '')}")
        
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        if not mcp_service.is_enabled():
            return ErrorResponse(
                msg="MCP服务未启用",
                request_id=getattr(request.state, "request_id", None)
            )
        
        await mcp_service.reconnect_server(server_id, current_user.id)
        
        return SuccessResponse(
            data={"id": server_id},
            msg="服务器重连成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 重连MCP服务器失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"重连服务器失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


# ==================== 批量操作接口 ====================

@router.post("/servers/import")
async def import_user_servers(
    request: Request,
    import_data: MCPServerConfigImport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """批量导入MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 批量导入MCP服务器配置, 请求ID: {getattr(request.state, 'request_id', '')}")
        result = await mcp_service.import_user_servers(
            user_id=current_user.id,
            servers_config=import_data.servers,
            overwrite=import_data.overwrite
        )
        
        return SuccessResponse(
            data=result,
            msg=f"导入完成: 创建{len(result['created'])}个, 更新{len(result['updated'])}个, 跳过{len(result['skipped'])}个",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 批量导入MCP服务器配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"导入服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/servers/export")
async def export_user_servers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """导出用户的所有MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 导出MCP服务器配置, 请求ID: {getattr(request.state, 'request_id', '')}")
        from datetime import datetime
        
        servers_config = await mcp_service.export_user_servers(
            user_id=current_user.id
        )
        
        export_data = {
            "servers": servers_config,
            "export_time": datetime.now().isoformat(),
            "user_id": current_user.public_id,  # 使用public_id而不是数据库ID
            "version": "1.0"
        }
        
        return SuccessResponse(
            data=export_data,
            msg="导出服务器配置成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 导出MCP服务器配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"导出服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/servers/statistics")
async def get_user_servers_statistics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取用户的MCP服务器统计信息"""
    try:
        api_logger.info(f"用户 {current_user.username} 获取MCP服务器统计信息, 请求ID: {getattr(request.state, 'request_id', '')}")
        stats = await mcp_service.get_user_servers_statistics(
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=stats,
            msg="获取统计信息成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 获取MCP服务器统计信息失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"获取统计信息失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


# ==================== 公开服务器接口（需要认证） ====================

@router.get("/public-servers")
async def get_public_servers(
    request: Request,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    current_user: User = Depends(get_current_active_user)
):
    """获取公开的MCP服务器配置"""
    try:
        api_logger.info(f"用户 {current_user.username} 获取公开MCP服务器列表, 请求ID: {getattr(request.state, 'request_id', '')}")
        servers = await mcp_service.get_public_servers(
            skip=skip,
            limit=limit
        )
        
        return SuccessResponse(
            data={
                "servers": servers,
                "total": len(servers),
                "skip": skip,
                "limit": limit
            },
            msg="获取公开服务器列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"用户 {current_user.username} 获取公开MCP服务器列表失败: {str(e)}", exc_info=True)
        return ErrorResponse(
            msg=f"获取公开服务器列表失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        ) 