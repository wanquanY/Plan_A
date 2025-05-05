<template>
  <div class="editor-container">
    <EditorToolbar
      :editor-ref="editorContentRef?.editorRef"
      :selected-heading="selectedHeading"
      @apply-formatting="applyFormat"
      @set-heading="setHeading"
      @set-letter-spacing="setLetterSpacing"
      @set-line-height="setLineHeight"
      @set-font-size="setFontSize"
      @undo="undoAction"
      @redo="redoAction"
    />
    
    <div class="editor-main">
      <EditorContent
        ref="editorContentRef"
        :model-value="modelValue"
        @update:model-value="$emit('update:modelValue', $event)"
        :show-agent-selector="showAgentSelector"
        @word-count="updateWordCount"
        @key-down="handleKeyDown"
        @show-agent-selector="showAgentSelectorAt"
        @composition-start="isComposing = true"
        @composition-end="isComposing = false"
        @input-update="handleInputUpdate"
      />
      
      <MentionHandler
        :show-selector="showAgentSelector"
        :current-range="currentRange"
        @close="showAgentSelector = false"
        @agent-selected="onAgentSelected"
      />
    </div>
    <AgentResponseHandler ref="agentResponseHandlerRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, watch } from 'vue';
import EditorToolbar from './EditorToolbar.vue';
import EditorContent from './EditorContent.vue';
import MentionHandler from './MentionHandler.vue';
import AgentResponseHandler from './AgentResponseHandler.vue';

// Props声明
const props = defineProps({
  modelValue: {
    type: String,
    default: '<p>开始写作...</p>'
  },
  conversationId: {
    type: [Number, String, null],
    default: null
  }
});

// 事件声明
const emit = defineEmits(['update:modelValue', 'word-count']);

// 状态变量
const wordCount = ref(0);
const isComposing = ref(false);
const showAgentSelector = ref(false);
const currentRange = ref(null);
const selectedHeading = ref('p');

// 组件引用
const editorContentRef = ref(null);
const agentResponseHandlerRef = ref(null);

// 监听会话ID变化
watch(() => props.conversationId, (newId) => {
  if (agentResponseHandlerRef.value) {
    console.log(`编辑器接收到会话ID: ${newId || 'null'}，设置到AgentResponseHandler`);
    // 无论newId是否为null都要设置，确保新建会话时能正确清空
    agentResponseHandlerRef.value.setConversationId(newId ? newId.toString() : null);
  }
}, { immediate: true });

// 监听modelValue变化
watch(() => props.modelValue, (newValue, oldValue) => {
  console.log('Editor接收到新内容，长度:', newValue.length);
  
  // 强制重新渲染内容到编辑器
  if (editorContentRef.value && editorContentRef.value.editorRef) {
    // 确保内容不同时才更新，避免光标跳动
    if (editorContentRef.value.editorRef.innerHTML !== newValue) {
      // 如果变化是由于处理代码块或渲染操作导致的微小差异，忽略更新
      if (oldValue && Math.abs(oldValue.length - newValue.length) < 10 && 
          oldValue.replace(/\s+/g, '') === newValue.replace(/\s+/g, '')) {
        console.log('内容变化很小，可能是格式化导致，忽略更新');
        return;
      }
      
      console.log('更新编辑器DOM内容');
      editorContentRef.value.editorRef.innerHTML = newValue;
    }
  }
}, { immediate: true });

// 格式化操作
const applyFormat = ({ command, value }) => {
  document.execCommand(command, false, value);
  // 聚焦编辑器以保持光标位置
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 设置标题
const setHeading = (heading: string) => {
  document.execCommand('formatBlock', false, heading);
  selectedHeading.value = heading;
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 设置字号
const setFontSize = (size: string) => {
  document.execCommand('fontSize', false, '7');
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    const fontElements = document.getElementsByTagName('font');
    for (let i = 0; i < fontElements.length; i++) {
      if (fontElements[i].getAttribute('size') === '7') {
        fontElements[i].removeAttribute('size');
        fontElements[i].style.fontSize = size;
      }
    }
  }
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 设置字间距
const setLetterSpacing = (spacing: string) => {
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    const span = document.createElement('span');
    span.style.letterSpacing = spacing;
    range.surroundContents(span);
  }
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 设置行高
const setLineHeight = (height: string) => {
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    
    // 检查选择是否包含多个段落或完整段落
    let containsElement = false;
    let startNode = range.startContainer;
    
    // 查找最近的块级元素
    while (startNode && startNode !== editorContentRef.value?.editorRef) {
      if (startNode.nodeType === Node.ELEMENT_NODE && 
          ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'DIV'].includes(startNode.nodeName)) {
        containsElement = true;
        break;
      }
      startNode = startNode.parentNode;
    }
    
    if (containsElement && startNode) {
      // 如果选择包含完整段落，直接设置段落的行高
      (startNode as HTMLElement).style.lineHeight = height;
    } else {
      // 创建一个包含选定内容的 span 元素
      const span = document.createElement('span');
      span.style.lineHeight = height;
      span.style.display = 'inline-block';
      span.style.width = '100%';
      
      try {
        range.surroundContents(span);
      } catch (e) {
        console.error('Cannot surroundContents, selection may cross element boundaries', e);
        // 备选方案：创建一个新的范围，提取内容，清除范围，插入 span
        const fragment = range.extractContents();
        span.appendChild(fragment);
        range.insertNode(span);
      }
    }
  }
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 显示AI助手选择器
const showAgentSelectorAt = (range) => {
  // 保存当前选区范围
  currentRange.value = range;
  
  // 先显示选择器，然后在下一帧计算位置
  showAgentSelector.value = true;
  
  // 使用nextTick确保选择器DOM已经渲染
  nextTick(() => {
    if (range) {
      const rect = range.getBoundingClientRect();
      if (rect) {
        // 查找选择器元素
        const selectorElement = document.querySelector('.agent-selector') as HTMLElement;
        if (selectorElement) {
          console.log('找到选择器元素，将设置位置');
          
          // 获取编辑器内容区域的位置
          const editorContentElement = editorContentRef.value?.editorRef;
          const editorRect = editorContentElement?.getBoundingClientRect();
          
          if (editorRect) {
            // 计算相对于编辑器的位置
            let top = rect.bottom - editorRect.top + window.scrollY + 5;
            const left = rect.left - editorRect.left + window.scrollX;
            
            // 检查选择器是否会超出窗口底部
            const viewportHeight = window.innerHeight;
            const selectorHeight = selectorElement.offsetHeight;
            const absoluteBottom = rect.bottom + selectorHeight + 5;
            
            // 如果超出底部，则向上显示
            if (absoluteBottom > viewportHeight) {
              // 在@符号上方显示
              top = rect.top - editorRect.top + window.scrollY - selectorHeight - 5;
              console.log('选择器将在上方显示，避免超出窗口');
            }
            
            console.log(`设置选择器位置: top=${top}px, left=${left}px`);
            selectorElement.style.top = `${top}px`;
            selectorElement.style.left = `${left}px`;
          }
        } else {
          console.warn('未找到选择器元素');
        }
      }
    }
  });
};

// 当选择了AI助手
const onAgentSelected = (agent) => {
  console.log('选择了AI助手:', agent.name);
};

// 更新字数计数
const updateWordCount = (count: number) => {
  wordCount.value = count;
  emit('word-count', count);
};

// 处理输入更新
const handleInputUpdate = ({ hasAgentMention, hasSendingIndicator, selection, content }) => {
  // 根据编辑器内容更新UI状态
  if (content) {
    // 确保EditorContent组件内容被更新到父组件的modelValue
    emit('update:modelValue', content);
    console.log('Editor内容已更新，字符数:', content.length);
  }
};

// 处理键盘按键事件
const handleKeyDown = ({ event, editorRef, selection }) => {
  // Enter 键按下时处理AI助手交互
  if (event.key === 'Enter' && !event.shiftKey && !isComposing.value) {
    const lastMention = agentResponseHandlerRef.value?.findLastMention(editorRef);
    
    if (lastMention && agentResponseHandlerRef.value && !agentResponseHandlerRef.value.isProcessing) {
      // 检查光标是否在包含@提及的行上
      const isInMentionLine = isCursorInSameLineWithMention(selection, lastMention);
      
      if (isInMentionLine) {
        // 获取用户输入
        const userInput = agentResponseHandlerRef.value.extractUserInput(editorRef, lastMention);
        
        if (userInput && userInput.trim()) {
          // 获取AI助手ID
          const agentId = lastMention.getAttribute('data-agent-id');
          
          if (agentId) {
            event.preventDefault(); // 阻止默认的换行行为
            
            // 不再在此处插入段落，由AgentResponseHandler控制插入位置
            // 让光标保持在当前位置
            
            // 发送消息给AI助手，它会在当前位置插入响应
            agentResponseHandlerRef.value.handleChat(agentId, userInput, editorRef);
          }
        }
      }
    }
  }
};

// 检查光标是否在包含@提及的同一行
const isCursorInSameLineWithMention = (selection, mention) => {
  if (!selection || !selection.rangeCount || !mention) return false;
  
  // 检查提及是否已处理
  if (mention.getAttribute('data-processed') === 'true') {
    console.log('忽略已处理的@提及元素');
    return false;
  }
  
  // 获取当前光标所在的范围
  const range = selection.getRangeAt(0);
  const cursorNode = range.startContainer;
  
  // 获取光标所在的段落元素
  let cursorParagraph = cursorNode;
  while (cursorParagraph && cursorParagraph.nodeType !== Node.ELEMENT_NODE) {
    cursorParagraph = cursorParagraph.parentNode;
  }
  
  // 获取提及元素所在的段落
  let mentionParagraph = mention;
  while (mentionParagraph && mentionParagraph.nodeName !== 'P' && mentionParagraph.nodeName !== 'DIV') {
    mentionParagraph = mentionParagraph.parentNode;
  }
  
  // 判断光标和提及是否在同一个段落中
  return cursorParagraph === mentionParagraph;
};

// 添加撤销和重做操作
const undoAction = () => {
  document.execCommand('undo', false);
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

const redoAction = () => {
  document.execCommand('redo', false);
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 组件挂载后聚焦编辑器
onMounted(() => {
  nextTick(() => {
    editorContentRef.value?.focus();
    
    // 处理已有的代码块和图表，但延迟执行避免初始化时触发递归更新
    if (agentResponseHandlerRef.value) {
      // 延迟更长时间，确保初始渲染完成
      setTimeout(() => {
        try {
          // 先检查是否有需要处理的代码块
          const hasUnprocessedBlocks = document.querySelectorAll('pre > code:not(.processed-code-block)').length > 0;
          // 检查是否有markdown代码块(可能是思维导图)
          const hasMarkdownBlocks = document.querySelectorAll('pre > code.language-markdown, pre > code.language-md').length > 0;
          
          if (hasUnprocessedBlocks || hasMarkdownBlocks) {
            console.log('编辑器加载完成，处理已有代码块和思维导图');
            
            // 分别处理各个功能，捕获可能的错误
            try {
              // 确保代码块有语言标识
              agentResponseHandlerRef.value.ensureCodeBlocksHaveLanguage();
            } catch (e) {
              console.error('代码语言识别错误:', e);
            }
            
            try {
              // 使用CodeBlock组件替换代码块
              agentResponseHandlerRef.value.setupCodeBlocks();
            } catch (e) {
              console.error('设置代码块组件错误:', e);
            }
            
            try {
              // 渲染Mermaid图表
              agentResponseHandlerRef.value.renderMermaidDiagrams();
            } catch (e) {
              console.error('渲染图表错误:', e);
            }
          }
          
          // 检查是否有符合思维导图格式的段落
          const paragraphs = document.querySelectorAll('p');
          let foundMindmap = false;
          
          for (const p of paragraphs) {
            const content = p.textContent || '';
            if (content.match(/^#\s+.+/m) && content.match(/^#{2,}\s+.+/m)) {
              foundMindmap = true;
              break;
            }
          }
          
          if (foundMindmap) {
            console.log('检测到思维导图内容，处理思维导图');
            
            // 处理可能的思维导图内容
            const mindmapContent = document.querySelector('.agent-response-paragraph')?.innerHTML;
            if (mindmapContent) {
              agentResponseHandlerRef.value.processRenderedHtml(
                mindmapContent, 
                document.querySelector('.agent-response-paragraph')
              );
            }
          }
        } catch (error) {
          console.error('初始化处理代码块时出错:', error);
        }
      }, 1500); // 进一步延长延迟时间，确保初始化完成
    }
  });
});

// 暴露编辑器内容组件方法给父组件
defineExpose({
  focus: () => editorContentRef.value?.focus(),
  getContent: () => props.modelValue,
  setContent: (newContent: string) => {
    emit('update:modelValue', newContent);
  },
  getWordCount: () => wordCount.value
});
</script>

<style scoped>
.editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.editor-main {
  position: relative;
  display: flex;
  flex: 1;
  overflow: hidden;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  padding: 10px 20px;
  border-top: 1px solid #eee;
  color: #888;
  font-size: 14px;
}
</style> 