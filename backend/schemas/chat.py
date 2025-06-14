from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class ImageData(BaseModel):
    """图片数据模型"""
    url: str = Field(..., description="图片URL")
    name: Optional[str] = Field(None, description="图片文件名")
    size: Optional[int] = Field(None, description="图片大小")


class Message(BaseModel):
    """聊天消息"""
    content: str = Field(..., description="消息内容")
    reasoning_content: Optional[str] = Field(None, description="模型思考推理内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    content: str = Field(..., description="用户消息内容")
    images: Optional[List[ImageData]] = Field(default=[], description="用户上传的图片列表")
    stream: Optional[bool] = Field(False, description="是否启用流式响应")
    session_id: Optional[str] = Field(None, description="聊天会话ID，如果为空则创建新会话")
    agent_id: Optional[str] = Field(None, description="Agent ID，指定使用的AI助手")
    note_id: Optional[str] = Field(None, description="笔记ID，当创建新会话时关联到指定笔记")
    model: Optional[str] = Field(None, description="指定使用的模型，如果提供则覆盖Agent默认模型")


class AskAgainRequest(BaseModel):
    """重新提问请求"""
    message_index: Union[int, str] = Field(..., description="消息索引或消息ID")
    content: Optional[str] = Field(None, description="新的消息内容，如果为空则仅截断记忆")
    images: Optional[List[ImageData]] = Field(default=[], description="用户上传的图片列表")
    stream: Optional[bool] = Field(False, description="是否启用流式响应")
    agent_id: Optional[str] = Field(None, description="Agent ID，指定使用的AI助手")
    is_user_message: bool = Field(True, description="是否是用户消息，True表示编辑用户输入，False表示编辑AI回复")
    rerun: bool = Field(True, description="编辑用户消息时是否重新执行，True表示编辑后重新执行，False表示仅编辑不重新执行")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应"""
    message: Message = Field(..., description="AI生成的消息")
    usage: Dict[str, Any] = Field(None, description="token使用统计")
    session_id: Optional[str] = Field(None, description="聊天会话ID")


class ChatMemory(BaseModel):
    """聊天记忆类，用于保存会话上下文"""
    messages: List[Dict[str, str]] = []  # 包含角色和内容的消息列表
    
    def add_user_message(self, content: str):
        """添加用户消息到记忆中"""
        self.messages.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        """添加助手消息到记忆中"""
        self.messages.append({"role": "assistant", "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有消息"""
        return self.messages
    
    def clear(self):
        """清空记忆"""
        self.messages = []


class ChatStreamRequest(BaseModel):
    """流式聊天请求"""
    content: str = Field(..., description="用户消息内容")
    images: Optional[List[ImageData]] = Field(default=[], description="用户上传的图片列表")
    session_id: Optional[str] = Field(None, description="聊天会话ID，如果为空则创建新会话")
    agent_id: Optional[str] = Field(None, description="Agent ID，指定使用的AI助手")
    note_id: Optional[str] = Field(None, description="笔记ID，当创建新会话时关联到指定笔记")


class ChatMessageBase(BaseModel):
    """聊天消息基础模型"""
    role: str
    content: str


class ChatMessageCreate(ChatMessageBase):
    """创建聊天消息的请求模型"""
    session_id: str


class ChatMessageResponse(ChatMessageBase):
    """聊天消息响应模型"""
    id: str
    session_id: str
    created_at: Optional[datetime] = None
    tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    agent_id: Optional[str] = None
    agent_info: Optional[Dict[str, Any]] = None  # 包含agent名称、头像等信息
    tool_calls: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class ChatBase(BaseModel):
    """聊天会话基础模型"""
    title: Optional[str] = None


class ChatCreate(ChatBase):
    """创建聊天会话的请求模型"""
    title: Optional[str] = "新对话"
    note_id: Optional[str] = Field(None, description="要关联的笔记ID")


class ChatUpdate(ChatBase):
    """更新聊天会话的请求模型"""
    title: str


class ChatResponse(ChatBase):
    """聊天会话响应模型"""
    id: str
    user_id: str
    agent_id: Optional[str] = None
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: Optional[List[ChatMessageResponse]] = []
    is_active: bool

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """聊天会话列表响应模型"""
    id: str
    title: str
    agent_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int = 0
    last_message: Optional[str] = None

    class Config:
        from_attributes = True


class ToolCallInfo(BaseModel):
    """工具调用信息"""
    id: str
    tool_call_id: str
    tool_name: str
    function_name: str
    arguments: Optional[Dict[str, Any]]
    status: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True 