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
        
        # 修复：在切片操作之前检查api_key是否为None
        if self.api_key:
            api_logger.info(f"Tavily工具初始化，API密钥: {self.api_key[:5]}***")
        else:
            api_logger.info("Tavily工具初始化，未提供API密钥")
    
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
        
        # 修复：在切片操作之前检查api_key是否为None
        if self.api_key:
            api_logger.info(f"Serper工具初始化，API密钥: {self.api_key[:5]}***")
        else:
            api_logger.info("Serper工具初始化，未提供API密钥")
    
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


class NoteReaderTool:
    """笔记阅读工具"""
    
    def __init__(self, db_session = None, session_id: Optional[int] = None):
        """
        初始化笔记阅读器工具
        
        Args:
            db_session: 数据库会话
            session_id: 可选的会话ID，用于确定当前对话的上下文
        """
        self.db_session = db_session
        self.session_id = session_id
        api_logger.info(f"笔记阅读工具初始化，会话ID: {session_id}")
    
    async def read_note(
        self,
        note_id: Optional[int] = None,
        search_title: Optional[str] = None,
        start_line: int = 1,
        line_count: int = -1,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """读取笔记内容"""
        if not self.db_session:
            api_logger.error("未提供数据库会话，无法读取笔记")
            return {"error": "数据库连接不可用"}
        
        try:
            from backend.models.note import Note
            from backend.models.chat import Chat
            from sqlalchemy import select, or_, and_
            
            # 确保在正确的异步上下文中执行数据库操作
            api_logger.info(f"开始读取笔记，参数: note_id={note_id}, search_title={search_title}")
            
            # 获取用户权限
            user_id = None
            session_note_id = None
            if self.session_id:
                try:
                    chat_stmt = select(Chat).where(Chat.id == self.session_id)
                    chat_result = await self.db_session.execute(chat_stmt)
                    chat = chat_result.scalar_one_or_none()
                    if chat:
                        user_id = chat.user_id
                        api_logger.info(f"从会话 {self.session_id} 获取用户ID: {user_id}")
                        
                        # 查找与此会话关联的笔记
                        from backend.models.note_session import NoteSession
                        note_session_stmt = select(NoteSession).where(
                            NoteSession.session_id == self.session_id
                        )
                        note_session_result = await self.db_session.execute(note_session_stmt)
                        note_session = note_session_result.scalar_one_or_none()
                        if note_session:
                            # 通过note_session获取笔记
                            note_stmt = select(Note).where(
                                Note.id == note_session.note_id,
                                Note.user_id == user_id,
                                Note.is_deleted == False
                            )
                            note_result = await self.db_session.execute(note_stmt)
                            session_note = note_result.scalar_one_or_none()
                            if session_note:
                                session_note_id = session_note.id
                                api_logger.info(f"找到会话关联的笔记ID: {session_note_id}")
                        else:
                            api_logger.info(f"未找到会话 {self.session_id} 关联的笔记")
                except Exception as e:
                    api_logger.error(f"获取会话信息时出错: {str(e)}", exc_info=True)
                    # 继续执行，不因会话信息获取失败而中断
            
            # 构建查询条件
            query_conditions = [
                Note.is_deleted == False
            ]
            
            # 如果有用户ID，添加用户权限过滤
            if user_id:
                query_conditions.append(Note.user_id == user_id)
            
            # 根据参数选择查询方式
            if note_id:
                # 通过ID直接查询
                query_conditions.append(Note.id == note_id)
                api_logger.info(f"通过指定ID查询笔记: {note_id}")
            elif session_note_id:
                # 如果没有指定笔记ID，但有会话关联的笔记，使用会话关联的笔记
                query_conditions.append(Note.id == session_note_id)
                api_logger.info(f"使用会话关联的笔记ID: {session_note_id}")
            elif search_title:
                # 通过标题模糊搜索
                query_conditions.append(Note.title.ilike(f"%{search_title}%"))
                api_logger.info(f"通过标题搜索笔记: {search_title}")
            else:
                # 如果都没提供，返回用户最近的笔记
                api_logger.info("未指定查询条件，返回最近的笔记")
            
            # 执行查询
            stmt = select(Note).where(*query_conditions).order_by(Note.updated_at.desc())
            
            notes = []
            try:
                if note_id:
                    # 如果是通过ID查询，只取一个
                    result = await self.db_session.execute(stmt)
                    note = result.scalar_one_or_none()
                    notes = [note] if note else []
                else:
                    # 如果是搜索或获取最近笔记，可能返回多个
                    result = await self.db_session.execute(stmt.limit(10))  # 限制返回数量
                    notes = result.scalars().all()
            except Exception as e:
                api_logger.error(f"执行数据库查询时出错: {str(e)}", exc_info=True)
                return {"error": f"数据库查询失败: {str(e)}"}
            
            if not notes:
                return {
                    "error": "未找到匹配的笔记",
                    "search_criteria": {
                        "note_id": note_id,
                        "search_title": search_title
                    }
                }
            
            # 处理多个笔记的情况
            if len(notes) > 1 and not search_title:
                # 如果没有搜索条件但返回多个，只取最新的一个
                notes = [notes[0]]
            
            results = []
            for note in notes:
                # 处理笔记内容
                content = note.content or ""
                
                # 按行分割内容
                lines = content.split('\n')
                total_lines = len(lines)
                
                # 处理行数范围
                if start_line < 1:
                    start_line = 1
                
                end_line = total_lines
                if line_count > 0:
                    end_line = min(start_line + line_count - 1, total_lines)
                
                # 提取指定行数的内容
                if start_line <= total_lines:
                    selected_lines = lines[start_line - 1:end_line]
                    selected_content = '\n'.join(selected_lines)
                else:
                    selected_content = ""
                
                # 构建结果
                note_result = {
                    "note_id": note.id,
                    "title": note.title,
                    "content": selected_content,
                    "content_info": {
                        "total_lines": total_lines,
                        "start_line": start_line,
                        "end_line": end_line,
                        "displayed_lines": len(selected_lines) if start_line <= total_lines else 0
                    }
                }
                
                # 添加元数据信息
                if include_metadata:
                    # 获取笔记关联的会话信息
                    try:
                        from backend.models.note_session import NoteSession
                        note_sessions_stmt = select(NoteSession).where(NoteSession.note_id == note.id)
                        note_sessions_result = await self.db_session.execute(note_sessions_stmt)
                        note_sessions = note_sessions_result.scalars().all()
                        
                        # 提取会话ID列表和主要会话ID
                        session_ids = [ns.session_id for ns in note_sessions]
                        primary_session_id = next((ns.session_id for ns in note_sessions if ns.is_primary), None)
                        
                        note_result["metadata"] = {
                            "created_at": note.created_at.isoformat() if note.created_at else None,
                            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                            "session_ids": session_ids,  # 所有关联的会话ID
                            "primary_session_id": primary_session_id,  # 主要会话ID
                            "is_public": note.is_public,
                            "last_edited_position": note.last_edited_position
                        }
                    except Exception as e:
                        api_logger.error(f"获取笔记会话关联信息失败: {str(e)}")
                        # 如果获取会话信息失败，提供基本元数据
                        note_result["metadata"] = {
                            "created_at": note.created_at.isoformat() if note.created_at else None,
                            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                            "session_ids": [],
                            "primary_session_id": None,
                            "is_public": note.is_public,
                            "last_edited_position": note.last_edited_position
                        }
                
                results.append(note_result)
            
            # 如果只有一个结果，直接返回该结果；如果有多个，返回列表
            if len(results) == 1:
                api_logger.info(f"成功读取笔记: {results[0]['title']}")
                return results[0]
            else:
                api_logger.info(f"找到 {len(results)} 个匹配的笔记")
                return {
                    "multiple_notes": True,
                    "count": len(results),
                    "notes": results
                }
                
        except Exception as e:
            api_logger.error(f"读取笔记异常: {str(e)}", exc_info=True)
            return {"error": f"读取笔记失败: {str(e)}"}


class NoteEditorTool:
    """笔记编辑工具"""
    
    def __init__(self, db_session = None, session_id: Optional[int] = None):
        """
        初始化笔记编辑器工具
        
        Args:
            db_session: 数据库会话  
            session_id: 可选的会话ID，用于自动关联新创建的笔记
        """
        self.db_session = db_session
        self.session_id = session_id
        api_logger.info(f"笔记编辑工具初始化，会话ID: {session_id}")
    
    async def edit_note(
        self,
        note_id: Optional[int] = None,
        search_title: Optional[str] = None,
        edit_type: str = "replace",
        content: Optional[str] = None,
        title: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        insert_position: Optional[str] = None,
        search_text: Optional[str] = None,
        replace_text: Optional[str] = None,
        save_immediately: bool = False
    ) -> Dict[str, Any]:
        """编辑笔记内容
        
        Args:
            note_id: 要编辑的笔记ID
            search_title: 通过标题搜索笔记
            edit_type: 编辑类型 - replace(替换全部), append(追加), prepend(前置), insert(插入), replace_lines(替换行), replace_text(替换文本)
            content: 新内容（用于replace, append, prepend, insert）
            title: 新标题（可选）
            start_line: 开始行号（用于replace_lines）
            end_line: 结束行号（用于replace_lines）
            insert_position: 插入位置 - start(开头), end(结尾), after_line:N(在第N行后), before_line:N(在第N行前)
            search_text: 要搜索的文本（用于replace_text）
            replace_text: 替换的文本（用于replace_text）
            save_immediately: 是否立即保存，默认为预览模式
        """
        if not self.db_session:
            api_logger.error("未提供数据库会话，无法编辑笔记")
            return {"error": "数据库连接不可用"}
        
        try:
            from backend.models.note import Note
            from backend.models.chat import Chat
            from sqlalchemy import select, or_, and_
            
            # 确保在正确的异步上下文中执行数据库操作
            api_logger.info(f"开始编辑笔记，参数: note_id={note_id}, edit_type={edit_type}")
            
            # 获取用户权限
            user_id = None
            session_note_id = None
            if self.session_id:
                try:
                    chat_stmt = select(Chat).where(Chat.id == self.session_id)
                    chat_result = await self.db_session.execute(chat_stmt)
                    chat = chat_result.scalar_one_or_none()
                    if chat:
                        user_id = chat.user_id
                        api_logger.info(f"从会话 {self.session_id} 获取用户ID: {user_id}")
                        
                        # 查找与此会话关联的笔记
                        from backend.models.note_session import NoteSession
                        note_session_stmt = select(NoteSession).where(
                            NoteSession.session_id == self.session_id
                        )
                        note_session_result = await self.db_session.execute(note_session_stmt)
                        note_session = note_session_result.scalar_one_or_none()
                        if note_session:
                            # 通过note_session获取笔记
                            note_stmt = select(Note).where(
                                Note.id == note_session.note_id,
                                Note.user_id == user_id,
                                Note.is_deleted == False
                            )
                            note_result = await self.db_session.execute(note_stmt)
                            session_note = note_result.scalar_one_or_none()
                            if session_note:
                                session_note_id = session_note.id
                                api_logger.info(f"找到会话关联的笔记ID: {session_note_id}")
                        else:
                            api_logger.info(f"未找到会话 {self.session_id} 关联的笔记")
                except Exception as e:
                    api_logger.error(f"获取会话信息时出错: {str(e)}", exc_info=True)
                    # 继续执行，不因会话信息获取失败而中断
            
            # 确定要编辑的笔记
            target_note = None
            
            try:
                if note_id:
                    # 通过ID查找笔记
                    query_conditions = [
                        Note.id == note_id,
                        Note.is_deleted == False
                    ]
                    if user_id:
                        query_conditions.append(Note.user_id == user_id)
                    
                    stmt = select(Note).where(and_(*query_conditions))
                    result = await self.db_session.execute(stmt)
                    target_note = result.scalar_one_or_none()
                    
                elif search_title:
                    # 通过标题搜索笔记
                    query_conditions = [
                        Note.title.ilike(f"%{search_title}%"),
                        Note.is_deleted == False
                    ]
                    if user_id:
                        query_conditions.append(Note.user_id == user_id)
                    
                    stmt = select(Note).where(and_(*query_conditions)).order_by(Note.updated_at.desc())
                    result = await self.db_session.execute(stmt)
                    target_note = result.scalar_one_or_none()
                    
                elif session_note_id:
                    # 使用会话关联的笔记
                    stmt = select(Note).where(
                        Note.id == session_note_id,
                        Note.is_deleted == False
                    )
                    result = await self.db_session.execute(stmt)
                    target_note = result.scalar_one_or_none()
            except Exception as e:
                api_logger.error(f"查找目标笔记时出错: {str(e)}", exc_info=True)
                return {"error": f"查找笔记失败: {str(e)}"}
            
            if not target_note:
                return {"error": "未找到要编辑的笔记"}
            
            # 记录编辑前的状态
            original_content = target_note.content or ""
            original_title = target_note.title or ""
            target_note_id = target_note.id  # 提前保存ID，避免rollback后访问
            
            # 执行编辑操作
            new_content = original_content
            new_title = title if title is not None else original_title
            
            if edit_type == "replace":
                # 完全替换内容
                if content is not None:
                    new_content = content
                    
            elif edit_type == "append":
                # 追加内容
                if content is not None:
                    new_content = original_content + "\n" + content if original_content else content
                    
            elif edit_type == "prepend":
                # 前置内容
                if content is not None:
                    new_content = content + "\n" + original_content if original_content else content
                    
            elif edit_type == "insert":
                # 在指定位置插入内容
                if content is not None and insert_position:
                    lines = original_content.split('\n')
                    
                    if insert_position == "start":
                        new_content = content + "\n" + original_content if original_content else content
                    elif insert_position == "end":
                        new_content = original_content + "\n" + content if original_content else content
                    elif insert_position.startswith("after_line:"):
                        try:
                            line_num = int(insert_position.split(":")[1])
                            if 0 <= line_num <= len(lines):
                                lines.insert(line_num, content)
                                new_content = '\n'.join(lines)
                            else:
                                return {"error": f"行号 {line_num} 超出范围"}
                        except ValueError:
                            return {"error": "无效的行号格式"}
                    elif insert_position.startswith("before_line:"):
                        try:
                            line_num = int(insert_position.split(":")[1])
                            if 1 <= line_num <= len(lines) + 1:
                                lines.insert(line_num - 1, content)
                                new_content = '\n'.join(lines)
                            else:
                                return {"error": f"行号 {line_num} 超出范围"}
                        except ValueError:
                            return {"error": "无效的行号格式"}
                    else:
                        return {"error": "无效的插入位置格式"}
                        
            elif edit_type == "replace_lines":
                # 替换指定行范围
                if content is not None and start_line is not None:
                    lines = original_content.split('\n')
                    end_line_actual = end_line if end_line is not None else start_line
                    
                    if 1 <= start_line <= len(lines) and 1 <= end_line_actual <= len(lines):
                        # 替换指定行范围
                        new_lines = content.split('\n')
                        lines[start_line-1:end_line_actual] = new_lines
                        new_content = '\n'.join(lines)
                    else:
                        return {"error": f"行号范围 {start_line}-{end_line_actual} 超出范围"}
                        
            elif edit_type == "replace_text":
                # 替换指定文本
                if search_text is not None and replace_text is not None:
                    if search_text in original_content:
                        new_content = original_content.replace(search_text, replace_text)
                    else:
                        return {"error": f"未找到要替换的文本: {search_text}"}
                else:
                    return {"error": "replace_text 类型需要提供 search_text 和 replace_text 参数"}
            else:
                return {"error": f"不支持的编辑类型: {edit_type}"}
            
            # 更新笔记
            target_note.content = new_content
            target_note.title = new_title
            
            # 根据save_immediately参数决定是否立即保存
            if save_immediately:
                # 提交更改到数据库
                try:
                    await self.db_session.commit()
                    await self.db_session.refresh(target_note)
                    api_logger.info(f"笔记 {target_note_id} 编辑已立即保存到数据库")
                except Exception as e:
                    api_logger.error(f"提交数据库事务失败: {str(e)}", exc_info=True)
                    await self.db_session.rollback()
                    return {"error": f"保存笔记失败: {str(e)}"}
            else:
                # 预览模式：回滚数据库更改，但保留计算结果
                try:
                    await self.db_session.rollback()
                    api_logger.info(f"笔记 {target_note_id} 编辑为预览模式，未保存到数据库")
                except Exception as e:
                    api_logger.error(f"回滚数据库事务失败: {str(e)}", exc_info=True)
                    # 即使回滚失败，也继续返回预览结果
            
            # 计算变化统计
            original_lines = original_content.split('\n')
            new_lines = new_content.split('\n')
            
            result = {
                "success": True,
                "note_id": target_note_id,  # 使用提前保存的ID
                "title": new_title,
                "edit_type": edit_type,
                "content": new_content,
                "is_preview": not save_immediately,  # 标记是否为预览
                "changes": {
                    "original_length": len(original_content),
                    "new_length": len(new_content),
                    "original_lines": len(original_lines),
                    "new_lines": len(new_lines),
                    "title_changed": original_title != new_title
                },
                "updated_at": None if not save_immediately else (target_note.updated_at.isoformat() if hasattr(target_note, 'updated_at') and target_note.updated_at else None)
            }
            
            # 如果是小的更改，显示预览
            if len(new_content) < 1000:
                result["content_preview"] = new_content[:500] + "..." if len(new_content) > 500 else new_content
            
            api_logger.info(f"成功编辑笔记 {target_note_id}: {edit_type}")
            return result
            
        except Exception as e:
            api_logger.error(f"编辑笔记异常: {str(e)}", exc_info=True)
            try:
                await self.db_session.rollback()
                api_logger.info("已回滚数据库事务")
            except Exception as rollback_error:
                api_logger.error(f"回滚数据库事务失败: {str(rollback_error)}", exc_info=True)
            return {"error": f"编辑笔记失败: {str(e)}"}


# 工具服务类，管理所有可用工具
class ToolsService:
    """工具服务，管理所有可用的工具"""
    
    def __init__(self):
        """初始化工具服务"""
        self.tools = {}
        self.available_tools = {
            "tavily": TavilyTool,
            "serper": SerperTool,
            "note_reader": NoteReaderTool,
            "note_editor": NoteEditorTool
        }
        api_logger.info(f"工具服务初始化，可用工具: {list(self.available_tools.keys())}")
    
    def get_tool(self, tool_name: str, config: Dict[str, Any] = None) -> Any:
        """获取指定的工具实例"""
        if tool_name not in self.available_tools:
            api_logger.warning(f"请求的工具 {tool_name} 不可用")
            return None
        
        # 对于笔记相关工具，不使用缓存，因为每次调用可能有不同的用户ID和数据库会话
        if tool_name in ["note_reader", "note_editor"]:
            try:
                if config:
                    tool_instance = self.available_tools[tool_name](**config)
                else:
                    tool_instance = self.available_tools[tool_name]()
                
                api_logger.info(f"创建工具 {tool_name} 实例成功（不缓存）")
                return tool_instance
            except Exception as e:
                api_logger.error(f"创建工具 {tool_name} 实例失败: {str(e)}", exc_info=True)
                return None
        
        # 其他工具使用缓存机制
        cache_key = f"{tool_name}_{json.dumps(config, sort_keys=True) if config else 'default'}"
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