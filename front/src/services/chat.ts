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
    };
    full_content: string;
    conversation_id: number;
    done: boolean;
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

// 流式回调类型
export type StreamCallback = (response: any, isComplete: boolean, conversationId: number) => void;

// 与Agent聊天的请求
export interface ChatRequest {
  agent_id: number;
  content: string;
  conversation_id?: number;
  note_id?: number;
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

// 与Agent聊天
const chatWithAgent = async (request: ChatRequest, onProgress: StreamCallback): Promise<AbortController> => {
  // 创建一个AbortController，用于取消请求
  const controller = new AbortController();
  
  console.log('初始化聊天请求:', {
    conversation_id: request.conversation_id,
    agent_id: request.agent_id,
    content_length: request.content.length,
    note_id: request.note_id
  });
  
  (async () => {
    try {
      // 获取token
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('需要登录');
      }
      
      // 构造请求体
      const body = JSON.stringify({
        content: request.content,
        conversation_id: request.conversation_id ?? 0,
        agent_id: request.agent_id,
        note_id: request.note_id
      });
      
      // 打印完整请求信息用于调试
      console.log('发送聊天请求完整信息:', {
        content_length: request.content.length,
        conversation_id: request.conversation_id ?? 0,
        agent_id: request.agent_id,
        note_id: request.note_id || '未提供'
      });
      
      // 发送请求
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat/chat/stream`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body,
        signal: controller.signal
      });
      
      // 检查响应是否成功
      if (!response.ok) {
        const errorText = await response.text();
        onProgress(`服务器返回错误: ${response.status} - ${errorText}`, true, request.conversation_id || 0);
        return;
      }
      
      // 确保响应体存在
      if (!response.body) {
        throw new Error('响应体为空');
      }
      
      // 处理文本流
      const finalId = await processTextStream(response.body.getReader(), onProgress, request.conversation_id);
      
      // 如果获取到了新的会话ID，刷新会话列表
      if (finalId && finalId !== request.conversation_id) {
        console.log(`聊天完成，新会话ID: ${finalId}，自动刷新会话列表`);
        try {
          // 使用全局刷新方法更新侧边栏
          if (typeof window !== 'undefined' && window.refreshSessions) {
            window.refreshSessions();
          } else {
            // 如果全局方法不可用，则使用本地getSessions只获取数据
            await getSessions();
          }
          console.log('会话列表已刷新');
        } catch (error) {
          console.error('刷新会话列表失败:', error);
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('用户取消了请求');
        onProgress('用户取消了请求', true, request.conversation_id || 0);
      } else {
        console.error('处理聊天请求时出错:', error);
        onProgress(`发生错误: ${error.message}`, true, request.conversation_id || 0);
      }
    }
  })();
  
  return controller;
};

// 处理流式文本数据
const processTextStream = async (
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callback: StreamCallback,
  conversationId: number | null = null
): Promise<number> => {
  let buffer = '';
  let currentConversationId = conversationId;
  let previousContent = '';
  let finalContent = ''; // 保存最终内容
  let finalResponse: any = null; // 保存最终响应对象

  try {
    const decoder = new TextDecoder();
    
    // 读取数据流
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        console.log('流读取完成');
        // 最后一次回调，确保UI知道流已结束
        // 使用最终累积的响应对象
        if (finalResponse) {
          // 确保设置done=true
          if (finalResponse.data && finalResponse.data.data) {
            finalResponse.data.data.done = true;
          }
          callback(finalResponse, true, currentConversationId || 0);
        } else {
          // 如果没有最终响应对象，创建一个基本的响应
          const basicResponse = {
            data: {
              data: {
                full_content: finalContent,
                done: true,
                conversation_id: currentConversationId || 0
              }
            }
          };
          callback(basicResponse, true, currentConversationId || 0);
        }
        return currentConversationId || 0;
      }
      
      // 将二进制数据解码为文本
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        console.log(`收到${value.length}字节数据`);
        
        // 添加到缓冲区
        buffer += chunk;
        
        // 按行处理数据
        const lines = buffer.split('\n');
        // 保留最后一行，可能是不完整的
        buffer = lines.pop() || '';
        
        // 处理完整的行
        for (const line of lines) {
          if (line.trim()) {
            processSSELine(line.trim());
          }
        }
      }
    }
  } catch (error: any) {
    console.error('处理流式数据时出错:', error);
    const errorResponse = {
      data: {
        data: {
          full_content: `读取响应流时出错: ${error.message}`,
          done: true,
          conversation_id: currentConversationId || 0
        }
      }
    };
    callback(errorResponse, true, currentConversationId || 0);
    return currentConversationId || 0;
  }
  
  // 处理SSE行数据
  function processSSELine(line: string) {
    try {
      // 检查是否是SSE格式
      let jsonStr = line;
      if (line.startsWith('data: ')) {
        jsonStr = line.substring(6).trim();
      }
      
      console.log('准备解析JSON:', jsonStr);
      const data = JSON.parse(jsonStr);
      
      if (data.code !== 200) {
        console.error('服务器返回错误:', data.msg);
        return;
      }
      
      // 创建包含完整响应的对象
      const response = { data: data };
      
      // 保存最终响应
      finalResponse = response;
      
      // 提取消息内容和会话ID
      if (data.data) {
        // 优先使用full_content字段
        const content = data.data.full_content || 
                        (data.data.message ? data.data.message.content : '') || '';
        
        // 判断是否完成
        const isComplete = data.data.done || false;
        
        // 更新会话ID，确保不为0
        if (data.data.conversation_id && data.data.conversation_id !== 0) {
          currentConversationId = data.data.conversation_id;
          console.log(`更新会话ID: ${currentConversationId}`);
        }
        
        // 如果内容非空，则更新最终内容
        if (content) {
          finalContent = content;
        }
        
        // 记录agent信息（如果存在）
        if (data.data.agent_info) {
          console.log('接收到agent信息:', data.data.agent_info);
        }
        
        console.log(`处理流式数据: 内容长度=${content.length}, 是否完成=${isComplete}, 会话ID=${currentConversationId || 'null'}`);
        
        // 确保有效会话ID
        const idToSend = currentConversationId ?? conversationId ?? 0;
        
        // 回调UI更新
        callback(response, isComplete, idToSend);
        
        // 保存上一个内容以防下一次回调为空
        if (content) {
          previousContent = content;
        }
      }
    } catch (e) {
      console.error('解析JSON失败:', e, '原始数据:', line);
    }
  }
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

const chatService = {
  streamChat: chatWithAgent,
  getSessions,
  getSessionDetail,
  createSession,
  updateSession,
  deleteSession
};

export default chatService; 