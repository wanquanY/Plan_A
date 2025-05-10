from typing import Dict, List, Any, Optional
import os
import json
import requests
from backend.utils.logging import api_logger

class TavilyTool:
    """Tavily搜索和网页解析工具"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化Tavily工具"""
        self.api_key = api_key
        if not self.api_key:
            # 尝试从环境变量中获取API密钥
            self.api_key = os.environ.get("TAVILY_API_KEY")
        
        self.base_url = "https://api.tavily.com/v1"
        self.search_endpoint = f"{self.base_url}/search"
        self.extract_endpoint = f"{self.base_url}/extract"
        
        api_logger.info(f"Tavily工具初始化，API密钥: {self.api_key[:5]}*** (如果有)")
    
    def search(
        self, 
        query: str, 
        max_results: int = 10, 
        search_depth: str = "basic",
        include_images: bool = False,
        include_answer: bool = False,
        include_raw_content: bool = False
    ) -> Dict[str, Any]:
        """执行Tavily搜索查询"""
        if not self.api_key:
            api_logger.error("未提供Tavily API密钥，无法执行搜索")
            return {"error": "未提供API密钥"}
        
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            payload = {
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_images": include_images,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content
            }
            
            api_logger.info(f"执行Tavily搜索: {query}, 最大结果数: {max_results}")
            response = requests.post(
                self.search_endpoint,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                api_logger.info(f"Tavily搜索成功，获取到 {len(result.get('results', []))} 条结果")
                return result
            else:
                api_logger.error(f"Tavily搜索API错误: {response.status_code}, {response.text}")
                return {"error": f"API错误: {response.status_code}", "details": response.text}
                
        except Exception as e:
            api_logger.error(f"Tavily搜索异常: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def extract(
        self,
        urls: List[str],
        include_images: bool = False
    ) -> Dict[str, Any]:
        """执行Tavily网页内容提取"""
        if not self.api_key:
            api_logger.error("未提供Tavily API密钥，无法执行内容提取")
            return {"error": "未提供API密钥"}
        
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            payload = {
                "urls": urls,
                "include_images": include_images
            }
            
            api_logger.info(f"执行Tavily内容提取: {urls}")
            response = requests.post(
                self.extract_endpoint,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                api_logger.info(f"Tavily内容提取成功，处理了 {len(result.get('results', []))} 个URL")
                return result
            else:
                api_logger.error(f"Tavily内容提取API错误: {response.status_code}, {response.text}")
                return {"error": f"API错误: {response.status_code}", "details": response.text}
                
        except Exception as e:
            api_logger.error(f"Tavily内容提取异常: {str(e)}", exc_info=True)
            return {"error": str(e)}


# 工具服务类，管理所有可用工具
class ToolsService:
    """工具服务，管理所有可用的工具"""
    
    def __init__(self):
        """初始化工具服务"""
        self.tools = {}
        self.available_tools = {
            "tavily": TavilyTool
        }
        api_logger.info(f"工具服务初始化，可用工具: {list(self.available_tools.keys())}")
    
    def get_tool(self, tool_name: str, config: Dict[str, Any] = None) -> Any:
        """获取指定的工具实例"""
        if tool_name not in self.available_tools:
            api_logger.warning(f"请求的工具 {tool_name} 不可用")
            return None
        
        # 检查是否已有缓存的实例
        cache_key = f"{tool_name}_{json.dumps(config) if config else 'default'}"
        if cache_key in self.tools:
            return self.tools[cache_key]
        
        # 创建新的工具实例
        try:
            if config:
                tool_instance = self.available_tools[tool_name](**config)
            else:
                tool_instance = self.available_tools[tool_name]()
            
            # 缓存工具实例
            self.tools[cache_key] = tool_instance
            api_logger.info(f"创建工具 {tool_name} 实例成功")
            return tool_instance
        except Exception as e:
            api_logger.error(f"创建工具 {tool_name} 实例失败: {str(e)}", exc_info=True)
            return None
    
    def execute_tool(
        self, 
        tool_name: str, 
        action: str, 
        params: Dict[str, Any] = None, 
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行工具操作"""
        tool = self.get_tool(tool_name, config)
        if not tool:
            return {"error": f"工具 {tool_name} 不可用"}
        
        if not hasattr(tool, action):
            api_logger.error(f"工具 {tool_name} 不支持操作 {action}")
            return {"error": f"操作 {action} 不支持"}
        
        try:
            method = getattr(tool, action)
            if params:
                result = method(**params)
            else:
                result = method()
            
            api_logger.info(f"工具 {tool_name} 执行 {action} 操作成功")
            return result
        except Exception as e:
            api_logger.error(f"工具 {tool_name} 执行 {action} 操作失败: {str(e)}", exc_info=True)
            return {"error": str(e)}


# 创建全局工具服务实例
tools_service = ToolsService() 