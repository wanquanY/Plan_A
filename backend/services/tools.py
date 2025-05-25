from typing import Dict, List, Any, Optional
import os
import json
import requests
import http.client
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


class SerperTool:
    """Serper Google搜索工具"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化Serper工具"""
        self.api_key = api_key
        if not self.api_key:
            # 尝试从环境变量中获取API密钥
            self.api_key = os.environ.get("SERPER_API_KEY")
        
        self.base_host = "google.serper.dev"
        
        api_logger.info(f"Serper工具初始化，API密钥: {self.api_key[:5]}*** (如果有)")
    
    def search(
        self, 
        query: str, 
        max_results: int = 10,
        gl: str = "cn",
        hl: str = "zh-cn",
        search_type: str = "search"
    ) -> Dict[str, Any]:
        """执行Serper搜索查询"""
        if not self.api_key:
            api_logger.error("未提供Serper API密钥，无法执行搜索")
            return {"error": "未提供API密钥"}
        
        try:
            # 使用http.client进行连接
            conn = http.client.HTTPSConnection(self.base_host)
            
            payload = json.dumps({
                "q": query,
                "gl": gl,
                "hl": hl,
                "num": max_results
            })
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            api_logger.info(f"执行Serper搜索: {query}, 最大结果数: {max_results}")
            
            # 根据搜索类型选择端点
            endpoint = f"/{search_type}"
            conn.request("POST", endpoint, payload, headers)
            
            res = conn.getresponse()
            data = res.read()
            
            if res.status == 200:
                result = json.loads(data.decode("utf-8"))
                
                # 统计结果数量
                organic_count = len(result.get('organic', []))
                news_count = len(result.get('topStories', []))
                total_count = organic_count + news_count
                
                api_logger.info(f"Serper搜索成功，获取到 {total_count} 条结果 (有机结果: {organic_count}, 新闻: {news_count})")
                
                # 格式化结果以便AI理解
                formatted_result = {
                    "query": query,
                    "total_results": total_count,
                    "organic_results": result.get('organic', []),
                    "news_results": result.get('topStories', []),
                    "search_parameters": result.get('searchParameters', {}),
                    "raw_response": result
                }
                
                return formatted_result
            else:
                error_text = data.decode("utf-8")
                api_logger.error(f"Serper搜索API错误: {res.status}, {error_text}")
                return {"error": f"API错误: {res.status}", "details": error_text}
                
        except Exception as e:
            api_logger.error(f"Serper搜索异常: {str(e)}", exc_info=True)
            return {"error": str(e)}
        finally:
            try:
                conn.close()
            except:
                pass
    
    def news_search(
        self, 
        query: str, 
        max_results: int = 10,
        gl: str = "cn",
        hl: str = "zh-cn"
    ) -> Dict[str, Any]:
        """执行Serper新闻搜索"""
        return self.search(query, max_results, gl, hl, "news")
    
    def image_search(
        self, 
        query: str, 
        max_results: int = 10,
        gl: str = "cn",
        hl: str = "zh-cn"
    ) -> Dict[str, Any]:
        """执行Serper图片搜索"""
        return self.search(query, max_results, gl, hl, "images")

    def scrape_url(
        self, 
        url: str,
        include_markdown: bool = True
    ) -> Dict[str, Any]:
        """执行Serper网页解析"""
        if not self.api_key:
            api_logger.error("未提供Serper API密钥，无法执行网页解析")
            return {"error": "未提供API密钥"}
        
        try:
            # 使用http.client进行连接到scrape.serper.dev
            conn = http.client.HTTPSConnection("scrape.serper.dev")
            
            payload = json.dumps({
                "url": url,
                "includeMarkdown": include_markdown
            })
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            api_logger.info(f"执行Serper网页解析: {url}, 包含Markdown: {include_markdown}")
            
            conn.request("POST", "/", payload, headers)
            
            res = conn.getresponse()
            data = res.read()
            
            if res.status == 200:
                result = json.loads(data.decode("utf-8"))
                
                api_logger.info(f"Serper网页解析成功，URL: {url}")
                
                # 格式化结果以便AI理解
                formatted_result = {
                    "url": url,
                    "success": True,
                    "content": result.get("text", ""),
                    "markdown": result.get("markdown", "") if include_markdown else None,
                    "title": result.get("title", ""),
                    "meta_description": result.get("description", ""),
                    "links": result.get("links", []),
                    "images": result.get("images", []),
                    "raw_response": result
                }
                
                return formatted_result
            else:
                error_text = data.decode("utf-8")
                api_logger.error(f"Serper网页解析API错误: {res.status}, {error_text}")
                return {"error": f"API错误: {res.status}", "details": error_text}
                
        except Exception as e:
            api_logger.error(f"Serper网页解析异常: {str(e)}", exc_info=True)
            return {"error": str(e)}
        finally:
            try:
                conn.close()
            except:
                pass


# 工具服务类，管理所有可用工具
class ToolsService:
    """工具服务，管理所有可用的工具"""
    
    def __init__(self):
        """初始化工具服务"""
        self.tools = {}
        self.available_tools = {
            "tavily": TavilyTool,
            "serper": SerperTool
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