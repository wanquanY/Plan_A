<template>
  <div v-if="toolCalls.length > 0" class="tool-calls-inline">
      <div 
        v-for="toolCall in toolCalls" 
        :key="toolCall.id"
      class="tool-call-inline-item"
        :class="toolCall.status"
      >
      <span class="tool-inline-icon">🔧</span>
      <span class="tool-inline-text">{{ getInlineStatusText(toolCall) }}</span>
      
      <!-- 工具调用结果（如果有且已完成） -->
      <div v-if="toolCall.result && toolCall.status === 'completed'" class="tool-inline-result">
        <button 
          class="result-toggle-btn" 
          @click="toggleResult(toolCall.id)"
          :class="{ expanded: isResultExpanded(toolCall.id) }"
        >
          查看结果
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6,9 12,15 18,9"></polyline>
          </svg>
        </button>
        <div v-if="isResultExpanded(toolCall.id)" class="tool-inline-result-content">
          {{ formatToolResult(toolCall.result) }}
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
import { computed, ref } from 'vue';
import type { ToolCallStatus } from '../../composables/useToolCallsStatus';

// Props
const props = defineProps<{
  toolCalls: ToolCallStatus[];
}>();

// 展开状态管理
const expandedResults = ref<Set<string>>(new Set());

// 计算已完成的工具数量
const completedCount = computed(() => {
  return props.toolCalls.filter(tool => tool.status === 'completed').length;
});

// 切换结果展开状态
const toggleResult = (id: string) => {
  if (expandedResults.value.has(id)) {
    expandedResults.value.delete(id);
  } else {
    expandedResults.value.add(id);
  }
};

// 检查结果是否展开
const isResultExpanded = (id: string): boolean => {
  return expandedResults.value.has(id);
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

// 格式化工具结果
const formatToolResult = (result: string): string => {
  try {
    // 尝试解析JSON
    const parsed = JSON.parse(result);
    
    // 如果是搜索结果，显示详细信息
    if (parsed.results && Array.isArray(parsed.results)) {
      const count = parsed.results.length;
      let summary = `找到 ${count} 条相关结果\n\n`;
      
      // 显示前3个结果的标题和链接
      parsed.results.slice(0, 3).forEach((item: any, index: number) => {
        summary += `${index + 1}. ${item.title || item.name || '无标题'}\n`;
        if (item.url) {
          summary += `   链接: ${item.url}\n`;
        }
        if (item.snippet || item.description) {
          summary += `   摘要: ${(item.snippet || item.description).substring(0, 100)}...\n`;
        }
        summary += '\n';
      });
      
      if (count > 3) {
        summary += `... 还有 ${count - 3} 条结果`;
      }
      
      return summary;
}

    // 如果是网页抓取结果，显示内容摘要
    if (parsed.content) {
      const contentLength = parsed.content.length;
      let summary = `成功抓取网页内容\n`;
      summary += `内容长度: ${contentLength} 字符\n\n`;
      
      // 显示内容前200个字符作为预览
      const preview = parsed.content.substring(0, 200).replace(/\s+/g, ' ').trim();
      summary += `内容预览:\n${preview}${contentLength > 200 ? '...' : ''}`;
      
      return summary;
}

    // 如果是新闻搜索结果
    if (parsed.news && Array.isArray(parsed.news)) {
      const count = parsed.news.length;
      let summary = `找到 ${count} 条新闻\n\n`;
      
      parsed.news.slice(0, 3).forEach((item: any, index: number) => {
        summary += `${index + 1}. ${item.title || '无标题'}\n`;
        if (item.source) {
          summary += `   来源: ${item.source}\n`;
}
        if (item.date) {
          summary += `   时间: ${item.date}\n`;
}
        if (item.snippet) {
          summary += `   摘要: ${item.snippet.substring(0, 100)}...\n`;
        }
        summary += '\n';
      });
      
      return summary;
    }
    
    // 如果有错误信息
    if (parsed.error) {
      return `执行失败: ${parsed.error}`;
}

    // 如果有成功状态和消息
    if (parsed.success && parsed.message) {
      return `执行成功: ${parsed.message}`;
    }
    
    // 其他情况，返回格式化的JSON
    return JSON.stringify(parsed, null, 2);
  } catch (e) {
    // 如果不是JSON，直接返回原始内容
    return result;
  }
};

// 获取内联状态文本
const getInlineStatusText = (toolCall: ToolCallStatus): string => {
  return `${getToolDisplayName(toolCall.name)} - ${getToolStatusText(toolCall.status)}`;
};
</script>

<style scoped>
.tool-calls-inline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-call-inline-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-inline-icon {
  font-size: 18px;
}

.tool-inline-text {
  font-size: 14px;
  color: #333;
}

.tool-inline-result {
  margin-left: 8px;
}

.result-toggle-btn {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  cursor: pointer;
  outline: inherit;
  color: #666;
  font-size: 12px;
  transition: color 0.2s ease;
}

.result-toggle-btn:hover {
  color: #1677ff;
}

.result-toggle-btn.expanded {
  color: #1677ff;
}

.tool-inline-result-content {
  padding: 8px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  overflow: hidden;
  font-size: 12px;
  color: #333;
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .tool-inline-text {
    font-size: 13px;
  }
}
</style> 