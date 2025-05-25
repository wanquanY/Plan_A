import { ref, computed } from 'vue';

// 工具调用状态类型定义
export interface ToolCallStatus {
  id: string;
  name: string;
  status: 'preparing' | 'executing' | 'completed' | 'error';
}

export function useToolCallsStatus() {
  // 工具调用状态列表
  const toolCalls = ref<ToolCallStatus[]>([]);

  // 计算属性：已完成的工具数量
  const completedCount = computed(() => {
    return toolCalls.value.filter((tool: ToolCallStatus) => tool.status === 'completed').length;
  });

  // 计算属性：是否有正在执行的工具
  const hasActiveTools = computed(() => {
    return toolCalls.value.some((tool: ToolCallStatus) => 
      tool.status === 'preparing' || tool.status === 'executing'
    );
  });

  // 计算属性：是否有错误的工具
  const hasErrorTools = computed(() => {
    return toolCalls.value.some((tool: ToolCallStatus) => tool.status === 'error');
  });

  // 添加工具调用
  const addToolCall = (id: string, name: string, status: ToolCallStatus['status'] = 'preparing') => {
    const existingIndex = toolCalls.value.findIndex((tool: ToolCallStatus) => tool.id === id);
    if (existingIndex === -1) {
      toolCalls.value.push({ id, name, status });
    } else {
      // 如果已存在，更新状态
      toolCalls.value[existingIndex].status = status;
    }
  };

  // 更新工具调用状态
  const updateToolCallStatus = (id: string, status: ToolCallStatus['status']) => {
    const tool = toolCalls.value.find((tool: ToolCallStatus) => tool.id === id);
    if (tool) {
      tool.status = status;
      
      // 移除自动清空逻辑，让工具状态保持显示
      // 用户可以手动清空或在新的对话开始时清空
    }
  };

  // 移除工具调用
  const removeToolCall = (id: string) => {
    const index = toolCalls.value.findIndex((tool: ToolCallStatus) => tool.id === id);
    if (index !== -1) {
      toolCalls.value.splice(index, 1);
    }
  };

  // 清空所有工具调用
  const clearToolCalls = () => {
    toolCalls.value = [];
  };

  // 处理工具状态更新（从流式响应中）
  const handleToolStatus = (toolStatus: any) => {
    console.log('处理工具状态更新:', toolStatus);
    const { type, tool_call_id, tool_name, status } = toolStatus;
    
    console.log('当前工具调用列表（处理前）:', toolCalls.value.map(t => `${t.name}(${t.status})`));
    
    if (type === 'tool_call_start' || type === 'tool_call_executing') {
      // 添加新的工具调用或更新为执行中
      if (type === 'tool_call_executing') {
        // 如果是执行中状态，先检查是否已存在，不存在则添加
        const existingTool = toolCalls.value.find(tool => tool.id === tool_call_id);
        if (!existingTool) {
          addToolCall(tool_call_id, tool_name, 'executing');
          console.log('添加新的执行中工具:', tool_call_id, tool_name);
        } else {
          updateToolCallStatus(tool_call_id, 'executing');
          console.log('更新工具状态为执行中:', tool_call_id);
        }
      } else {
        addToolCall(tool_call_id, tool_name, 'preparing');
        console.log('添加新的准备中工具:', tool_call_id, tool_name);
      }
    } else if (type === 'tool_call_completed') {
      // 更新工具调用状态为完成
      updateToolCallStatus(tool_call_id, 'completed');
      console.log('更新工具状态为完成:', tool_call_id);
    } else if (type === 'tool_call_error') {
      // 更新工具调用状态为错误
      updateToolCallStatus(tool_call_id, 'error');
      console.log('更新工具状态为错误:', tool_call_id);
    } else if (type === 'tools_completed') {
      // 所有工具处理完成，但不自动清空状态，让用户能看到完成的工具
      console.log('所有工具处理完成，保持状态显示');
    }
    
    console.log('当前工具调用状态（处理后）:', toolCalls.value.map(t => `${t.name}(${t.status})`));
    console.log('工具调用数组长度:', toolCalls.value.length);
  };

  // 获取特定状态的工具数量
  const getToolCountByStatus = (status: ToolCallStatus['status']) => {
    return toolCalls.value.filter((tool: ToolCallStatus) => tool.status === status).length;
  };

  // 获取工具调用详情
  const getToolCall = (id: string) => {
    return toolCalls.value.find((tool: ToolCallStatus) => tool.id === id);
  };

  // 批量更新工具状态
  const batchUpdateToolStatus = (updates: Array<{ id: string; status: ToolCallStatus['status'] }>) => {
    updates.forEach(({ id, status }) => {
      updateToolCallStatus(id, status);
    });
  };

  return {
    // 状态
    toolCalls,
    completedCount,
    hasActiveTools,
    hasErrorTools,
    
    // 方法
    addToolCall,
    updateToolCallStatus,
    removeToolCall,
    clearToolCalls,
    handleToolStatus,
    getToolCountByStatus,
    getToolCall,
    batchUpdateToolStatus
  };
} 