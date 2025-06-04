import { ref, nextTick } from 'vue';
import { parseAgentMessage, extractTextFromInteractionFlow } from '../utils/messageParser';
import type { ChatMessage, ContentChunk } from './useAgentChat';

export function useStreamingResponse() {
  // 处理工具状态更新
  const handleToolStatus = (toolStatus: any, currentMsg: ChatMessage) => {
    console.log('处理工具状态:', toolStatus);
    console.log('目标消息ID:', currentMsg.id, '当前contentChunks数量:', currentMsg.contentChunks?.length || 0);
    
    // 忽略 tools_completed 状态，这是一个总体完成状态，不需要显示
    if (toolStatus.type === 'tools_completed') {
      console.log('忽略 tools_completed 状态');
      return;
    }
    
    // 初始化contentChunks数组和lastTextLength
    if (!currentMsg.contentChunks) {
      currentMsg.contentChunks = [];
      currentMsg.lastTextLength = 0;
      currentMsg.baseTimestamp = new Date(); // 设置基准时间戳
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
            timestamp: new Date((currentMsg.baseTimestamp || new Date()).getTime() + (currentMsg.lastTextLength || 0)), // 基于基准时间和文本位置
            segmentIndex: currentMsg.contentChunks.filter(c => c.type === 'text').length
          };
          currentMsg.contentChunks.push(textChunk);
          console.log('工具调用前创建文本段:', newTextContent.substring(0, 50));
        }
        currentMsg.lastTextLength = currentTextLength;
      }
    }
    
    // 计算工具状态的时间戳，应该在当前文本位置之后
    const toolTimestamp = new Date((currentMsg.baseTimestamp || new Date()).getTime() + (currentMsg.content?.length || 0) + 1);
    
    // 添加或更新工具状态块
    const toolChunk: ContentChunk = {
      type: 'tool_status',
      tool_name: toolStatus.tool_name,
      status: toolStatus.status,
      tool_call_id: toolStatus.tool_call_id,
      timestamp: toolTimestamp,
      result: toolStatus.result || null,
      error: toolStatus.error || null
    };
    
    console.log('创建工具状态块:', {
      tool_name: toolChunk.tool_name,
      status: toolChunk.status,
      tool_call_id: toolChunk.tool_call_id,
      has_result: !!toolChunk.result,
      has_error: !!toolChunk.error
    });
    
    // 检查是否已经有相同tool_call_id的状态
    const existingIndex = currentMsg.contentChunks.findIndex(
      chunk => chunk.type === 'tool_status' && chunk.tool_call_id === toolStatus.tool_call_id
    );
    
    if (existingIndex !== -1) {
      // 更新现有的工具状态，保持原有时间戳
      const existingChunk = currentMsg.contentChunks[existingIndex];
      console.log('找到现有工具状态，更新从:', existingChunk.status, '到:', toolChunk.status);
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
    
    console.log('处理工具状态后，当前内容块数量:', currentMsg.contentChunks.length);
    console.log('当前所有工具状态块:', currentMsg.contentChunks.filter(c => c.type === 'tool_status').map(c => ({
      tool_name: c.tool_name,
      status: c.status,
      tool_call_id: c.tool_call_id
    })));
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
      
      // 检查是否有任何非文本块（包括reasoning和tool_status）
      const hasNonTextBlocks = currentMsg.contentChunks.some(chunk => 
        chunk.type === 'tool_status' || chunk.type === 'reasoning'
      );
      
      if (hasNonTextBlocks) {
        // 如果有非文本块，检查最后一个文本块的位置
        const lastTextChunk = [...currentMsg.contentChunks].reverse().find(chunk => chunk.type === 'text');
        const lastNonTextChunk = [...currentMsg.contentChunks].reverse().find(chunk => 
          chunk.type === 'tool_status' || chunk.type === 'reasoning'
        );
        
        // 如果最后一个文本块在最后一个非文本块之后，更新它；否则创建新的文本块
        if (lastTextChunk && lastNonTextChunk && lastTextChunk.timestamp > lastNonTextChunk.timestamp) {
          // 更新现有的最后文本块
          const allPreviousTextChunks = currentMsg.contentChunks.filter(chunk => 
            chunk.type === 'text' && chunk !== lastTextChunk
          );
          const previousTextLength = allPreviousTextChunks.reduce((sum, chunk) => sum + (chunk.content?.length || 0), 0);
          lastTextChunk.content = newResponse.substring(previousTextLength);
          console.log('更新非文本块后的文本块:', lastTextChunk.content.substring(0, 50));
        } else if (newTextContent.trim()) {
          // 创建新的文本段，时间戳要在最后一个块之后
          const textTimestamp = lastNonTextChunk 
            ? new Date(lastNonTextChunk.timestamp.getTime() + 1)
            : new Date((currentMsg.baseTimestamp || new Date()).getTime() + currentTextLength);
          
          const textChunk: ContentChunk = {
            type: 'text',
            content: newTextContent,
            timestamp: textTimestamp,
            segmentIndex: currentMsg.contentChunks.filter(c => c.type === 'text').length
          };
          currentMsg.contentChunks.push(textChunk);
          console.log('非文本块后创建新文本段:', newTextContent.substring(0, 50));
        }
        currentMsg.lastTextLength = currentTextLength;
      } else {
        // 没有非文本块，更新或创建第一个文本块
        let firstTextChunk = currentMsg.contentChunks.find(chunk => chunk.type === 'text');
        
        if (firstTextChunk) {
          // 更新现有文本块
          firstTextChunk.content = newResponse;
          console.log('更新现有文本块，长度:', newResponse.length);
        } else {
          // 初始化baseTimestamp如果不存在
          if (!currentMsg.baseTimestamp) {
            currentMsg.baseTimestamp = new Date();
          }
          
          // 创建第一个文本块
          firstTextChunk = {
            type: 'text',
            content: newResponse,
            timestamp: currentMsg.baseTimestamp,
            segmentIndex: 0
          };
          currentMsg.contentChunks.push(firstTextChunk);
          console.log('创建第一个文本块，长度:', newResponse.length);
        }
        currentMsg.lastTextLength = currentTextLength;
      }
    }
  };

  // 优化contentChunks结构，合并连续的文本块
  const optimizeContentChunks = (currentMsg: ChatMessage) => {
    if (!currentMsg.contentChunks || currentMsg.contentChunks.length === 0) return;
    
    console.log('优化前的contentChunks数量:', currentMsg.contentChunks.length);
    
    const optimizedChunks: ContentChunk[] = [];
    let currentTextChunk: ContentChunk | null = null;
    
    // 按时间戳排序
    const sortedChunks = getSortedContentChunks(currentMsg.contentChunks);
    
    for (const chunk of sortedChunks) {
      if (chunk.type === 'text') {
        if (currentTextChunk) {
          // 合并连续的文本块
          currentTextChunk.content += chunk.content || '';
        } else {
          // 开始新的文本块
          currentTextChunk = { ...chunk };
        }
      } else {
        // 遇到非文本块（reasoning或tool_status），先保存当前文本块（如果有）
        if (currentTextChunk) {
          optimizedChunks.push(currentTextChunk);
          currentTextChunk = null;
        }
        // 添加非文本块（reasoning或tool_status）
        optimizedChunks.push(chunk);
      }
    }
    
    // 添加最后的文本块（如果有）
    if (currentTextChunk) {
      optimizedChunks.push(currentTextChunk);
    }
    
    console.log('优化后的contentChunks数量:', optimizedChunks.length);
    currentMsg.contentChunks = optimizedChunks;
  };

  // 处理完整的agent响应（JSON结构）
  const handleCompleteResponse = (response: string, currentMsg: ChatMessage) => {
    console.log('handleCompleteResponse 被调用，响应长度:', response.length);
    
    // 如果消息已经有contentChunks结构，优化结构并更新内容
    if (currentMsg.contentChunks && currentMsg.contentChunks.length > 0) {
      console.log('消息已有contentChunks结构，优化结构并更新内容');
      
      // 更新最终的content内容
      currentMsg.content = response;
      
      // 优化contentChunks结构，合并连续的文本块
      optimizeContentChunks(currentMsg);
      
      return true; // 表示已处理
    }
    
    try {
      const parsedResponse = parseAgentMessage(response);
      
      if (typeof parsedResponse === 'object' && parsedResponse.type === 'agent_response') {
        console.log('处理完整JSON结构响应，interaction_flow长度:', parsedResponse.interaction_flow?.length || 0);
        
        // 提取纯文本内容用于显示
        const displayContent = extractTextFromInteractionFlow(parsedResponse.interaction_flow);
        console.log('提取的显示内容长度:', displayContent.length, '内容预览:', displayContent.substring(0, 100));
        
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
          } else if (segment.type === 'reasoning') {
            return {
              type: 'reasoning',
              content: segment.content,
              timestamp: new Date(segment.timestamp)
            };
          }
          // 对于其他未知类型，返回null并过滤掉
          return null;
        }).filter(chunk => chunk !== null) as ContentChunk[];
        
        // 更新消息内容 - 使用提取的完整文本内容
        currentMsg.content = displayContent;
        currentMsg.originalContent = response;
        currentMsg.contentChunks = contentChunks;
        
        console.log('转换后的contentChunks:', contentChunks.map(chunk => 
          `${chunk.type}:${chunk.tool_name || chunk.content?.substring(0, 20) || 'empty'}`
        ));
        console.log('最终设置的消息内容长度:', currentMsg.content.length);
        
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
      
      if (timeA === timeB) {
        // 优先级: reasoning > text > tool_status
        const typePriority = (type: string) => {
          if (type === 'reasoning') return 1;
          if (type === 'text') return 2;
          if (type === 'tool_status') return 3;
          return 4; // 其他类型
        };
        
        const priorityA = typePriority(a.type);
        const priorityB = typePriority(b.type);
        
        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }
        
        // 如果都是文本块，按segmentIndex排序 (这个逻辑可能需要重新审视，但暂时保留)
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