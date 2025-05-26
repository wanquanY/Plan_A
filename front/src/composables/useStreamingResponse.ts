import { ref, nextTick } from 'vue';
import { parseAgentMessage, extractTextFromInteractionFlow } from '../utils/messageParser';
import type { ChatMessage, ContentChunk } from './useAgentChat';

export function useStreamingResponse() {
  // 处理工具状态更新
  const handleToolStatus = (toolStatus: any, currentMsg: ChatMessage) => {
    console.log('处理工具状态:', toolStatus);
    
    // 初始化contentChunks数组和lastTextLength
    if (!currentMsg.contentChunks) {
      currentMsg.contentChunks = [];
      currentMsg.lastTextLength = 0;
    }
    
    // 当工具调用开始时，将当前文本内容分割
    if (toolStatus.status === 'preparing') {
      const currentTextLength = currentMsg.content ? currentMsg.content.length : 0;
      
      // 如果有新的文本内容，创建文本段
      if (currentTextLength > (currentMsg.lastTextLength || 0)) {
        const newTextContent = currentMsg.content.substring(currentMsg.lastTextLength || 0);
        if (newTextContent.trim()) {
          const textChunk: ContentChunk = {
            type: 'text',
            content: newTextContent,
            timestamp: new Date(Date.now() - 100), // 稍早于工具调用
            segmentIndex: currentMsg.contentChunks.filter(c => c.type === 'text').length
          };
          currentMsg.contentChunks.push(textChunk);
          console.log('工具调用前创建文本段:', newTextContent.substring(0, 50));
        }
        currentMsg.lastTextLength = currentTextLength;
      }
    }
    
    // 添加或更新工具状态块
    const toolChunk: ContentChunk = {
      type: 'tool_status',
      tool_name: toolStatus.tool_name,
      status: toolStatus.status,
      tool_call_id: toolStatus.tool_call_id,
      timestamp: new Date(),
      result: toolStatus.result || null,
      error: toolStatus.error || null
    };
    
    // 检查是否已经有相同tool_call_id的状态
    const existingIndex = currentMsg.contentChunks.findIndex(
      chunk => chunk.type === 'tool_status' && chunk.tool_call_id === toolStatus.tool_call_id
    );
    
    if (existingIndex !== -1) {
      // 更新现有的工具状态，保持原有时间戳
      const existingChunk = currentMsg.contentChunks[existingIndex];
      Object.assign(existingChunk, {
        ...toolChunk,
        timestamp: existingChunk.timestamp // 保持原有时间戳
      });
      console.log('更新现有工具状态:', toolChunk);
    } else {
      // 添加新的工具状态
      currentMsg.contentChunks.push(toolChunk);
      console.log('添加新工具状态到内容流:', toolChunk);
    }
    
    console.log('当前内容块数量:', currentMsg.contentChunks.length);
  };

  // 处理流式文本更新
  const handleStreamingText = (newResponse: string, currentMsg: ChatMessage) => {
    console.log('处理流式文本更新:', newResponse.length, '字符');
    
    // 初始化contentChunks数组和lastTextLength
    if (!currentMsg.contentChunks) {
      currentMsg.contentChunks = [];
      currentMsg.lastTextLength = 0;
    }
    
    // 更新消息的完整内容
    currentMsg.content = newResponse;
    
    // 检查是否有新的文本内容需要处理
    const currentTextLength = newResponse.length;
    
    // 如果文本长度增加了，需要处理新增的内容
    if (currentTextLength > (currentMsg.lastTextLength || 0)) {
      const newTextContent = newResponse.substring(currentMsg.lastTextLength || 0);
      
      // 检查是否有工具状态块
      const hasToolStatus = currentMsg.contentChunks.some(chunk => chunk.type === 'tool_status');
      
      if (hasToolStatus) {
        // 如果有工具状态，说明需要创建新的文本段
        if (newTextContent.trim()) {
          const textChunk: ContentChunk = {
            type: 'text',
            content: newTextContent,
            timestamp: new Date(), // 使用当前时间，确保在工具状态之后
            segmentIndex: currentMsg.contentChunks.filter(c => c.type === 'text').length
          };
          currentMsg.contentChunks.push(textChunk);
          console.log('工具调用后创建新文本段:', newTextContent.substring(0, 50));
        }
        currentMsg.lastTextLength = currentTextLength;
      } else {
        // 没有工具状态，更新或创建第一个文本块
        let firstTextChunk = currentMsg.contentChunks.find(chunk => chunk.type === 'text');
        
        if (firstTextChunk) {
          // 更新现有文本块
          firstTextChunk.content = newResponse;
        } else {
          // 创建第一个文本块
          firstTextChunk = {
            type: 'text',
            content: newResponse,
            timestamp: currentMsg.baseTimestamp || currentMsg.timestamp || new Date(),
            segmentIndex: 0
          };
          currentMsg.contentChunks.push(firstTextChunk);
        }
        currentMsg.lastTextLength = currentTextLength;
      }
    }
  };

  // 处理完整的agent响应（JSON结构）
  const handleCompleteResponse = (response: string, currentMsg: ChatMessage) => {
    try {
      const parsedResponse = parseAgentMessage(response);
      
      if (typeof parsedResponse === 'object' && parsedResponse.type === 'agent_response') {
        console.log('处理完整JSON结构响应，interaction_flow长度:', parsedResponse.interaction_flow?.length || 0);
        
        // 提取纯文本内容用于显示
        const displayContent = extractTextFromInteractionFlow(parsedResponse.interaction_flow);
        
        // 将interaction_flow转换为contentChunks格式，保持时间顺序
        const contentChunks: ContentChunk[] = parsedResponse.interaction_flow.map(segment => {
          if (segment.type === 'text') {
            return {
              type: 'text',
              content: segment.content,
              timestamp: new Date(segment.timestamp)
            };
          } else if (segment.type === 'tool_call') {
            return {
              type: 'tool_status',
              tool_name: segment.name,
              status: segment.status,
              tool_call_id: segment.id,
              timestamp: new Date(segment.started_at),
              result: segment.result,
              error: segment.error
            };
          }
          return segment as ContentChunk;
        });
        
        // 更新消息内容
        currentMsg.content = displayContent;
        currentMsg.originalContent = response;
        currentMsg.contentChunks = contentChunks;
        
        console.log('转换后的contentChunks:', contentChunks.map(chunk => 
          `${chunk.type}:${chunk.tool_name || chunk.content?.substring(0, 20) || 'empty'}`
        ));
        
        return true; // 表示处理了完整响应
      }
    } catch (error: any) {
      console.log('解析agent响应失败，使用流式处理:', error.message);
    }
    
    return false; // 表示需要流式处理
  };

  // 按时间顺序排序内容块
  const getSortedContentChunks = (chunks: ContentChunk[]) => {
    if (!chunks || chunks.length === 0) return [];
    
    // 创建副本避免修改原数组
    const sortedChunks = [...chunks];
    
    // 严格按时间戳排序
    sortedChunks.sort((a, b) => {
      const timeA = new Date(a.timestamp || 0).getTime();
      const timeB = new Date(b.timestamp || 0).getTime();
      
      // 如果时间戳相同，文本块优先于工具状态块
      if (timeA === timeB) {
        if (a.type === 'text' && b.type === 'tool_status') return -1;
        if (a.type === 'tool_status' && b.type === 'text') return 1;
        
        // 如果都是文本块，按segmentIndex排序
        if (a.type === 'text' && b.type === 'text') {
          return (a.segmentIndex || 0) - (b.segmentIndex || 0);
        }
        
        return 0;
      }
      
      return timeA - timeB;
    });
    
    console.log('排序后的内容块:', sortedChunks.map((chunk, index) => ({
      index,
      type: chunk.type,
      tool_name: chunk.tool_name,
      content_preview: chunk.content?.substring(0, 30) || '',
      timestamp: chunk.timestamp,
      segmentIndex: chunk.segmentIndex
    })));
    
    return sortedChunks;
  };

  return {
    handleToolStatus,
    handleStreamingText,
    handleCompleteResponse,
    getSortedContentChunks
  };
} 