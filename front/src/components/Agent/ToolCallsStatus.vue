<template>
  <div v-if="toolCalls.length > 0" class="tool-calls-status">
    <div class="tool-calls-header">
      <span class="tool-icon">🔧</span>
      <span class="tool-title">正在使用工具...</span>
      <span class="tool-count">({{ completedCount }}/{{ toolCalls.length }})</span>
    </div>
    <div class="tool-calls-list">
      <div 
        v-for="toolCall in toolCalls" 
        :key="toolCall.id"
        class="tool-call-item"
        :class="toolCall.status"
      >
        <div class="tool-call-info">
          <span class="tool-name">{{ getToolDisplayName(toolCall.name) }}</span>
          <span class="tool-status">{{ getToolStatusText(toolCall.status) }}</span>
        </div>
        <div class="tool-call-progress">
          <div 
            class="progress-bar" 
            :class="toolCall.status"
            :style="{ width: getProgressWidth(toolCall.status) }"
          ></div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 保留少量调试信息，但样式更低调 -->
  <div v-else-if="false" style="padding: 4px; background: #f9f9f9; border-radius: 4px; margin: 4px 0; font-size: 11px; color: #999; opacity: 0.7;">
    调试: 工具调用数量 = {{ toolCalls.length }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ToolCallStatus } from '../../composables/useToolCallsStatus';

// Props
const props = defineProps<{
  toolCalls: ToolCallStatus[];
}>();

// 计算已完成的工具数量
const completedCount = computed(() => {
  return props.toolCalls.filter(tool => tool.status === 'completed').length;
});

// 获取工具显示名称
const getToolDisplayName = (toolName: string): string => {
  const toolNameMap: Record<string, string> = {
    'tavily_search': 'Tavily 搜索',
    'tavily_extract': 'Tavily 网页提取',
    'serper_search': 'Serper 搜索',
    'serper_news': 'Serper 新闻',
    'serper_scrape': 'Serper 网页抓取',
    'web_search': '网页搜索',
    'web_scrape': '网页抓取',
    'file_read': '文件读取',
    'file_write': '文件写入',
    'code_execute': '代码执行'
  };
  return toolNameMap[toolName] || toolName;
};

// 获取工具状态文本
const getToolStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    'preparing': '准备中...',
    'executing': '执行中...',
    'completed': '已完成',
    'error': '执行失败'
  };
  return statusMap[status] || status;
};

// 获取进度条宽度
const getProgressWidth = (status: string): string => {
  const widthMap: Record<string, string> = {
    'preparing': '30%',
    'executing': '70%',
    'completed': '100%',
    'error': '100%'
  };
  return widthMap[status] || '0%';
};
</script>

<style scoped>
.tool-calls-status {
  margin: 12px 0;
  padding: 16px;
  background: linear-gradient(135deg, #f6f8ff 0%, #e8f4fd 100%);
  border: 1px solid #d1e7ff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.tool-calls-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-weight: 500;
  color: #1677ff;
  font-size: 14px;
}

.tool-icon {
  font-size: 18px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tool-title {
  flex: 1;
}

.tool-count {
  font-size: 12px;
  color: #666;
  background: rgba(22, 119, 255, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
}

.tool-calls-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-call-item {
  background: white;
  border-radius: 8px;
  padding: 12px 16px;
  border-left: 4px solid #d9d9d9;
  transition: all 0.3s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.tool-call-item.preparing {
  border-left-color: #faad14;
  background: linear-gradient(135deg, #fffbe6 0%, #fff7e6 100%);
}

.tool-call-item.executing {
  border-left-color: #1677ff;
  background: linear-gradient(135deg, #f6f8ff 0%, #e6f7ff 100%);
  animation: pulse 2s ease-in-out infinite;
}

.tool-call-item.completed {
  border-left-color: #52c41a;
  background: linear-gradient(135deg, #f6ffed 0%, #f0f9e8 100%);
}

.tool-call-item.error {
  border-left-color: #ff4d4f;
  background: linear-gradient(135deg, #fff2f0 0%, #ffece8 100%);
}

@keyframes pulse {
  0%, 100% { 
    transform: scale(1);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }
  50% { 
    transform: scale(1.02);
    box-shadow: 0 2px 8px rgba(22, 119, 255, 0.15);
  }
}

.tool-call-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tool-name {
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

.tool-status {
  font-size: 12px;
  color: #666;
  font-weight: 400;
}

.tool-call-progress {
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  border-radius: 2px;
  transition: all 0.5s ease;
  position: relative;
}

.progress-bar.preparing {
  background: linear-gradient(90deg, #faad14, #ffc53d);
  animation: shimmer 1.5s ease-in-out infinite;
}

.progress-bar.executing {
  background: linear-gradient(90deg, #1677ff, #40a9ff);
  animation: shimmer 1s ease-in-out infinite;
}

.progress-bar.completed {
  background: linear-gradient(90deg, #52c41a, #73d13d);
}

.progress-bar.error {
  background: linear-gradient(90deg, #ff4d4f, #ff7875);
}

@keyframes shimmer {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

/* 响应式设计 */
@media (max-width: 480px) {
  .tool-calls-status {
    margin: 8px 0;
    padding: 12px;
  }
  
  .tool-call-item {
    padding: 10px 12px;
  }
  
  .tool-name {
    font-size: 13px;
  }
  
  .tool-status {
    font-size: 11px;
  }
}
</style> 