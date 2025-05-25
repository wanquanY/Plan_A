"""
工具配置文件
定义所有可用的工具及其参数配置
"""

# 定义支持的工具配置
AVAILABLE_TOOLS = [
    # Tavily工具（保留向后兼容）
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "通过Tavily搜索引擎查询信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回的最大结果数量",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tavily_extract",
            "description": "从指定URL提取网页内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "需要提取内容的URL列表"
                    },
                    "include_images": {
                        "type": "boolean",
                        "description": "是否包含图片",
                        "default": False
                    }
                },
                "required": ["urls"]
            }
        }
    },
    # Serper工具
    {
        "type": "function",
        "function": {
            "name": "serper_search",
            "description": "通过Serper Google搜索引擎查询信息，获取最新的网络搜索结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回的最大结果数量",
                        "default": 10
                    },
                    "gl": {
                        "type": "string",
                        "description": "搜索地区代码",
                        "default": "cn"
                    },
                    "hl": {
                        "type": "string",
                        "description": "搜索语言代码",
                        "default": "zh-cn"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "serper_news",
            "description": "通过Serper搜索最新新闻信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "新闻搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回的最大结果数量",
                        "default": 10
                    },
                    "gl": {
                        "type": "string",
                        "description": "搜索地区代码",
                        "default": "cn"
                    },
                    "hl": {
                        "type": "string",
                        "description": "搜索语言代码",
                        "default": "zh-cn"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "serper_scrape",
            "description": "通过Serper解析指定网页的内容，提取文本、标题、链接等信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "需要解析的网页URL"
                    },
                    "include_markdown": {
                        "type": "boolean",
                        "description": "是否包含Markdown格式的内容",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        }
    }
]

# 工具分类映射
TOOL_CATEGORIES = {
    "search": ["tavily_search", "tavily_extract", "serper_search", "serper_news"],
    "scrape": ["tavily_extract", "serper_scrape"],
    "tavily": ["tavily_search", "tavily_extract"],
    "serper": ["serper_search", "serper_news", "serper_scrape"]
}

# 工具提供商配置
TOOL_PROVIDERS = {
    "tavily": {
        "name": "Tavily",
        "description": "Tavily搜索和网页解析工具",
        "tools": ["tavily_search", "tavily_extract"],
        "api_key_required": True,
        "website": "https://tavily.com"
    },
    "serper": {
        "name": "Serper",
        "description": "基于Google的搜索API和网页解析工具",
        "tools": ["serper_search", "serper_news", "serper_scrape"],
        "api_key_required": True,
        "website": "https://serper.dev"
    }
}

def get_tools_by_category(category: str) -> list:
    """根据分类获取工具列表"""
    if category not in TOOL_CATEGORIES:
        return []
    
    tool_names = TOOL_CATEGORIES[category]
    return [tool for tool in AVAILABLE_TOOLS if tool["function"]["name"] in tool_names]

def get_tools_by_provider(provider: str) -> list:
    """根据提供商获取工具列表"""
    if provider not in TOOL_PROVIDERS:
        return []
    
    tool_names = TOOL_PROVIDERS[provider]["tools"]
    return [tool for tool in AVAILABLE_TOOLS if tool["function"]["name"] in tool_names]

def get_tool_by_name(tool_name: str) -> dict:
    """根据名称获取单个工具配置"""
    for tool in AVAILABLE_TOOLS:
        if tool["function"]["name"] == tool_name:
            return tool
    return None

def get_all_tool_names() -> list:
    """获取所有工具名称列表"""
    return [tool["function"]["name"] for tool in AVAILABLE_TOOLS] 