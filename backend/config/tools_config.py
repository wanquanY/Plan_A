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
            "description": "通过Google搜索引擎查询信息，获取搜索结果列表。返回的结果包含标题、摘要和链接。如需获取某个链接的详细内容，请使用serper_scrape工具进一步解析。",
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
            "description": "搜索最新新闻信息，返回新闻标题、摘要和链接。如需获取新闻的完整内容，请使用serper_scrape工具解析具体的新闻链接。",
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
            "description": "解析网页内容获取详细信息。当搜索结果中有感兴趣的链接时，使用此工具获取网页的完整内容、正文、标题等详细信息。特别适用于需要深入了解某个网页内容的场景。",
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
    },
    # 笔记阅读工具
    {
        "type": "function",
        "function": {
            "name": "note_reader",
            "description": "阅读用户当前正在编辑的笔记内容。如果在侧边栏聊天中调用，会自动读取当前关联的笔记。也可以通过笔记ID或标题搜索其他笔记，并支持指定阅读的行数范围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "integer",
                        "description": "要阅读的笔记ID，如果不提供则自动读取当前关联的笔记"
                    },
                    "search_title": {
                        "type": "string",
                        "description": "通过标题搜索笔记，支持模糊匹配"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "开始阅读的行数（从1开始计数）",
                        "default": 1
                    },
                    "line_count": {
                        "type": "integer",
                        "description": "要阅读的行数，如果不指定则读取全部内容",
                        "default": -1
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "是否包含笔记的元数据信息（创建时间、更新时间等）",
                        "default": True
                    }
                },
                "required": []
            }
        }
    }
]

# 工具分类映射
TOOL_CATEGORIES = {
    "search": ["tavily_search", "tavily_extract", "serper_search", "serper_news"],
    "scrape": ["tavily_extract", "serper_scrape"],
    "note": ["note_reader"],
    "document": ["note_reader"],
    "tavily": ["tavily_search", "tavily_extract"],
    "serper": ["serper_search", "serper_news", "serper_scrape"],
    "local": ["note_reader"]
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
    },
    "local": {
        "name": "本地工具",
        "description": "用户笔记和文档处理工具",
        "tools": ["note_reader"],
        "api_key_required": False,
        "website": ""
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