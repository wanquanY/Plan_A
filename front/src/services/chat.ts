import apiClient from './api';

// 为Window全局对象添加refreshSessions方法类型声明
declare global {
  interface Window {
    refreshSessions?: () => Promise<void>;
    sessionData?: any;
  }
}

// 流式响应消息格式
export interface ChatStreamMessage {
  code: number;
  msg: string;
  data: {
    message: {
      content: string;
      reasoning_content?: string;
    };
    full_content: string;
    session_id: number;
    done: boolean;
    tool_status?: {
      type: string;
      tool_call_id?: string;
      tool_name?: string;
      status: string;
    };
    agent_info?: {
      id: number;
      name: string;
      avatar_url?: string;
      model?: string;
    };
  };
  errors: any;
  timestamp: string;
  request_id: string;
}

// 流式回调类型 - 修改为支持思考内容
export type StreamCallback = (
  response: any, 
  isComplete: boolean, 
  sessionId: number, 
  toolStatus?: any,
  reasoningContent?: string
) => void;

// 与Agent聊天的请求
export interface ChatRequest {
  agent_id: number;
  content: string;
  images?: Array<{
    url: string;
    name?: string;
    size?: number;
  }>;
  session_id?: number;
  note_id?: number;
  model?: string;
}

// 会话列表接口
export interface ChatSession {
  id: number;
  title: string;
  agent_id: number;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message: string;
}

// 聊天消息接口
export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  session_id: number;
  created_at: string;
  agent_id?: number;
  agent_info?: {
    id: number;
    name: string;
    avatar_url?: string;
    model?: string;
  };
  tool_calls?: any[];
}

// 添加分页响应模型
export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// 更新会话列表响应模型
interface SessionsResponse {
  code: number;
  msg: string;
  data: PaginationResponse<ChatSession>;
  errors: any;
  timestamp: string;
  request_id: string;
}

// 会话详情接口
export interface ChatSessionDetail {
  id: number;
  title: string;
  agent_id: number;
  created_at: string;
  updated_at: string;
  messages: {
    id: number;
    role: string;
    content: string;
    timestamp: string;
    created_at?: string;
    tokens?: number;
    agent_id?: number;
    agent_info?: {
      id: number;
      name: string;
      avatar_url?: string;
      model?: string;
    };
    // 工具调用相关字段 - 新的数据结构
    tool_calls_data?: Array<{
      id: string;
      name: string;
      arguments: any;
      status: string;
      result?: any;
      error?: string;
      started_at?: string;
      completed_at?: string;
    }>;
  }[];
}

// 会话详情响应
interface SessionDetailResponse {
  code: number;
  msg: string;
  data: ChatSessionDetail;
  errors: any;
  timestamp: string;
  request_id: string;
}

// 编辑消息请求接口
export interface EditMessageRequest {
  message_index: number;
  content?: string;
  stream?: boolean;
  agent_id?: number;
  is_user_message: boolean;
  rerun: boolean;
}

// 编辑消息响应接口
export interface EditMessageResponse {
  success: boolean;
  messages_removed?: number;
  db_messages_deleted?: number;
  edited: boolean;
  rerun: boolean;
  message?: {
    content: string;
  };
  session_id?: number;
  agent_info?: {
    id: number;
    name: string;
    avatar_url?: string;
    model?: string;
  };
}

// 与Agent聊天
const chatWithAgent = async (request: ChatRequest, onProgress: StreamCallback): Promise<AbortController> => {
  // 创建一个AbortController，用于取消请求
  const controller = new AbortController();
  
  console.log('初始化聊天请求:', {
    session_id: request.session_id,
    agent_id: request.agent_id,
    content_length: request.content.length,
    note_id: request.note_id,
    images_count: request.images?.length || 0
  });
  
  (async () => {
    try {
      // 获取token
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('未找到认证令牌');
      }
      
      // 获取API基础URL
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:1314/api/v1';
      const streamUrl = `${apiBaseUrl}/chat/stream`;
      
      console.log('发送流式聊天请求到:', streamUrl);
      
      // 构建请求体
      const requestBody = {
        content: request.content,
        agent_id: request.agent_id,
        session_id: request.session_id,
        images: request.images,
        note_id: request.note_id,
        model: request.model
      };
      
      console.log('发送的请求体:', JSON.stringify(requestBody, null, 2));
      console.log('🔍 关键字段检查:', {
        'note_id值': request.note_id,
        'note_id类型': typeof request.note_id,
        'session_id值': request.session_id,
        'session_id类型': typeof request.session_id,
        'agent_id值': request.agent_id
      });
      
      // 发送请求
      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        onProgress(`服务器返回错误: ${response.status} - ${errorText}`, true, request.session_id || 0);
        return;
      }
      
      if (!response.body) {
        throw new Error('响应体为空');
      }
      
      const finalId = await processTextStream(response.body.getReader(), onProgress, request.session_id);
      console.log('流式聊天完成，最终session_id:', finalId);
      
    } catch (error: any) {
      if (error.name === 'AbortError') {
        onProgress('用户取消了聊天请求', true, request.session_id || 0);
        return;
      }
      onProgress(`聊天失败: ${error.message}`, true, request.session_id || 0);
    }
  })();
  
  return controller;
};

// 处理流式文本数据
const processTextStream = async (
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callback: StreamCallback,
  sessionId: number | null = null
): Promise<number> => {
  const decoder = new TextDecoder();
  let buffer = '';
  let currentSessionId = sessionId || 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        // 处理最后的缓冲区内容
        if (buffer.trim()) {
          try {
            processSSELine(buffer.trim());
          } catch (e) {
            console.warn('处理最后缓冲区数据失败:', e);
          }
        }
        console.log('流式传输完成，最终session_id:', currentSessionId);
        break;
      }
      
      // 将新数据添加到缓冲区
      buffer += decoder.decode(value, { stream: true });
        
      // 按行处理数据 - 修复换行符分割问题
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 保留最后一行（可能不完整）
        
      for (const line of lines) {
        try {
          processSSELine(line.trim());
        } catch (e) {
          console.warn('处理SSE行失败:', e, '行内容:', line);
          continue;
        }
      }
    }
  } catch (error) {
    console.error('读取流时出错:', error);
    throw error;
  }
  
  function processSSELine(line: string) {
    if (!line || line === 'data: [DONE]') return;
    
    // 移除 'data: ' 前缀
    if (line.startsWith('data: ')) {
      line = line.substring(6);
    } else {
      // 如果没有 'data: ' 前缀，可能是不完整的行，直接跳过
      return;
    }
      
    try {
      const data = JSON.parse(line);
      
      // 处理标准的API响应格式
      if (data.code === 200 && data.data) {
        const responseData = data.data;
        
        if (responseData.session_id) {
          currentSessionId = responseData.session_id;
        }
        
        // 🔧 修复：首先处理工具状态信息
        if (responseData.tool_status) {
          console.log('🔧 检测到工具状态信息，立即传递:', responseData.tool_status);
          // 立即传递工具状态信息，即使没有文本内容
          callback(data, responseData.done || false, currentSessionId, responseData.tool_status);
        }
        
        // 然后处理文本消息
        if (responseData.message) {
          const content = responseData.message.content || '';
          const reasoning = responseData.message.reasoning_content || null;
          
          console.log('processSSELine 传递数据:', {
            content_length: content.length,
            full_content_length: responseData.full_content?.length || 0,
            reasoning_content_length: reasoning?.length || 0,
            done: responseData.done,
            session_id: responseData.session_id,
            has_tool_status: !!responseData.tool_status
          });
          
          // 调用回调函数，传递完整的响应数据而不仅仅是content字符串
          // 这样前端可以访问 full_content 字段进行正确的累积显示
          // 🔧 修复：如果已经处理了工具状态，这里不要重复传递工具状态
          callback(data, responseData.done || false, currentSessionId, responseData.tool_status ? null : null, reasoning);
        }
        
        // 如果是完成状态
        if (responseData.done) {
          callback(data, true, currentSessionId);
        }
      }
      
      // 保持对旧格式的兼容性
      else if (data.type === 'session_info') {
        // 从session_info中获取session_id
        if (data.session_id) {
          currentSessionId = data.session_id;
          console.log('获取到session_id:', currentSessionId);
        }
        return;
      } else if (data.type === 'content') {
        const content = data.content || '';
        const reasoning = data.reasoning || null;
        
        // 调用回调函数，传递内容和推理信息
        callback(content, false, currentSessionId, null, reasoning);
      } else if (data.type === 'tool_status') {
        // 处理工具状态更新
        callback('', false, currentSessionId, data);
      } else if (data.type === 'complete') {
        // 流式传输完成
        if (data.session_id) {
          currentSessionId = data.session_id;
        }
        callback('', true, currentSessionId);
      } else if (data.type === 'error') {
        // 错误信息
        if (data.session_id) {
          currentSessionId = data.session_id;
        }
        callback(data.error || '发生未知错误', true, currentSessionId);
      }
      
    } catch (e) {
      console.warn('解析JSON失败:', e, '原始数据:', line);
    }
  }
  
  return currentSessionId;
};

// 获取聊天会话列表
const getSessions = async (page: number = 1, pageSize: number = 10): Promise<{sessions: ChatSession[], total: number, pages: number}> => {
  try {
    console.log(`调用getSessions API请求会话列表, page=${page}, pageSize=${pageSize}`);
    const response = await apiClient.get('/chat/sessions', {
      params: {
        page,
        page_size: pageSize
      }
    });
    console.log('getSessions API响应:', response.status, response.data ? `code=${response.data.code}` : '无data');
    
    if (response.data && response.data.code === 200) {
      const paginationData = response.data.data;
      console.log(`getSessions API成功，获取到${paginationData.items ? paginationData.items.length : 0}条会话，总数${paginationData.total}`);
      return {
        sessions: paginationData.items || [],
        total: paginationData.total || 0,
        pages: paginationData.pages || 1
      };
    }
    
    throw new Error(response.data.msg || '获取会话列表失败');
  } catch (error) {
    console.error('获取会话列表失败:', error);
    return {
      sessions: [],
      total: 0,
      pages: 1
    };
  }
};

// 获取聊天会话详情
const getSessionDetail = async (sessionId: number): Promise<ChatSessionDetail | null> => {
  try {
    // 获取token
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('需要登录');
    }

    const response = await apiClient.get(`/chat/sessions/${sessionId}`);

    if (response.data && response.data.code === 200) {
      return response.data.data;
    }
    
    throw new Error(response.data.msg || '获取会话详情失败');
  } catch (error) {
    console.error('获取会话详情失败:', error);
    return null;
  }
};

// 根据会话ID获取历史Agent记录（用于笔记关联的对话历史）
const getSessionAgentHistory = async (sessionId: number): Promise<Array<{user: string, agent: string, userMessageId?: number, agentMessageId?: number}> | null> => {
  try {
    if (!sessionId) {
      console.log('没有会话ID，返回空历史记录');
      return null;
    }

    console.log(`获取会话 ${sessionId} 的Agent历史记录`);
    
    const sessionDetail = await getSessionDetail(sessionId);
    if (!sessionDetail || !sessionDetail.messages) {
      console.log(`会话 ${sessionId} 没有消息记录`);
      return null;
    }

    // 将消息按照用户-AI的配对方式组织，同时处理工具调用
    const agentHistory: Array<{user: string, agent: string, userMessageId?: number, agentMessageId?: number}> = [];
    const messages = sessionDetail.messages.sort((a, b) => 
      new Date(a.created_at || a.timestamp).getTime() - new Date(b.created_at || b.timestamp).getTime()
    );
    
    console.log(`处理 ${messages.length} 条消息，包含工具调用`);
    
    let currentUserMessage = '';
    let currentUserMessageId: number | undefined;
    let currentAgentMessage = '';
    let currentAgentMessageId: number | undefined;
    
    for (let i = 0; i < messages.length; i++) {
      const message = messages[i];
      console.log(`处理消息 ${i}: role=${message.role}, has_tools=${!!message.tool_calls_data}, content="${message.content.substring(0, 50)}..."`);
      
      if (message.role === 'user') {
        // 如果已经有一对完整的对话，先保存它
        if (currentUserMessage && currentAgentMessage) {
          agentHistory.push({
            user: currentUserMessage,
            agent: currentAgentMessage,
            userMessageId: currentUserMessageId,
            agentMessageId: currentAgentMessageId
          });
          
          console.log(`保存对话对: user="${currentUserMessage.substring(0, 20)}...", agent="${currentAgentMessage.substring(0, 20)}..."`);
          
          // 重置状态
          currentUserMessage = '';
          currentUserMessageId = undefined;
          currentAgentMessage = '';
          currentAgentMessageId = undefined;
        }
        
        currentUserMessage = message.content;
        currentUserMessageId = message.id;
        console.log(`设置用户消息: "${currentUserMessage.substring(0, 30)}..."`);
        
      } else if (message.role === 'assistant') {
        // 处理AI助手消息
        currentAgentMessage = message.content;
        currentAgentMessageId = message.id;
        console.log(`设置AI消息: "${currentAgentMessage.substring(0, 30)}..."`);
        
        // 如果有用户消息，立即配对保存
        if (currentUserMessage) {
          agentHistory.push({
            user: currentUserMessage,
            agent: currentAgentMessage,
            userMessageId: currentUserMessageId,
            agentMessageId: currentAgentMessageId
          });
          
          console.log(`立即保存对话对: user="${currentUserMessage.substring(0, 20)}...", agent="${currentAgentMessage.substring(0, 20)}..."`);
          
          // 重置状态
          currentUserMessage = '';
          currentUserMessageId = undefined;
          currentAgentMessage = '';
          currentAgentMessageId = undefined;
        }
      }
    }
    
    // 处理剩余的消息
    if (currentUserMessage && currentAgentMessage) {
      agentHistory.push({
        user: currentUserMessage,
        agent: currentAgentMessage,
        userMessageId: currentUserMessageId,
        agentMessageId: currentAgentMessageId
      });
      
      console.log(`最终保存对话对: user="${currentUserMessage.substring(0, 20)}...", agent="${currentAgentMessage.substring(0, 20)}..."`);
    }

    console.log(`会话 ${sessionId} 的Agent历史记录处理完成，共 ${agentHistory.length} 对对话`);
    return agentHistory;
  } catch (error) {
    console.error(`获取会话 ${sessionId} 的历史记录失败:`, error);
    return null;
  }
};

// 创建新的会话
const createSession = async (title: string = '新会话'): Promise<ChatSession | null> => {
  try {
    const response = await apiClient.post<any>('/chat/sessions', { title });
    if (response.data.code === 200) {
      return response.data.data;
    } else {
      console.error('创建会话失败:', response.data.msg);
      return null;
    }
  } catch (error) {
    console.error('创建会话请求出错:', error);
    return null;
  }
};

// 更新会话信息
const updateSession = async (sessionId: number, title: string): Promise<boolean> => {
  try {
    const response = await apiClient.put(`/chat/sessions/${sessionId}`, { title });
    if (response.data.code === 200) {
      console.log('会话更新成功:', response.data.data);
      return true;
    } else {
      console.error('更新会话失败:', response.data.msg);
      return false;
    }
  } catch (error) {
    console.error('更新会话请求出错:', error);
    return false;
  }
};

// 删除会话
const deleteSession = async (sessionId: number): Promise<boolean> => {
  try {
    const response = await apiClient.delete(`/chat/sessions/${sessionId}`);
    if (response.data.code === 200) {
      console.log('会话删除成功:', response.data.data);
      return true;
    } else {
      console.error('删除会话失败:', response.data.msg);
      return false;
    }
  } catch (error) {
    console.error(`删除会话 ${sessionId} 失败:`, error);
    return false;
  }
};

// 在全局对象上添加刷新会话列表的方法，允许其他组件和服务调用
if (typeof window !== 'undefined') {
  window.refreshSessions = async () => {
    try {
      console.log('全局刷新会话列表方法被调用');
      const { sessions: sessionsData } = await getSessions();
      if (sessionsData) {
        // 存储会话数据供其他组件使用
        window.sessionData = sessionsData;
        console.log('会话列表已全局刷新，当前数量:', sessionsData.length);
      }
    } catch (error) {
      console.error('全局刷新会话列表失败:', error);
    }
  };
}

// 编辑消息并可选择重新执行
const editMessage = async (
  sessionId: number, 
  request: EditMessageRequest, 
  onProgress?: StreamCallback
): Promise<EditMessageResponse | AbortController> => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('未找到认证令牌');
    }

    if (request.stream && onProgress) {
      // 流式编辑
      const controller = new AbortController();
      
      (async () => {
        try {
          // 获取API基础URL
          const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:1314/api/v1';
          const editUrl = `${apiBaseUrl}/chat/ask-again/${sessionId}`;
          
          console.log('发送流式编辑请求到:', editUrl);
          
          const response = await fetch(editUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(request),
            signal: controller.signal
          });

          if (!response.ok) {
            const errorText = await response.text();
            onProgress(`服务器返回错误: ${response.status} - ${errorText}`, true, sessionId);
            return;
          }

          if (!response.body) {
            throw new Error('响应体为空');
          }

          await processTextStream(response.body.getReader(), onProgress, sessionId);
          
        } catch (error: any) {
          if (error.name === 'AbortError') {
            onProgress('用户取消了编辑请求', true, sessionId);
            return;
          }
          onProgress(`编辑失败: ${error.message}`, true, sessionId);
        }
      })();

      return controller;
    } else {
      // 非流式编辑
      const response = await apiClient.post(`/chat/ask-again/${sessionId}`, request);
      return response.data.data;
    }
  } catch (error) {
    console.error('编辑消息失败:', error);
    throw error;
  }
};

// 强制停止并保存响应
const stopAndSaveResponse = async (sessionId: number, currentContent: string, userContent: string, agentId?: number): Promise<boolean> => {
  try {
    await apiClient.post(`/chat/${sessionId}/stop`, {
      session_id: sessionId,
      current_content: currentContent,
      user_content: userContent,
      agent_id: agentId
    });

    await apiClient.post(`/chat/${sessionId}/save`, {
      session_id: sessionId,
      current_content: currentContent
    });
    
      return true;
  } catch (error) {
    console.error('停止并保存响应失败:', error);
    return false;
  }
};

const chatService = {
  streamChat: chatWithAgent,
  getSessions,
  getSessionDetail,
  getSessionAgentHistory,
  createSession,
  updateSession,
  deleteSession,
  editMessage,
  stopAndSaveResponse
};

export default chatService; 