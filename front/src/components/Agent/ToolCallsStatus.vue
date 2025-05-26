<template>
  <div v-if="toolCalls.length > 0" class="tool-calls-container">
    <div class="tool-calls-header">
      <div class="header-info">
        <span class="tool-icon">🛠️</span>
        <span class="header-text">工具调用</span>
        <span class="tool-count-badge">{{ toolCalls.length }}</span>
      </div>
      <div class="header-status">
        <span v-if="hasActiveTools" class="status-indicator active">
          <span class="pulse-dot"></span>
          执行中
        </span>
        <span v-else-if="hasErrorTools" class="status-indicator error">
          ❌ 有错误
        </span>
        <span v-else class="status-indicator completed">
          ✅ 已完成
        </span>
      </div>
    </div>

    <div class="tool-calls-list">
      <div 
        v-for="(toolCall, index) in toolCalls" 
        :key="toolCall.id"
        class="tool-call-card"
        :class="[toolCall.status, { 'expanded': isResultExpanded(toolCall.id) }]"
      >
        <!-- 工具调用头部 -->
        <div class="tool-call-header" @click="toggleResult(toolCall.id)">
          <div class="tool-info">
            <div class="tool-icon-wrapper" :class="toolCall.status">
              <span class="tool-icon-emoji">{{ getToolIcon(toolCall.name, toolCall.status) }}</span>
              <div v-if="toolCall.status === 'executing'" class="loading-spinner"></div>
            </div>
            <div class="tool-details">
              <div class="tool-name">{{ getToolDisplayName(toolCall.name) }}</div>
              <div class="tool-status-text" :class="toolCall.status">
                {{ getToolStatusText(toolCall.status) }}
              </div>
            </div>
          </div>
          
          <div class="tool-actions">
            <div v-if="toolCall.status === 'executing'" class="progress-bar">
              <div class="progress-fill" :style="{ width: getProgressWidth(toolCall.status) }"></div>
            </div>
            <button 
              v-if="toolCall.result && toolCall.status === 'completed'"
              class="expand-btn"
              :class="{ 'expanded': isResultExpanded(toolCall.id) }"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6,9 12,15 18,9"></polyline>
              </svg>
            </button>
          </div>
        </div>

        <!-- 工具调用结果展开区域 -->
        <transition name="expand">
          <div v-if="isResultExpanded(toolCall.id) && toolCall.result" class="tool-result-container">
            <div class="result-header">
              <span class="result-label">执行结果</span>
              <button class="copy-btn" @click="copyResult(toolCall.result)" title="复制结果">
                📋
              </button>
            </div>
            <div class="tool-result-content">
              <div class="result-preview">
                {{ formatToolResult(toolCall.result) }}
              </div>
            </div>
          </div>
        </transition>

        <!-- 错误信息显示 -->
        <div v-if="toolCall.status === 'error'" class="tool-error-container">
          <div class="error-header">
            <span class="error-icon">⚠️</span>
            <span class="error-label">执行失败</span>
          </div>
          <div class="error-content">
            执行过程中发生错误，请稍后重试
          </div>
        </div>
      </div>
    </div>

    <!-- 工具调用总结 -->
    <div class="tool-calls-summary">
      <div class="summary-stats">
        <span class="stat-item">
          <span class="stat-label">总计:</span>
          <span class="stat-value">{{ toolCalls.length }}</span>
        </span>
        <span class="stat-item">
          <span class="stat-label">完成:</span>
          <span class="stat-value completed">{{ completedCount }}</span>
        </span>
        <span v-if="hasErrorTools" class="stat-item">
          <span class="stat-label">失败:</span>
          <span class="stat-value error">{{ getToolCountByStatus('error') }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ToolCallStatus } from '../../composables/useToolCallsStatus';

// Props
const props = defineProps<{
  toolCalls: ToolCallStatus[];
}>();

// 展开状态管理
const expandedResults = ref<Set<string>>(new Set());

// 计算属性
const completedCount = computed(() => {
  return props.toolCalls.filter(tool => tool.status === 'completed').length;
});

const hasActiveTools = computed(() => {
  return props.toolCalls.some(tool => 
    tool.status === 'preparing' || tool.status === 'executing'
  );
});

const hasErrorTools = computed(() => {
  return props.toolCalls.some(tool => tool.status === 'error');
});

// 方法
const toggleResult = (id: string) => {
  if (expandedResults.value.has(id)) {
    expandedResults.value.delete(id);
  } else {
    expandedResults.value.add(id);
  }
};

const isResultExpanded = (id: string): boolean => {
  return expandedResults.value.has(id);
};

const getToolCountByStatus = (status: string): number => {
  return props.toolCalls.filter(tool => tool.status === status).length;
};

const copyResult = async (result: string) => {
  try {
    await navigator.clipboard.writeText(result);
    // 可以添加一个提示消息
  } catch (err) {
    console.error('复制失败:', err);
  }
};

// 获取工具图标
const getToolIcon = (toolName: string, status: string): string => {
  const toolIcons: Record<string, string> = {
    'tavily_search': '🔍',
    'tavily_extract': '📄',
    'serper_search': '🌐',
    'serper_news': '📰',
    'serper_scrape': '🕷️',
    'web_search': '🔍',
    'web_scrape': '🕷️',
    'file_read': '📖',
    'file_write': '✏️',
    'code_execute': '💻'
  };
  
  if (status === 'error') return '❌';
  if (status === 'completed') return '✅';
  
  return toolIcons[toolName] || '🔧';
};

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
    'completed': '执行完成',
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

// 格式化工具结果
const formatToolResult = (result: string): string => {
  try {
    const parsed = JSON.parse(result);
    
    // 搜索结果格式化
    if (parsed.results && Array.isArray(parsed.results)) {
      const count = parsed.results.length;
      let summary = `🔍 找到 ${count} 条相关结果\n\n`;
      
      parsed.results.slice(0, 3).forEach((item: any, index: number) => {
        summary += `${index + 1}. ${item.title || item.name || '无标题'}\n`;
        if (item.url) {
          summary += `   🔗 ${item.url}\n`;
        }
        if (item.snippet || item.description) {
          summary += `   📝 ${(item.snippet || item.description).substring(0, 100)}...\n`;
        }
        summary += '\n';
      });
      
      if (count > 3) {
        summary += `... 还有 ${count - 3} 条结果`;
      }
      
      return summary;
    }

    // 网页抓取结果格式化
    if (parsed.content) {
      const contentLength = parsed.content.length;
      let summary = `📄 成功抓取网页内容\n`;
      summary += `📊 内容长度: ${contentLength} 字符\n\n`;
      
      const preview = parsed.content.substring(0, 200).replace(/\s+/g, ' ').trim();
      summary += `📖 内容预览:\n${preview}${contentLength > 200 ? '...' : ''}`;
      
      return summary;
    }

    // 新闻搜索结果格式化
    if (parsed.news && Array.isArray(parsed.news)) {
      const count = parsed.news.length;
      let summary = `📰 找到 ${count} 条新闻\n\n`;
      
      parsed.news.slice(0, 3).forEach((item: any, index: number) => {
        summary += `${index + 1}. ${item.title || '无标题'}\n`;
        if (item.source) {
          summary += `   📺 来源: ${item.source}\n`;
        }
        if (item.date) {
          summary += `   📅 时间: ${item.date}\n`;
        }
        if (item.snippet) {
          summary += `   📝 ${item.snippet.substring(0, 100)}...\n`;
        }
        summary += '\n';
      });
      
      return summary;
    }
    
    if (parsed.error) {
      return `❌ 执行失败: ${parsed.error}`;
    }

    if (parsed.success && parsed.message) {
      return `✅ 执行成功: ${parsed.message}`;
    }
    
    return JSON.stringify(parsed, null, 2);
  } catch (e) {
    return result;
  }
};
</script>

<style scoped>
.tool-calls-container {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  margin: 12px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.tool-calls-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-icon {
  font-size: 20px;
}

.header-text {
  font-weight: 600;
  color: #334155;
  font-size: 16px;
}

.tool-count-badge {
  background: #3b82f6;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-indicator.active {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-indicator.completed {
  background: #dcfce7;
  color: #166534;
}

.status-indicator.error {
  background: #fee2e2;
  color: #dc2626;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: #3b82f6;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.tool-calls-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-call-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.tool-call-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #cbd5e1;
}

.tool-call-card.expanded {
  border-color: #3b82f6;
}

.tool-call-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.tool-call-header:hover {
  background: #f8fafc;
}

.tool-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tool-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.tool-icon-wrapper.preparing {
  background: #fef3c7;
}

.tool-icon-wrapper.executing {
  background: #dbeafe;
}

.tool-icon-wrapper.completed {
  background: #dcfce7;
}

.tool-icon-wrapper.error {
  background: #fee2e2;
}

.tool-icon-emoji {
  font-size: 20px;
  z-index: 2;
}

.loading-spinner {
  position: absolute;
  width: 32px;
  height: 32px;
  border: 2px solid #e2e8f0;
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  z-index: 1;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.tool-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tool-name {
  font-weight: 600;
  color: #334155;
  font-size: 14px;
}

.tool-status-text {
  font-size: 12px;
  font-weight: 500;
}

.tool-status-text.preparing {
  color: #d97706;
}

.tool-status-text.executing {
  color: #2563eb;
}

.tool-status-text.completed {
  color: #16a34a;
}

.tool-status-text.error {
  color: #dc2626;
}

.tool-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 60px;
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.expand-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.expand-btn:hover {
  background: #f1f5f9;
  color: #334155;
}

.expand-btn.expanded {
  transform: rotate(180deg);
  color: #3b82f6;
}

.tool-result-container {
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.result-label {
  font-weight: 600;
  color: #334155;
  font-size: 13px;
}

.copy-btn {
  background: none;
  border: none;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.copy-btn:hover {
  background: #e2e8f0;
}

.tool-result-content {
  padding: 16px;
}

.result-preview {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #374151;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.tool-error-container {
  border-top: 1px solid #fecaca;
  background: #fef2f2;
  padding: 12px 16px;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.error-icon {
  font-size: 16px;
}

.error-label {
  font-weight: 600;
  color: #dc2626;
  font-size: 13px;
}

.error-content {
  color: #991b1b;
  font-size: 12px;
  line-height: 1.4;
}

.tool-calls-summary {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.summary-stats {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.stat-value {
  font-weight: 600;
  font-size: 12px;
}

.stat-value.completed {
  color: #16a34a;
}

.stat-value.error {
  color: #dc2626;
}

/* 展开动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
  opacity: 1;
}

/* 响应式设计 */
@media (max-width: 640px) {
  .tool-calls-container {
    padding: 12px;
    margin: 8px 0;
  }
  
  .tool-call-header {
    padding: 10px 12px;
  }
  
  .tool-icon-wrapper {
    width: 36px;
    height: 36px;
  }
  
  .tool-icon-emoji {
    font-size: 18px;
  }
  
  .loading-spinner {
    width: 28px;
    height: 28px;
  }
  
  .summary-stats {
    gap: 12px;
  }
}
</style> 