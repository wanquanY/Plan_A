from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.services.tools import tools_service
from backend.api.deps import get_current_active_user
from backend.models.user import User
from backend.core.response import SuccessResponse
from backend.utils.logging import api_logger
from backend.config.tools_manager import tools_manager

router = APIRouter()


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    max_results: Optional[int] = Field(10, description="最大结果数")
    search_depth: Optional[str] = Field("basic", description="搜索深度")
    include_images: Optional[bool] = Field(False, description="是否包含图片")
    include_answer: Optional[bool] = Field(False, description="是否包含AI回答")
    include_raw_content: Optional[bool] = Field(False, description="是否包含原始内容")
    api_key: Optional[str] = Field(None, description="Tavily API密钥")


class ExtractRequest(BaseModel):
    """网页内容提取请求模型"""
    urls: List[str] = Field(..., description="要提取内容的URL列表")
    include_images: Optional[bool] = Field(False, description="是否包含图片")
    api_key: Optional[str] = Field(None, description="Tavily API密钥")


@router.post("/search", response_model=Dict[str, Any])
async def search(
    request: Request,
    search_request: SearchRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    执行Tavily搜索
    """
    api_logger.info(f"收到搜索请求: {search_request.query}, 用户: {current_user.username}")
    
    # 提取API密钥
    api_key = search_request.api_key
    
    # 准备搜索参数
    search_params = {
        "query": search_request.query,
        "max_results": search_request.max_results,
        "search_depth": search_request.search_depth,
        "include_images": search_request.include_images,
        "include_answer": search_request.include_answer,
        "include_raw_content": search_request.include_raw_content
    }
    
    # 准备工具配置
    tool_config = {"api_key": api_key} if api_key else None
    
    # 执行搜索
    result = tools_service.execute_tool(
        tool_name="tavily", 
        action="search", 
        params=search_params,
        config=tool_config
    )
    
    # 检查是否有错误
    if "error" in result:
        api_logger.error(f"搜索失败: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {result['error']}"
        )
    
    return SuccessResponse(
        data=result,
        msg="搜索成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/extract", response_model=Dict[str, Any])
async def extract(
    request: Request,
    extract_request: ExtractRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    执行Tavily网页内容提取
    """
    api_logger.info(f"收到网页内容提取请求: {extract_request.urls}, 用户: {current_user.username}")
    
    # 提取API密钥
    api_key = extract_request.api_key
    
    # 准备提取参数
    extract_params = {
        "urls": extract_request.urls,
        "include_images": extract_request.include_images
    }
    
    # 准备工具配置
    tool_config = {"api_key": api_key} if api_key else None
    
    # 执行内容提取
    result = tools_service.execute_tool(
        tool_name="tavily", 
        action="extract", 
        params=extract_params,
        config=tool_config
    )
    
    # 检查是否有错误
    if "error" in result:
        api_logger.error(f"内容提取失败: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内容提取失败: {result['error']}"
        )
    
    return SuccessResponse(
        data=result,
        msg="内容提取成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/tools", response_model=List[Dict[str, Any]])
async def get_tools_list(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取所有可用工具的详细信息
    """
    try:
        tools_details = tools_manager.get_tools_with_details()
        api_logger.info(f"用户 {current_user.id} 获取工具列表，共 {len(tools_details)} 个工具")
        return tools_details
    except Exception as e:
        api_logger.error(f"获取工具列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取工具列表失败"
        )

@router.get("/tools/grouped", response_model=Dict[str, List[Dict[str, Any]]])
async def get_tools_grouped_by_provider(
    current_user: User = Depends(get_current_active_user)
):
    """
    按提供商分组获取工具详情
    """
    try:
        grouped_tools = tools_manager.get_tools_grouped_by_provider()
        api_logger.info(f"用户 {current_user.id} 获取分组工具列表")
        return grouped_tools
    except Exception as e:
        api_logger.error(f"获取分组工具列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取分组工具列表失败"
        )

@router.get("/tools/providers", response_model=Dict[str, Dict[str, Any]])
async def get_tool_providers(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取所有工具提供商信息
    """
    try:
        providers = tools_manager.get_tool_providers()
        api_logger.info(f"用户 {current_user.id} 获取工具提供商信息")
        return providers
    except Exception as e:
        api_logger.error(f"获取工具提供商信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取工具提供商信息失败"
        )

@router.post("/tools/validate", response_model=Dict[str, Any])
async def validate_tools_config(
    tools_config: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    验证工具配置
    """
    try:
        validation_result = tools_manager.validate_agent_tools_config(tools_config)
        api_logger.info(f"用户 {current_user.id} 验证工具配置，类型: {validation_result['config_type']}")
        return validation_result
    except Exception as e:
        api_logger.error(f"验证工具配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证工具配置失败"
        )

@router.post("/tools/convert", response_model=Dict[str, Any])
async def convert_provider_config_to_tool_config(
    provider_config: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    将提供商级别配置转换为工具级别配置
    """
    try:
        tool_config = tools_manager.convert_provider_config_to_tool_config(provider_config)
        api_logger.info(f"用户 {current_user.id} 转换配置格式")
        return {
            "success": True,
            "tool_config": tool_config,
            "original_config": provider_config
        }
    except Exception as e:
        api_logger.error(f"转换配置格式失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="转换配置格式失败"
        )

@router.get("/tools/default-config", response_model=Dict[str, Any])
async def get_default_tool_config(
    enabled_tools: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取默认工具配置
    
    Args:
        enabled_tools: 逗号分隔的要启用的工具名称列表
    """
    try:
        enabled_list = []
        if enabled_tools:
            enabled_list = [tool.strip() for tool in enabled_tools.split(",")]
        
        default_config = tools_manager.create_default_tool_config(enabled_list)
        api_logger.info(f"用户 {current_user.id} 获取默认工具配置")
        return default_config
    except Exception as e:
        api_logger.error(f"获取默认工具配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取默认工具配置失败"
        )

@router.get("/tools/recommendations", response_model=List[str])
async def get_tool_recommendations(
    use_case: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    根据使用场景获取推荐工具
    
    Args:
        use_case: 使用场景 (search, news, extract, scrape, web, realtime, content)
    """
    try:
        recommendations = tools_manager.get_recommended_tools(use_case)
        api_logger.info(f"用户 {current_user.id} 获取 {use_case} 场景的推荐工具")
        return recommendations
    except Exception as e:
        api_logger.error(f"获取推荐工具失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取推荐工具失败"
        )

@router.get("/tools/search", response_model=List[Dict[str, Any]])
async def search_tools(
    query: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    搜索工具
    
    Args:
        query: 搜索关键词
    """
    try:
        search_results = tools_manager.search_tools(query)
        api_logger.info(f"用户 {current_user.id} 搜索工具: {query}")
        return search_results
    except Exception as e:
        api_logger.error(f"搜索工具失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索工具失败"
    ) 