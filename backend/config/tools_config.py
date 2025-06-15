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
            "description": "阅读用户的笔记内容。在侧边栏聊天中，会自动读取当前关联的笔记；在其他情况下，建议明确指定要读取的笔记。支持通过笔记ID或标题搜索笔记，并可指定阅读的行数范围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "要阅读的笔记ID。在侧边栏聊天中可以不提供（会自动读取关联笔记），但在其他场景建议明确指定"
                    },
                    "search_title": {
                        "type": "string",
                        "description": "通过标题搜索笔记，支持模糊匹配。当不知道具体笔记ID时可以使用"
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
    },
    # 笔记编辑工具
    {
        "type": "function",
        "function": {
            "name": "note_editor",
            "description": "编辑用户的笔记内容。支持多种编辑操作：完全替换、追加内容、前置内容、插入内容、替换指定行、替换指定文本等。在侧边栏聊天中会自动编辑当前关联的笔记。",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "要编辑的笔记ID。在侧边栏聊天中可以不提供（会自动编辑关联笔记）"
                    },
                    "search_title": {
                        "type": "string",
                        "description": "通过标题搜索要编辑的笔记，支持模糊匹配"
                    },
                    "edit_type": {
                        "type": "string",
                        "enum": ["replace", "append", "prepend", "insert", "replace_lines", "replace_text"],
                        "description": "编辑类型：replace(完全替换), append(追加到末尾), prepend(添加到开头), insert(在指定位置插入), replace_lines(替换指定行), replace_text(替换指定文本)",
                        "default": "replace"
                    },
                    "content": {
                        "type": "string",
                        "description": "新的内容。用于replace、append、prepend、insert、replace_lines操作"
                    },
                    "title": {
                        "type": "string",
                        "description": "新的标题（可选）。如果提供，会同时更新笔记标题"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "开始行号（从1开始计数）。用于replace_lines操作"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "结束行号。用于replace_lines操作，如果不提供则只替换start_line指定的行"
                    },
                    "insert_position": {
                        "type": "string",
                        "description": "插入位置。用于insert操作。格式：start(开头), end(结尾), after_line:N(在第N行后), before_line:N(在第N行前)"
                    },
                    "search_text": {
                        "type": "string",
                        "description": "要搜索的文本。用于replace_text操作"
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "替换的文本。用于replace_text操作"
                    },
                    "save_immediately": {
                        "type": "boolean",
                        "description": "是否立即保存到数据库。默认为预览模式（false）",
                        "default": False
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
    "note": ["note_reader", "note_editor"],
    "document": ["note_reader", "note_editor"],
    "tavily": ["tavily_search", "tavily_extract"],
    "serper": ["serper_search", "serper_news", "serper_scrape"],
    "local": ["note_reader", "note_editor"]
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
        "tools": ["note_reader", "note_editor"],
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