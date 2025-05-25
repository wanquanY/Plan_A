"""
工具配置管理器
提供高级的工具管理和配置功能
"""

from typing import Dict, List, Any, Optional
from .tools_config import (
    AVAILABLE_TOOLS, 
    TOOL_CATEGORIES, 
    TOOL_PROVIDERS,
    get_tools_by_category,
    get_tools_by_provider,
    get_tool_by_name,
    get_all_tool_names
)

class ToolsManager:
    """工具配置管理器"""
    
    def __init__(self):
        """初始化工具管理器"""
        self._tools_cache = {}
        self._provider_cache = {}
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        return AVAILABLE_TOOLS.copy()
    
    def get_tool_providers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有工具提供商信息"""
        return TOOL_PROVIDERS.copy()
    
    def get_tool_categories(self) -> Dict[str, List[str]]:
        """获取工具分类信息"""
        return TOOL_CATEGORIES.copy()
    
    def validate_tool_config(self, tool_name: str, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证工具配置是否有效
        
        Args:
            tool_name: 工具名称
            config: 工具配置
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        tool = get_tool_by_name(tool_name)
        if not tool:
            return False, f"工具 {tool_name} 不存在"
        
        # 检查是否需要API密钥
        provider = self._get_tool_provider(tool_name)
        if provider and TOOL_PROVIDERS[provider].get("api_key_required", False):
            if not config.get("api_key"):
                return False, f"工具 {tool_name} 需要API密钥"
        
        return True, ""
    
    def get_agent_tools(self, agent_tools_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据Agent配置获取可用工具列表
        支持两种配置格式：
        1. 提供商级别配置（向后兼容）
        2. 工具级别配置（新格式）
        
        Args:
            agent_tools_config: Agent的工具配置
            
        Returns:
            List: 可用工具列表
        """
        if not agent_tools_config:
            return []
        
        tools = []
        
        # 检查配置格式
        if self._is_tool_level_config(agent_tools_config):
            # 新格式：工具级别配置
            tools = self._get_tools_from_tool_config(agent_tools_config)
        else:
            # 旧格式：提供商级别配置（向后兼容）
            tools = self._get_tools_from_provider_config(agent_tools_config)
        
        return tools
    
    def _is_tool_level_config(self, config: Dict[str, Any]) -> bool:
        """
        判断是否为工具级别配置
        工具级别配置的特征：配置键是具体的工具名称
        """
        tool_names = get_all_tool_names()
        
        # 如果配置中有任何一个键是具体工具名称，则认为是工具级别配置
        for key in config.keys():
            if key in tool_names:
                return True
        
        # 如果配置中的键都是提供商名称，则认为是提供商级别配置
        return False
    
    def _get_tools_from_tool_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从工具级别配置中获取工具列表
        
        配置格式：
        {
            "serper_search": {
                "enabled": true,
                "api_key": "xxx"
            },
            "tavily_search": {
                "enabled": false,
                "api_key": "yyy"
            }
        }
        """
        tools = []
        
        for tool_name, tool_config in config.items():
            if not isinstance(tool_config, dict):
                continue
            
            if tool_config.get("enabled", False):
                # 获取工具配置
                tool_definition = get_tool_by_name(tool_name)
                if tool_definition:
                    tools.append(tool_definition)
        
        return tools
    
    def _get_tools_from_provider_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从提供商级别配置中获取工具列表（向后兼容）
        
        配置格式：
        {
            "serper": {
                "enabled": true,
                "api_key": "xxx"
            },
            "tavily": {
                "enabled": false,
                "api_key": "yyy"
            }
        }
        """
        tools = []
        
        # 遍历所有提供商
        for provider_name, provider_config in config.items():
            if not isinstance(provider_config, dict):
                continue
                
            if provider_config.get("enabled", False):
                # 获取该提供商的所有工具
                provider_tools = get_tools_by_provider(provider_name)
                tools.extend(provider_tools)
        
        return tools
    
    def get_tool_api_key(self, tool_name: str, agent_tools_config: Dict[str, Any]) -> Optional[str]:
        """
        获取指定工具的API密钥
        
        Args:
            tool_name: 工具名称
            agent_tools_config: Agent的工具配置
            
        Returns:
            Optional[str]: API密钥，如果未找到则返回None
        """
        if not agent_tools_config:
            return None
        
        # 检查是否为工具级别配置
        if self._is_tool_level_config(agent_tools_config):
            # 工具级别配置：直接查找工具配置
            tool_config = agent_tools_config.get(tool_name, {})
            return tool_config.get("api_key")
        else:
            # 提供商级别配置：查找工具所属的提供商
            provider = self._get_tool_provider(tool_name)
            if provider and provider in agent_tools_config:
                provider_config = agent_tools_config[provider]
                if isinstance(provider_config, dict):
                    return provider_config.get("api_key")
        
        return None
    
    def get_tool_usage_stats(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具使用统计信息（占位符，可以后续实现）
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Dict: 使用统计信息
        """
        return {
            "tool_name": tool_name,
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0,
            "last_used": None
        }
    
    def get_recommended_tools(self, use_case: str) -> List[str]:
        """
        根据使用场景推荐工具
        
        Args:
            use_case: 使用场景 (search, news, extract等)
            
        Returns:
            List: 推荐的工具名称列表
        """
        recommendations = {
            "search": ["serper_search", "tavily_search"],
            "news": ["serper_news"],
            "extract": ["tavily_extract"],
            "scrape": ["serper_scrape", "tavily_extract"],
            "web": ["tavily_search", "tavily_extract", "serper_scrape"],
            "realtime": ["serper_search", "serper_news"],
            "content": ["serper_scrape", "tavily_extract"]
        }
        
        return recommendations.get(use_case, [])
    
    def export_tools_config(self) -> Dict[str, Any]:
        """
        导出完整的工具配置
        
        Returns:
            Dict: 完整的工具配置信息
        """
        return {
            "tools": self.get_available_tools(),
            "providers": self.get_tool_providers(),
            "categories": self.get_tool_categories(),
            "total_tools": len(AVAILABLE_TOOLS),
            "total_providers": len(TOOL_PROVIDERS)
        }
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索工具
        
        Args:
            query: 搜索关键词
            
        Returns:
            List: 匹配的工具列表
        """
        query = query.lower()
        matching_tools = []
        
        for tool in AVAILABLE_TOOLS:
            tool_name = tool["function"]["name"].lower()
            tool_desc = tool["function"]["description"].lower()
            
            if query in tool_name or query in tool_desc:
                matching_tools.append(tool)
        
        return matching_tools
    
    def get_tool_dependencies(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具依赖信息
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Dict: 依赖信息
        """
        provider = self._get_tool_provider(tool_name)
        if not provider:
            return {}
        
        provider_info = TOOL_PROVIDERS[provider]
        return {
            "provider": provider,
            "provider_name": provider_info["name"],
            "api_key_required": provider_info["api_key_required"],
            "website": provider_info["website"],
            "description": provider_info["description"]
        }
    
    def _get_tool_provider(self, tool_name: str) -> Optional[str]:
        """获取工具的提供商"""
        for provider, provider_info in TOOL_PROVIDERS.items():
            if tool_name in provider_info["tools"]:
                return provider
        return None
    
    def validate_agent_tools_config(self, tools_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证Agent工具配置的完整性
        支持两种配置格式的验证
        
        Args:
            tools_config: Agent的工具配置
            
        Returns:
            Dict: 验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "enabled_tools": [],
            "missing_api_keys": [],
            "config_type": "unknown"
        }
        
        if not tools_config:
            result["warnings"].append("未配置任何工具")
            return result
        
        # 判断配置类型
        if self._is_tool_level_config(tools_config):
            result["config_type"] = "tool_level"
            self._validate_tool_level_config(tools_config, result)
        else:
            result["config_type"] = "provider_level"
            self._validate_provider_level_config(tools_config, result)
        
        return result
    
    def _validate_tool_level_config(self, tools_config: Dict[str, Any], result: Dict[str, Any]):
        """验证工具级别配置"""
        tool_names = get_all_tool_names()
        
        for tool_name, tool_config in tools_config.items():
            if not isinstance(tool_config, dict):
                result["errors"].append(f"工具 {tool_name} 配置格式错误")
                result["valid"] = False
                continue
            
            # 检查工具是否存在
            if tool_name not in tool_names:
                result["errors"].append(f"未知的工具: {tool_name}")
                result["valid"] = False
                continue
            
            if tool_config.get("enabled", False):
                # 检查API密钥
                provider = self._get_tool_provider(tool_name)
                if provider and TOOL_PROVIDERS[provider].get("api_key_required", False):
                    if not tool_config.get("api_key"):
                        result["missing_api_keys"].append(tool_name)
                        result["warnings"].append(f"工具 {tool_name} 缺少API密钥")
                
                # 添加启用的工具
                result["enabled_tools"].append(tool_name)
    
    def _validate_provider_level_config(self, tools_config: Dict[str, Any], result: Dict[str, Any]):
        """验证提供商级别配置（向后兼容）"""
        for provider_name, provider_config in tools_config.items():
            if not isinstance(provider_config, dict):
                result["errors"].append(f"提供商 {provider_name} 配置格式错误")
                result["valid"] = False
                continue
            
            if provider_config.get("enabled", False):
                # 检查提供商是否存在
                if provider_name not in TOOL_PROVIDERS:
                    result["errors"].append(f"未知的工具提供商: {provider_name}")
                    result["valid"] = False
                    continue
                
                # 检查API密钥
                provider_info = TOOL_PROVIDERS[provider_name]
                if provider_info.get("api_key_required", False):
                    if not provider_config.get("api_key"):
                        result["missing_api_keys"].append(provider_name)
                        result["warnings"].append(f"提供商 {provider_name} 缺少API密钥")
                
                # 添加启用的工具
                provider_tools = provider_info["tools"]
                result["enabled_tools"].extend(provider_tools)
    
    def convert_provider_config_to_tool_config(self, provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将提供商级别配置转换为工具级别配置
        
        Args:
            provider_config: 提供商级别配置
            
        Returns:
            Dict: 工具级别配置
        """
        tool_config = {}
        
        for provider_name, provider_settings in provider_config.items():
            if not isinstance(provider_settings, dict):
                continue
            
            if provider_name in TOOL_PROVIDERS:
                provider_info = TOOL_PROVIDERS[provider_name]
                api_key = provider_settings.get("api_key", "")
                enabled = provider_settings.get("enabled", False)
                
                # 为该提供商的所有工具创建配置
                for tool_name in provider_info["tools"]:
                    tool_config[tool_name] = {
                        "enabled": enabled,
                        "name": tool_name,
                        "api_key": api_key,
                        "provider": provider_name
                    }
        
        return tool_config
    
    def get_tools_with_details(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的详细信息，包括提供商信息
        
        Returns:
            List: 包含详细信息的工具列表
        """
        tools_with_details = []
        
        for tool in AVAILABLE_TOOLS:
            tool_name = tool["function"]["name"]
            provider = self._get_tool_provider(tool_name)
            
            tool_detail = {
                "name": tool_name,
                "display_name": tool["function"]["name"].replace("_", " ").title(),
                "description": tool["function"]["description"],
                "provider": provider,
                "provider_info": TOOL_PROVIDERS.get(provider, {}),
                "parameters": tool["function"]["parameters"]["properties"],
                "required_params": tool["function"]["parameters"].get("required", []),
                "api_key_required": TOOL_PROVIDERS.get(provider, {}).get("api_key_required", False)
            }
            
            tools_with_details.append(tool_detail)
        
        return tools_with_details
    
    def get_tools_grouped_by_provider(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        按提供商分组获取工具详情
        
        Returns:
            Dict: 按提供商分组的工具详情
        """
        grouped_tools = {}
        tools_with_details = self.get_tools_with_details()
        
        for tool in tools_with_details:
            provider = tool["provider"]
            if provider not in grouped_tools:
                grouped_tools[provider] = []
            grouped_tools[provider].append(tool)
        
        return grouped_tools
    
    def create_default_tool_config(self, enabled_tools: List[str] = None) -> Dict[str, Any]:
        """
        创建默认的工具级别配置
        
        Args:
            enabled_tools: 要启用的工具列表，如果为None则全部禁用
            
        Returns:
            Dict: 默认工具配置
        """
        if enabled_tools is None:
            enabled_tools = []
        
        tool_config = {}
        tool_names = get_all_tool_names()
        
        for tool_name in tool_names:
            tool_config[tool_name] = {
                "enabled": tool_name in enabled_tools,
                "name": tool_name,
                "api_key": "",
                "provider": self._get_tool_provider(tool_name)
            }
        
        return tool_config


# 创建全局工具管理器实例
tools_manager = ToolsManager() 