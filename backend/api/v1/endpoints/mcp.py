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
from backend.api.deps import get_current_user, get_current_active_user, get_async_session
from backend.models.user import User
from backend.utils.id_converter import IDConverter


router = APIRouter()


async def get_user_server_by_public_id(db: AsyncSession, user_id: int, server_public_id: str) -> Optional[Dict[str, Any]]:
    """根据server_public_id获取用户的服务器配置"""
    try:
        # 转换public_id为数据库ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_public_id)
        if not db_id:
            return None
    except:
        return None
    
    servers = await mcp_service.get_user_servers(
        user_id=user_id,
        skip=0,
        limit=1000
    )
    
    return next((s for s in servers if s["id"] == server_public_id), None)


# 导入schemas
from backend.schemas.mcp_server import (
    MCPServerCreate, MCPServerUpdate, MCPServerResponse, 
    MCPServerListResponse, MCPServerConfigImport, MCPServerConfigExport,
    MCPServerImportResult, MCPServerSearchParams, MCPServerStatistics,
    MCPServerToggleResponse
)


# ==================== 系统状态接口（无需认证） ====================

@router.get("/status")
async def get_mcp_status():
    """获取MCP服务整体状态（无需认证）"""
    try:
        status = mcp_service.get_status()
        return SuccessResponse(
            data=status,
            msg="获取MCP服务状态成功"
        )
    except Exception as e:
        return ErrorResponse(msg=f"获取MCP服务状态失败: {str(e)}")


@router.get("/health")
async def health_check():
    """MCP服务健康检查（无需认证）"""
    try:
        health = await mcp_service.health_check()
        return SuccessResponse(
            data=health,
            msg="健康检查完成"
        )
    except Exception as e:
        return ErrorResponse(msg=f"健康检查失败: {str(e)}")


# ==================== 用户服务器配置管理接口 ====================

@router.get("/servers")
async def get_user_servers(
    request: Request,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的MCP服务器配置列表"""
    try:
        servers = await mcp_service.get_user_servers(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        # 标准化服务器数据，只返回public_id
        standardized_servers = []
        for server in servers:
            # 如果服务器数据包含数据库ID，移除它并只保留public_id作为id
            server_data = server.copy()
            if "public_id" in server_data:
                server_data["id"] = server_data["public_id"]
                del server_data["public_id"]
            standardized_servers.append(server_data)
        
        return SuccessResponse(
            data={
                "servers": standardized_servers,
                "total": len(standardized_servers),
                "skip": skip,
                "limit": limit
            },
            msg="获取服务器列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        return ErrorResponse(
            msg=f"获取服务器列表失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/servers")
async def create_user_server(
    request: Request,
    server_data: MCPServerCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """创建MCP服务器配置"""
    try:
        result = await mcp_service.create_user_server(
            user_id=current_user.id,
            server_data=server_data.dict()
        )
        
        # 标准化返回数据，只返回public_id作为id
        standardized_result = {
            "id": result.get("public_id", result.get("id")),
            "name": result.get("name"),
            "message": result.get("message", "服务器配置创建成功")
        }
        
        return SuccessResponse(
            data=standardized_result,
            msg="服务器配置创建成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        return ErrorResponse(
            msg=f"创建服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/servers/{server_id}")
async def get_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定的MCP服务器配置"""
    try:
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
            # 标准化数据，使用public_id作为id进行比较
            if s.get("public_id") == server_id:
                server = s.copy()
                server["id"] = server["public_id"]
                if "public_id" in server:
                    del server["public_id"]
                break
        
        if not server:
            return ErrorResponse(
                msg=f"服务器不存在: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        return SuccessResponse(
            data=server,
            msg="获取服务器配置成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        return ErrorResponse(
            msg=f"获取服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.put("/servers/{server_id}")
async def update_user_server(
    request: Request,
    server_id: str,
    update_data: MCPServerUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """更新MCP服务器配置"""
    try:
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 只更新非空字段
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        result = await mcp_service.update_user_server(
            user_id=current_user.id,
            server_id=db_id,  # 使用数据库ID
            update_data=update_dict
        )
        
        # 标准化返回数据
        if "public_id" in result:
            result["id"] = result["public_id"]
            del result["public_id"]
        
        return SuccessResponse(
            data=result,
            msg="服务器配置更新成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        return ErrorResponse(
            msg=f"更新服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.delete("/servers/{server_id}")
async def delete_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """删除MCP服务器配置"""
    try:
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        result = await mcp_service.delete_user_server(
            user_id=current_user.id,
            server_id=db_id  # 使用数据库ID
        )
        
        return SuccessResponse(
            data={"id": server_id},
            msg="服务器配置删除成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        return ErrorResponse(
            msg=f"删除服务器配置失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/servers/{server_id}/toggle")
async def toggle_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """切换MCP服务器启用状态"""
    try:
        # 验证并转换public_id为内部ID
        db_id = await IDConverter.get_mcp_server_db_id(db, server_id)
        if not db_id:
            return ErrorResponse(
                msg=f"无效的服务器ID: {server_id}",
                request_id=getattr(request.state, "request_id", None)
            )
        
        result = await mcp_service.toggle_user_server(
            user_id=current_user.id,
            server_id=db_id  # 使用数据库ID
        )
        
        return SuccessResponse(
            data={"id": server_id, "action": result.get("action", "unknown")},
            msg=f"服务器已{result.get('action', 'unknown')}",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        return ErrorResponse(
            msg=f"切换服务器状态失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/servers/{server_id}/status")
async def get_user_server_status(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """获取用户服务器的运行时状态"""
    try:
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
        return ErrorResponse(
            msg=f"获取服务器状态失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/servers/{server_id}/reconnect")
async def reconnect_user_server(
    request: Request,
    server_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """重新连接用户的MCP服务器"""
    try:
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
        return ErrorResponse(
            msg=f"重连服务器失败: {str(e)}",
            request_id=getattr(request.state, "request_id", None)
        )


# ==================== 批量操作接口 ====================

@router.post("/servers/import")
async def import_user_servers(
    import_data: MCPServerConfigImport,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """批量导入MCP服务器配置"""
    try:
        result = await mcp_service.import_user_servers(
            user_id=current_user.id,
            servers_config=import_data.servers,
            overwrite=import_data.overwrite
        )
        
        return SuccessResponse(
            data=result,
            msg=f"导入完成: 创建{len(result['created'])}个, 更新{len(result['updated'])}个, 跳过{len(result['skipped'])}个"
        )
    except Exception as e:
        return ErrorResponse(msg=f"导入服务器配置失败: {str(e)}")


@router.get("/servers/export")
async def export_user_servers(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """导出用户的所有MCP服务器配置"""
    try:
        from datetime import datetime
        
        servers_config = await mcp_service.export_user_servers(
            user_id=current_user.id
        )
        
        export_data = {
            "servers": servers_config,
            "export_time": datetime.now().isoformat(),
            "user_id": current_user.id,
            "version": "1.0"
        }
        
        return SuccessResponse(
            data=export_data,
            msg="导出服务器配置成功"
        )
    except Exception as e:
        return ErrorResponse(msg=f"导出服务器配置失败: {str(e)}")


@router.get("/servers/statistics")
async def get_user_servers_statistics(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """获取用户的MCP服务器统计信息"""
    try:
        stats = await mcp_service.get_user_servers_statistics(
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=stats,
            msg="获取统计信息成功"
        )
    except Exception as e:
        return ErrorResponse(msg=f"获取统计信息失败: {str(e)}")


# ==================== 公开服务器接口 ====================

@router.get("/public-servers")
async def get_public_servers(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量")
):
    """获取公开的MCP服务器配置（无需认证）"""
    try:
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
            msg="获取公开服务器列表成功"
        )
    except Exception as e:
        return ErrorResponse(msg=f"获取公开服务器列表失败: {str(e)}")


# ==================== 工具调用接口（用于聊天集成） ====================

@router.get("/available-tools")
async def get_available_tools():
    """获取所有可用的MCP工具（用于聊天集成，无需认证）"""
    try:
        tools = await mcp_service.get_available_tools_for_chat()
        return SuccessResponse(
            data={"tools": tools},
            msg="获取可用工具成功"
        )
    except Exception as e:
        return ErrorResponse(msg=f"获取可用工具失败: {str(e)}")


@router.post("/execute-tool")
async def execute_mcp_tool(
    tool_name: str = Query(..., description="工具名称"),
    arguments: Dict[str, Any] = {}
):
    """执行MCP工具（用于聊天集成，无需认证）"""
    try:
        result = await mcp_service.execute_mcp_tool_for_chat(tool_name, arguments)
        return SuccessResponse(
            data=result,
            msg="工具执行完成"
        )
    except Exception as e:
        return ErrorResponse(msg=f"工具执行失败: {str(e)}") 