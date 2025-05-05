<template>
  <div
    ref="editorRef"
    class="editor-content"
    contenteditable="true"
    @input="handleInput"
    @keydown="handleKeyDown"
    @compositionstart="handleCompositionStart"
    @compositionend="handleCompositionEnd"
  ></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue';

const props = defineProps({
  modelValue: {
    type: String,
    default: '<p>开始写作...</p>'
  },
  showAgentSelector: {
    type: Boolean,
    default: false
  },
  readOnlyContent: {
    type: String,
    default: ''
  }
});

const emit = defineEmits([
  'update:modelValue', 
  'word-count', 
  'key-down', 
  'show-agent-selector',
  'composition-start',
  'composition-end',
  'input-update'
]);

const editorRef = ref<HTMLElement | null>(null);
const isComposing = ref(false);

// 监听值变化，更新编辑器内容
watch(() => props.modelValue, (newValue) => {
  if (editorRef.value && editorRef.value.innerHTML !== newValue) {
    // 保存光标位置
    const selection = window.getSelection();
    const range = selection?.rangeCount ? selection.getRangeAt(0) : null;
    
    // 更新内容
    updateEditorContent(newValue);
    
    // 恢复光标位置（仅当不是在不可编辑区域时）
    if (range && selection) {
      try {
        selection.removeAllRanges();
        selection.addRange(range);
      } catch (e) {
        console.log('无法恢复光标位置', e);
      }
    }
  }
});

// 更新编辑器内容，同时保护不可编辑区域
const updateEditorContent = (content) => {
  if (!editorRef.value) return;
  
  // 清理HTML中的连续空段落和多余空格
  let cleanContent = content;
  
  // 替换连续的空段落为单个空段落
  cleanContent = cleanContent.replace(/<p>\s*<\/p>\s*<p>\s*<\/p>/g, '<p></p>');
  
  // 替换包含只有空格的段落
  cleanContent = cleanContent.replace(/<p>\s+<\/p>/g, '<p></p>');
  
  // 移除段落之间的多余换行和空格
  cleanContent = cleanContent.replace(/>\s*\n+\s*</g, '><');
  
  // 移除多余的非断行空格
  cleanContent = cleanContent.replace(/&nbsp;/g, ' ');
  
  // 移除段落内连续多个空格
  cleanContent = cleanContent.replace(/(<p[^>]*>)(\s{2,})([^<]*<\/p>)/g, '$1 $3');
  
  if (props.readOnlyContent) {
    // 如果有不可编辑内容，确保它被正确标记
    const readOnlyDiv = document.createElement('div');
    readOnlyDiv.innerHTML = props.readOnlyContent;
    readOnlyDiv.classList.add('read-only-content');
    readOnlyDiv.setAttribute('contenteditable', 'false');
    
    // 创建可编辑区域
    const editableDiv = document.createElement('div');
    editableDiv.classList.add('editable-content');
    
    // 提取用户可编辑部分（从readOnlyContent后的内容）
    const editableContent = cleanContent.substring(props.readOnlyContent.length);
    editableDiv.innerHTML = editableContent || '<p></p>';
    
    // 清空编辑器并添加两个区域
    editorRef.value.innerHTML = '';
    editorRef.value.appendChild(readOnlyDiv);
    editorRef.value.appendChild(editableDiv);
  } else {
    // 如果没有不可编辑内容，直接设置
    editorRef.value.innerHTML = cleanContent;
  }
};

// 计算字数
const countWords = () => {
  if (!editorRef.value) return 0;
  // 去除HTML标签后计算文本长度
  const text = editorRef.value.textContent || '';
  emit('word-count', text.length);
  return text.length;
};

// 获取完整内容
const getFullContent = () => {
  if (!editorRef.value) return '';
  return editorRef.value.innerHTML;
};

// 处理输入事件
const handleInput = (event) => {
  if (isComposing.value || !editorRef.value) return;
  
  // 获取当前内容
  const currentContent = getFullContent();
  
  // 对内容进行清理（移除多余空行）后再比较
  let cleanedContent = currentContent;
  // 替换连续的空段落为单个空段落
  cleanedContent = cleanedContent.replace(/<p>\s*<\/p>\s*<p>\s*<\/p>/g, '<p></p>');
  // 替换包含只有空格的段落
  cleanedContent = cleanedContent.replace(/<p>\s+<\/p>/g, '<p></p>');
  // 移除段落之间的多余换行和空格
  cleanedContent = cleanedContent.replace(/>\s*\n+\s*</g, '><');
  
  // 如果内容没有变化，不触发更新
  if (cleanedContent === props.modelValue) {
    console.log('内容未变化，跳过更新');
    return;
  }
  
  // 确保不可编辑区域没有被修改
  if (props.readOnlyContent && !cleanedContent.startsWith(props.readOnlyContent)) {
    console.log('检测到不可编辑区域被修改，恢复内容');
    updateEditorContent(props.modelValue);
    return;
  }
  
  console.log('编辑器内容已改变，长度:', cleanedContent.length);
  emit('update:modelValue', cleanedContent);
  countWords();
  
  // 检查是否有Agent标签，决定是否显示底部提示
  const hasAgentMention = !!editorRef.value.querySelector('.user-mention');
  // 检查是否有加载指示器，如果有表示正在发送中
  const hasSendingIndicator = !!editorRef.value.querySelector('.typing-indicator');
  
  // 发送输入更新事件
  emit('input-update', { 
    hasAgentMention, 
    hasSendingIndicator, 
    selection: window.getSelection(),
    content: cleanedContent
  });
  
  // 检查是否刚输入了@符号
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0 && !props.showAgentSelector) {
    const range = selection.getRangeAt(0);
    
    // 处理文本节点
    if (range.startContainer.nodeType === Node.TEXT_NODE) {
      const textContent = range.startContainer.textContent || '';
      const offset = range.startOffset;
      
      // 检查光标前面的字符是否是@
      if (offset > 0 && textContent[offset - 1] === '@') {
        console.log('检测到@符号，触发选择器显示');
        emit('show-agent-selector', range);
      }
    }
  }
};

// 防止在只读区域编辑
const preventEditInReadOnlyArea = (event) => {
  if (!props.readOnlyContent) return false;
  
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount) return false;
  
  const range = selection.getRangeAt(0);
  const readOnlyElement = editorRef.value?.querySelector('.read-only-content');
  
  if (!readOnlyElement) return false;
  
  // 检查选区是否在只读区域内
  const isInReadOnly = readOnlyElement.contains(range.commonAncestorContainer) ||
                        readOnlyElement === range.commonAncestorContainer;
  
  if (isInReadOnly) {
    // 阻止在只读区域的键盘编辑
    event.preventDefault();
    
    // 将光标移动到可编辑区域开始位置
    const editableDiv = editorRef.value?.querySelector('.editable-content');
    if (editableDiv) {
      const newRange = document.createRange();
      newRange.setStart(editableDiv, 0);
      newRange.collapse(true);
      
      selection.removeAllRanges();
      selection.addRange(newRange);
    }
    
    return true;
  }
  
  return false;
};

// 处理键盘事件
const handleKeyDown = (event: KeyboardEvent) => {
  // 如果正在输入中文，不拦截任何键盘事件
  if (isComposing.value) return;
  
  // 检查并防止在只读区域编辑
  if (preventEditInReadOnlyArea(event)) {
    return;
  }
  
  // 处理@键
  if (event.key === '@' && !props.showAgentSelector) {
    console.log('检测到@键被按下');
    
    // 让浏览器先插入@符号
    setTimeout(() => {
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        console.log('准备显示选择器，范围:', range);
        emit('show-agent-selector', range);
      }
    }, 0);
  }
  
  // 处理连续回车键，避免产生过多空行
  if (event.key === 'Enter' && !event.shiftKey) {
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      let node = range.startContainer;
      
      // 找到当前段落元素
      while (node && node.nodeType !== Node.ELEMENT_NODE) {
        node = node.parentNode;
      }
      
      // 检查当前段落是否为空
      if (node && (node as HTMLElement).tagName === 'P' && 
          (!node.textContent || node.textContent.trim() === '')) {
        // 如果已经是空段落，则阻止创建新段落
        const prevNode = node.previousSibling;
        if (prevNode && (prevNode as HTMLElement).tagName === 'P' && 
            (!prevNode.textContent || prevNode.textContent.trim() === '')) {
          event.preventDefault();
          // 可选：删除前一个空段落
          node.parentNode?.removeChild(prevNode);
        }
      }
    }
  }
  
  // 转发键盘事件
  emit('key-down', {
    event,
    editorRef: editorRef.value,
    selection: window.getSelection()
  });
};

// 处理中文输入开始
const handleCompositionStart = () => {
  isComposing.value = true;
  emit('composition-start');
};

// 处理中文输入结束
const handleCompositionEnd = () => {
  isComposing.value = false;
  if (editorRef.value) {
    emit('update:modelValue', getFullContent());
    countWords();
  }
  emit('composition-end');
};

// 设置只读内容，将agent最后输出的内容标记为不可编辑
const setReadOnlyContent = (content) => {
  if (!editorRef.value) return;
  updateEditorContent(props.modelValue);
};

// 暴露方法和引用
defineExpose({
  editorRef,
  focus: () => editorRef.value?.focus(),
  setReadOnlyContent
});

// 直接DOM事件监听器，确保不会错过input事件
onMounted(() => {
  if (editorRef.value) {
    updateEditorContent(props.modelValue);
    countWords();
    
    // 添加DOM级别的事件监听器以确保捕获所有变更
    editorRef.value.addEventListener('input', () => {
      if (!isComposing.value && editorRef.value) {
        console.log('捕获到DOM input事件');
        
        // 检查并恢复只读区域
        const currentContent = getFullContent();
        if (props.readOnlyContent && !currentContent.startsWith(props.readOnlyContent)) {
          console.log('DOM事件中检测到只读区域被修改，恢复内容');
          updateEditorContent(props.modelValue);
          return;
        }
        
        emit('update:modelValue', currentContent);
      }
    });
    
    // 添加鼠标点击监听器，防止在只读区域设置光标
    editorRef.value.addEventListener('mousedown', (event) => {
      const target = event.target as Node;
      const readOnlyElement = editorRef.value?.querySelector('.read-only-content');
      
      if (readOnlyElement && (readOnlyElement.contains(target) || readOnlyElement === target)) {
        // 允许选择，但不设置光标在只读区域
        if (!event.shiftKey && !event.ctrlKey && !event.metaKey) {
          // 如果是单纯点击，则阻止默认行为
          event.preventDefault();
          
          // 将光标移至可编辑区域开始处
          const editableDiv = editorRef.value?.querySelector('.editable-content');
          if (editableDiv) {
            const range = document.createRange();
            range.setStart(editableDiv, 0);
            range.collapse(true);
            
            const selection = window.getSelection();
            if (selection) {
              selection.removeAllRanges();
              selection.addRange(range);
            }
          }
        }
      }
    });
  }
});
</script>

<style scoped>
.editor-content {
  flex: 1;
  outline: none;
  padding: 20px;
  font-size: 16px;
  line-height: 1.7;
  color: #333;
  overflow-y: auto;
  white-space: normal;
  word-break: break-word;
}

/* 只读内容样式 */
.read-only-content {
  position: relative;
  opacity: 0.9;
  background-color: #f9f9f9;
  border-radius: 5px;
  pointer-events: none;
  user-select: text;
  padding: 2px;
  margin-bottom: 15px;
}

/* 只读内容添加淡灰色边框 */
.read-only-content::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  pointer-events: none;
}

/* 可编辑内容样式 */
.editable-content {
  position: relative;
  min-height: 20px;
}

/* 自定义滚动条样式 */
.editor-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.editor-content::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 4px;
}

.editor-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
  transition: background 0.3s ease;
}

.editor-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Firefox滚动条自定义 */
.editor-content {
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f5f5f5;
}

.editor-content:focus {
  outline: none;
}

.editor-content p {
  margin: 0 0 10px;
}

/* 确保Agent响应段落样式 */
.editor-content .agent-response-paragraph {
  margin: 0 0 10px;
  white-space: normal;
  word-break: break-word;
  line-height: 1.7;
}

/* 在段落之间添加更明显的间距 */
.editor-content p + p {
  margin-top: 2px;
}

/* 调整标题与前面内容的间距，确保有适当分隔 */
.editor-content h1, 
.editor-content h2, 
.editor-content h3,
.editor-content h4,
.editor-content h5,
.editor-content h6 {
  margin-top: 1.2em;
}

/* 标题样式 */
.editor-content h1 {
  font-size: 2em;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.editor-content h2 {
  font-size: 1.5em;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.editor-content h3 {
  font-size: 1.17em;
  margin-top: 0.7em;
  margin-bottom: 0.7em;
  font-weight: bold;
}

.editor-content h4 {
  font-size: 1em;
  margin-top: 0.9em;
  margin-bottom: 0.9em;
  font-weight: bold;
}

.editor-content h5 {
  font-size: 0.83em;
  margin-top: 1em;
  margin-bottom: 1em;
  font-weight: bold;
}

.editor-content h6 {
  font-size: 0.67em;
  margin-top: 1.2em;
  margin-bottom: 1.2em;
  font-weight: bold;
}

/* 添加示例样式 */
.editor-content span[style*="letter-spacing"] {
  display: inline-block;
}

/* 行高样式 */
.editor-content span[style*="line-height"],
.editor-content div[style*="line-height"],
.editor-content p[style*="line-height"],
.editor-content h1[style*="line-height"],
.editor-content h2[style*="line-height"],
.editor-content h3[style*="line-height"],
.editor-content h4[style*="line-height"],
.editor-content h5[style*="line-height"],
.editor-content h6[style*="line-height"] {
  display: block;
  min-height: 1em;
}

/* 添加字号大小样式 */
.editor-content span[style*="font-size"],
.editor-content font[style*="font-size"] {
  display: inline;
}

/* 确保行高和字体大小正确显示 */
.editor-content [style*="font-size"] {
  font-size: inherit; /* 继承样式，确保样式生效 */
}

.editor-content [style*="line-height"] {
  line-height: inherit !important; /* 使用!important确保样式优先级 */
}
</style> 