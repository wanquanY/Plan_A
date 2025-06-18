<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import hljs from 'highlight.js';
// 注释掉默认样式，使用自定义样式
// import 'highlight.js/styles/github.css';

// 定义组件的属性
const props = defineProps({
  // 代码内容
  code: {
    type: String,
    required: true
  },
  // 代码语言
  language: {
    type: String,
    default: 'text'
  }
});

// 复制按钮的状态
const isCopied = ref(false);
const codeRef = ref(null);

// 在组件挂载后应用代码高亮
onMounted(async () => {
  await nextTick();
  
  if (codeRef.value && props.code) {
    try {
      // 设置代码内容（纯文本，安全）
      codeRef.value.textContent = props.code;
      
      // 应用高亮
      if (props.language && props.language !== 'text') {
        hljs.highlightElement(codeRef.value);
      } else {
        // 自动检测语言
        hljs.highlightElement(codeRef.value);
      }
    } catch (error) {
      console.error('代码高亮处理失败:', error);
      // 如果高亮失败，至少显示原始代码
      if (codeRef.value) {
        codeRef.value.textContent = props.code;
      }
    }
  }
});

// 复制代码到剪贴板
const copyCode = () => {
  navigator.clipboard.writeText(props.code)
    .then(() => {
      isCopied.value = true;
      setTimeout(() => {
        isCopied.value = false;
      }, 2000);
    })
    .catch(err => {
      console.error('复制失败:', err);
    });
};
</script>

<template>
  <div class="code-block-wrapper">
    <pre :data-language="language"><code ref="codeRef" :class="`language-${language}`"></code></pre>
    <div 
      class="code-copy-button" 
      :class="{ 'copied': isCopied }" 
      :title="isCopied ? '已复制!' : '复制代码'" 
      @click="copyCode"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.code-block-wrapper {
  position: relative;
  margin: 0.6em 0;
}

pre {
  background-color: #f6f8fa !important;
  border-radius: 6px;
  padding: 2.4em 1em 1em;
  margin: 0;
  overflow-x: auto;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 85%;
  tab-size: 4;
  white-space: pre;
  line-height: 1.4;
  border: 1px solid #eaecef;
  position: relative;
}

code {
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace !important;
  background-color: transparent !important;
  padding: 0;
  margin: 0;
  border-radius: 0;
  white-space: pre;
  display: block;
  overflow-x: auto;
  color: #24292e !important;
  font-size: 0.95em;
}

/* 添加语言标识 */
pre::before {
  content: attr(data-language);
  position: absolute;
  top: 0;
  left: 0;
  padding: 3px 8px;
  font-size: 12px;
  color: #666;
  background-color: #f6f8fa;
  border-bottom-right-radius: 4px;
  pointer-events: none;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  border-bottom: 1px solid #eaecef;
  border-right: 1px solid #eaecef;
  font-weight: 500;
}

/* 复制按钮样式 */
.code-copy-button {
  position: absolute;
  right: 0;
  top: 0;
  background-color: rgba(246, 248, 250, 0.9);
  border-radius: 0 5px 0 4px;
  padding: 4px 6px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease, background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-bottom: 1px solid #eaecef;
  border-left: 1px solid #eaecef;
  color: #666;
}

.code-block-wrapper:hover .code-copy-button {
  opacity: 1;
}

/* 复制按钮交互效果 */
.code-copy-button:hover {
  background-color: #f0f0f0;
  color: #0366d6;
}

.code-copy-button.copied {
  background-color: #dcffe4;
  color: #28a745;
  opacity: 1;
}

.code-copy-button svg {
  width: 16px;
  height: 16px;
}

/* 代码块滚动条 */
pre::-webkit-scrollbar {
  height: 6px;
}

pre::-webkit-scrollbar-track {
  background: transparent;
}

pre::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

/* highlight.js相关样式覆盖 - GitHub主题 */
:deep(.hljs) {
  background-color: transparent !important;
  color: #24292e !important;
}

:deep(.hljs-keyword) {
  color: #d73a49 !important;
  font-weight: bold;
}

:deep(.hljs-string) {
  color: #032f62 !important;
}

:deep(.hljs-comment) {
  color: #6a737d !important;
  font-style: italic;
}

:deep(.hljs-function) {
  color: #6f42c1 !important;
}

:deep(.hljs-number) {
  color: #005cc5 !important;
}

:deep(.hljs-operator) {
  color: #d73a49 !important;
}

:deep(.hljs-tag) {
  color: #22863a !important;
}

:deep(.hljs-name) {
  color: #6f42c1 !important;
}

:deep(.hljs-attr) {
  color: #032f62 !important;
}

:deep(.hljs-built_in) {
  color: #e36209 !important;
}

:deep(.hljs-literal) {
  color: #005cc5 !important;
}

:deep(.hljs-type) {
  color: #d73a49 !important;
}

:deep(.hljs-params) {
  color: #24292e !important;
}

:deep(.hljs-meta) {
  color: #6a737d !important;
}

:deep(.hljs-title) {
  color: #6f42c1 !important;
  font-weight: bold;
}

:deep(.hljs-variable) {
  color: #e36209 !important;
}

:deep(.hljs-emphasis) {
  font-style: italic;
}

:deep(.hljs-strong) {
  font-weight: bold;
}
</style> 