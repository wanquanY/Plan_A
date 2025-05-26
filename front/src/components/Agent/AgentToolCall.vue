<template>
  <div class="tool-call-card" :class="status">
    <div class="tool-call-header" @click="toggleResult">
      <span class="tool-icon">{{ getToolStatusIcon(status) }}</span>
      <span class="tool-name">{{ getToolDisplayName(toolName) }}</span>
      <span class="tool-status-text">{{ getToolStatusText(status) }}</span>
      <span v-if="result" class="expand-icon" :class="{ expanded: isExpanded }">›</span>
    </div>
    
    <div v-if="result && isExpanded" class="tool-result">
      <div v-if="isSearchTool" class="search-results">
        <div v-for="(item, index) in getSearchResults(result)" :key="index" class="search-item">
          <a :href="item.link" target="_blank" class="search-title">{{ item.title }}</a>
          <p class="search-snippet">{{ item.snippet }}</p>
        </div>
      </div>
      <pre v-else>{{ formatToolResult(result) }}</pre>
    </div>
    
    <div v-if="error" class="tool-error">
      <span class="error-text">错误: {{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  toolName: string;
  status: string;
  toolCallId: string;
  result?: any;
  error?: any;
}

const props = defineProps<Props>();

const isExpanded = ref(false);

const isSearchTool = computed(() => {
  return props.toolName === 'serper_search' || props.toolName === 'tavily_search';
});

const toggleResult = () => {
  if (props.result) {
    isExpanded.value = !isExpanded.value;
  }
};

// 获取工具状态图标
const getToolStatusIcon = (status: string) => {
  const iconMap: Record<string, string> = {
    'preparing': '⏳',
    'executing': '⚙️',
    'completed': '✅',
    'error': '❌'
  };
  return iconMap[status] || '🔧';
};

// 获取工具显示名称
const getToolDisplayName = (toolName: string) => {
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
const getToolStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'preparing': '准备中...',
    'executing': '执行中...',
    'completed': '执行完成',
    'error': '执行失败'
  };
  return statusMap[status] || status;
};

// 格式化工具结果
const formatToolResult = (result: any) => {
  if (typeof result === 'string') {
    try {
      const parsed = JSON.parse(result);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return result;
    }
  } else if (typeof result === 'object') {
    return JSON.stringify(result, null, 2);
  }
  return String(result);
};

// 解析搜索结果
const getSearchResults = (result: any) => {
  try {
    let searchData = result;
    
    // 如果是字符串，尝试解析
    if (typeof result === 'string') {
      searchData = JSON.parse(result);
    }
    
    // 提取搜索结果
    if (searchData.organic_results) {
      return searchData.organic_results.slice(0, 5); // 只显示前5个结果
    } else if (searchData.results) {
      return searchData.results.slice(0, 5);
    } else if (Array.isArray(searchData)) {
      return searchData.slice(0, 5);
    }
    
    return [];
  } catch (error) {
    console.error('解析搜索结果失败:', error);
    return [];
  }
};
</script>

<style scoped>
/* 工具卡片样式 - 简约版 */
.tool-call-card {
  background: transparent;
  border: none;
  border-left: 3px solid #e5e7eb;
  border-radius: 0;
  margin: 8px 0;
  padding: 8px 12px;
  transition: all 0.2s ease;
  clear: both;
  display: block;
}

.tool-call-card:hover {
  background: rgba(0, 0, 0, 0.02);
}

.tool-call-card.executing {
  border-left-color: #3b82f6;
  background: rgba(59, 130, 246, 0.03);
}

.tool-call-card.completed {
  border-left-color: #10b981;
  background: rgba(16, 185, 129, 0.03);
}

.tool-call-card.error {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.03);
}

.tool-call-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
}

.tool-call-header .tool-icon {
  font-size: 14px;
  display: flex;
  align-items: center;
  min-width: 16px;
  opacity: 0.7;
}

.tool-call-header .tool-name {
  font-weight: 500;
  color: #6b7280;
  font-size: 13px;
}

.tool-call-header .tool-status-text {
  font-size: 12px;
  color: #9ca3af;
  margin-left: auto;
  margin-right: 8px;
}

.tool-call-header .expand-icon {
  font-size: 14px;
  color: #9ca3af;
  transition: transform 0.2s ease;
  cursor: pointer;
  margin-left: auto;
  font-weight: bold;
}

.tool-call-header .expand-icon.expanded {
  transform: rotate(90deg);
}

.tool-result {
  margin-top: 8px;
  padding: 8px 0;
  max-height: 400px;
  overflow-y: auto;
}

.tool-result pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
  line-height: 1.4;
  color: #6b7280;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #f8fafc;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.tool-error {
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 4px;
}

.tool-error .error-text {
  font-size: 12px;
  color: #dc2626;
  font-weight: 400;
}

.tool-call-card.executing .tool-icon {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 搜索结果样式 */
.search-results {
  margin: 0;
}

.search-item {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f3f4f6;
}

.search-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.search-title {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #2563eb;
  text-decoration: none;
  line-height: 1.3;
  margin-bottom: 4px;
}

.search-title:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.search-snippet {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
  margin: 0;
}
</style> 