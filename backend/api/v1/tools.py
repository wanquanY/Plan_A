from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.services.tools import tools_service
from backend.api.deps import get_current_active_user
from backend.models.user import User
from backend.core.response import SuccessResponse
from backend.utils.logging import api_logger

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