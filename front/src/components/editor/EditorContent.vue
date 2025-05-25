<template>
  <div
    ref="editorRef"
    class="editor-content"
    contenteditable="true"
    @input="handleInput"
    @keydown="handleKeyDown"
    @compositionstart="handleCompositionStart"
    @compositionend="handleCompositionEnd"
    @click="handleEditorClick"
    @paste="handlePaste"
    @drop="handleDrop"
  >
    <!-- 在EditorContent内部直接显示输入框 -->
    <div v-if="showAgentInput" class="agent-input-container" :style="agentInputStyle">
      <div class="agent-input-card">
        <div class="agent-input-header">
          <div class="agent-selector">
            <img 
              v-if="selectedAgent" 
              :src="selectedAgent.avatar_url || 'https://placehold.co/20x20?text=AI'" 
              :alt="selectedAgent.name" 
              class="agent-avatar"
            />
            <span class="agent-name">{{ selectedAgent ? selectedAgent.name : '选择AI助手' }}</span>
          </div>
          <button @click="closeAgentInput" class="close-button">×</button>
        </div>
        <div class="agent-input-body">
          <input 
            ref="agentInputRef"
            type="text" 
            class="agent-input-field"
            :placeholder="selectedAgent ? `向${selectedAgent.name}提问...` : '请先选择AI助手...'"
            v-model="agentInputText"
            @keydown.enter="sendToAgent"
            @keydown.esc="closeAgentInput"
          />
          <button 
            class="send-button"
            @click="sendToAgent"
            :disabled="!agentInputText.trim()"
          >
            <svg class="send-icon" viewBox="0 0 24 24" width="16" height="16">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick, computed } from 'vue';
import uploadService from '../../services/uploadService';
import { message } from 'ant-design-vue';
import agentService from '../../services/agent';

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
  'show-agent-modal',
  'composition-start',
  'composition-end',
  'input-update',
  'send-to-agent'
]);

const editorRef = ref<HTMLElement | null>(null);
const isComposing = ref(false);

// Agent输入框相关状态
const showAgentInput = ref(false);
const agentInputText = ref('');
const selectedAgent = ref(null);
const agents = ref([]);
const cursorPosition = ref({ x: 0, y: 0 });
const activeRange = ref(null);
const agentInputRef = ref(null);

// 计算输入框位置样式
const agentInputStyle = computed(() => {
  return {
    position: 'absolute',
    top: `${cursorPosition.value.y}px`,
    left: 0,
    right: 0,
    width: '100%',
    zIndex: 100
  };
});

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
  
  // 在内容更新后处理代码块后的段落
  nextTick(() => {
    // 确保标题占位符是空的
    const titlePlaceholder = editorRef.value?.querySelector('.title-placeholder');
    if (titlePlaceholder && titlePlaceholder.innerHTML.trim() !== '') {
      console.log('updateEditorContent: 清空标题占位符内容');
      titlePlaceholder.innerHTML = '';
    }
    
    // 查找所有代码块，确保在最后一个代码块后有段落
    setTimeout(() => {
      const codeBlocks = editorRef.value?.querySelectorAll('.code-block-wrapper, pre');
      if (codeBlocks && codeBlocks.length > 0) {
        const lastCodeBlock = codeBlocks[codeBlocks.length - 1];
        let nextElement = lastCodeBlock.nextElementSibling;
        let hasContentAfterCodeBlock = false;
        
        while (nextElement) {
          hasContentAfterCodeBlock = true;
          break;
        }
        
        if (!hasContentAfterCodeBlock) {
          const emptyParagraph = document.createElement('p');
          emptyParagraph.innerHTML = '<br>';
          emptyParagraph.className = 'after-code-block-paragraph';
          
          // 直接添加到编辑器末尾
          editorRef.value.appendChild(emptyParagraph);
        }
      }
    }, 200);
  });
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
  
  // 处理标题占位符的特殊逻辑
  const titlePlaceholder = editorRef.value.querySelector('.title-placeholder');
  if (titlePlaceholder) {
    const titleContent = titlePlaceholder.textContent || '';
    
    // 如果用户在标题占位符中输入了内容
    if (titleContent && titleContent.trim() !== '') {
      // 移除占位符类，让它变成正常的标题
      titlePlaceholder.classList.remove('title-placeholder');
      titlePlaceholder.removeAttribute('data-placeholder');
    } else if (!titleContent || titleContent.trim() === '') {
      // 如果内容为空，确保占位符样式正确
      titlePlaceholder.classList.add('title-placeholder');
      titlePlaceholder.setAttribute('data-placeholder', '请输入标题');
      // 清空内容，让CSS伪元素显示占位符
      titlePlaceholder.innerHTML = '';
    }
  }
  
  // 保存当前滚动位置
  const scrollTop = editorRef.value.scrollTop;
  const scrollHeight = editorRef.value.scrollHeight;
  
  // 保存当前选择范围
  const selection = window.getSelection();
  const range = selection && selection.rangeCount ? selection.getRangeAt(0) : null;
  
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
  
  // 检查是否刚输入了/符号
  if (selection && selection.rangeCount > 0 && !props.showAgentSelector) {
    const range = selection.getRangeAt(0);
    
    // 处理文本节点
    if (range.startContainer.nodeType === Node.TEXT_NODE) {
      const textContent = range.startContainer.textContent || '';
      const offset = range.startOffset;
      
      // 检查光标前面的字符是否是/
      if (offset > 0 && textContent[offset - 1] === '/') {
        console.log('检测到/符号，触发选择器显示');
        emit('show-agent-selector', range);
      }
    }
  }
  
  // 在更新完成后恢复滚动位置
  nextTick(() => {
    if (editorRef.value) {
      // 首先恢复滚动位置
      editorRef.value.scrollTop = scrollTop;
      
      // 如果有选择范围，并且在编辑器底部，确保光标可见
      if (range) {
        const container = range.startContainer;
        let node = container;
        
        // 查找包含节点的元素
        while (node && node.nodeType !== Node.ELEMENT_NODE) {
          node = node.parentNode;
        }
        
        if (node && editorRef.value.contains(node) && node !== editorRef.value) {
          // 如果节点在编辑器底部，确保它可见
          const nodeRect = (node as HTMLElement).getBoundingClientRect();
          const editorRect = editorRef.value.getBoundingClientRect();
          
          // 计算需要滚动的距离
          if (nodeRect.bottom > editorRect.bottom) {
            // 向下滚动，但使用更温和的方式
            editorRef.value.scrollBy({
              top: nodeRect.bottom - editorRect.bottom + 30,
              behavior: 'smooth'
            });
          } else if (nodeRect.top < editorRect.top) {
            // 向上滚动，但使用更温和的方式
            editorRef.value.scrollBy({
              top: nodeRect.top - editorRect.top - 30,
              behavior: 'smooth'
            });
          }
        }
      }
    }
  });
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
const handleKeyDown = (event) => {
  // 优先处理/符号
  if (event.key === '/' && event.currentTarget.classList.contains('editor-content')) {
    if (handleSlashSymbol(event)) {
      return; // 已处理/键，不需要继续处理
    }
  }

  // 如果正在中文输入或编辑器不存在，不处理特殊键
  if (isComposing.value || !editorRef.value) {
    emit('key-down', {
      event,
      editorRef: editorRef.value,
      selection: window.getSelection()
    });
    return;
  }
   
  // 检查并防止在只读区域编辑
  if (preventEditInReadOnlyArea(event)) {
    return;
  }
  
  // 处理Tab键
  if (event.key === 'Tab') {
    event.preventDefault(); // 阻止默认的Tab行为
    
    // 获取当前选中的范围
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    
    const range = selection.getRangeAt(0);
    
    // 获取当前光标所在的段落
    let paragraphNode = range.startContainer;
    while (paragraphNode && paragraphNode.nodeName !== 'P') {
      paragraphNode = paragraphNode.parentNode;
    }
    
    // 只处理段落节点
    if (paragraphNode && paragraphNode.nodeName === 'P') {
      if (event.shiftKey) {
        // 如果按下Shift+Tab，则减少缩进
        const currentIndent = parseInt(window.getComputedStyle(paragraphNode).paddingLeft) || 0;
        if (currentIndent >= 40) { // 如果当前缩进至少是40px
          paragraphNode.style.paddingLeft = `${currentIndent - 40}px`;
        } else if (currentIndent > 0) {
          // 完全移除缩进
          paragraphNode.style.paddingLeft = '';
        }
      } else {
        // 单独按Tab键，增加缩进
        const currentIndent = parseInt(window.getComputedStyle(paragraphNode).paddingLeft) || 0;
        // 每次增加40px的缩进（可根据需要调整）
        paragraphNode.style.paddingLeft = `${currentIndent + 40}px`;
      }
      
      // 触发内容更新
      setTimeout(() => {
        emit('update:modelValue', getFullContent());
      }, 0);
    }
    
    return; // 已处理Tab键，不需要继续处理
  }
  
  // 处理在文档末尾的回车键
  if (event.key === 'Enter' && !event.shiftKey) {
    // 保存页面当前的滚动位置
    const pageScrollPosition = savePageScrollPosition();
    
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      
      // 检查光标是否在文档末尾
      const isAtEnd = isSelectionAtDocumentEnd(selection);
      
      if (isAtEnd) {
        console.log('检测到在文档末尾按回车键');
        
        // 阻止默认的回车行为，手动处理插入新段落
        event.preventDefault();
        
        // 保存当前滚动位置
        const scrollTop = editorRef.value.scrollTop;
        
        // 创建新段落
        const newParagraph = document.createElement('p');
        newParagraph.innerHTML = '<br>';
        
        // 为了在更新后能找到同一位置，给最后一个节点添加一个临时标记
        const lastParagraph = getLastParagraph();
        if (lastParagraph) {
          lastParagraph.setAttribute('data-end-marker', 'true');
          
          // 在最后一个段落后插入新段落
          if (lastParagraph.parentNode) {
            lastParagraph.parentNode.insertBefore(newParagraph, lastParagraph.nextSibling);
          }
        } else {
          // 如果找不到最后一个段落，直接添加到编辑区
          const editableContent = editorRef.value.querySelector('.editable-content') || editorRef.value;
          editableContent.appendChild(newParagraph);
        }
        
        // 更新编辑器内容
        emit('update:modelValue', getFullContent());
        
        // 使用setTimeout确保这个事件处理完成后再处理恢复光标位置
        setTimeout(() => {
          // 将光标设置到新段落
          const selection = window.getSelection();
          if (selection) {
            const range = document.createRange();
            range.setStart(newParagraph, 0);
            range.collapse(true);
            
            selection.removeAllRanges();
            selection.addRange(range);
          }
          
          // 找到带有标记的段落并移除标记
          const markedParagraph = editorRef.value?.querySelector('[data-end-marker="true"]');
          if (markedParagraph) {
            markedParagraph.removeAttribute('data-end-marker');
          }
          
          // 确保新段落可见
          const newParagraphRect = newParagraph.getBoundingClientRect();
          const viewportHeight = window.innerHeight;
          
          // 只有当新段落不完全可见时才滚动
          if (newParagraphRect.bottom > viewportHeight) {
            window.scrollTo({
              top: pageScrollPosition.y + (newParagraphRect.bottom - viewportHeight) + 30,
              behavior: 'auto' // 使用auto而非smooth，避免动画过程中的闪烁
            });
          } else {
            // 确保页面不会滚动到顶部
            window.scrollTo(pageScrollPosition.x, pageScrollPosition.y);
          }
          
          // 确保编辑器获得焦点
          editorRef.value.focus();
        }, 10);
        
        return; // 已处理回车键，不需要继续处理
      }
      
      // 检查当前段落是否为空
      let node = range.startContainer;
      while (node && node.nodeType !== Node.ELEMENT_NODE) {
        node = node.parentNode;
      }
      
      // 移除空行限制，允许用户创建任意数量的空行
      // 原有的空行限制逻辑已被移除，用户可以自由创建空段落
    }
  }
  
  // 转发键盘事件
  emit('key-down', {
    event,
    editorRef: editorRef.value,
    selection: window.getSelection()
  });
};

// 修改isSelectionAtDocumentEnd函数，使其更准确地判断光标是否在文档末尾
const isSelectionAtDocumentEnd = (selection) => {
  if (!selection || selection.rangeCount === 0 || !editorRef.value) return false;
  
  const range = selection.getRangeAt(0);
  const lastParagraph = getLastParagraph();
  
  if (!lastParagraph) return false;
  
  // 检查光标是否在最后一个段落内
  let node = range.startContainer;
  let isInLastParagraph = false;
  
  // 向上查找，检查是否在最后一个段落内
  while (node && node !== editorRef.value) {
    if (node === lastParagraph) {
      isInLastParagraph = true;
      break;
    }
    node = node.parentNode;
  }
  
  if (!isInLastParagraph) return false;
  
  // 检查是否在最后一个位置
  if (range.startContainer.nodeType === Node.TEXT_NODE) {
    // 光标在文本节点中，检查是否在文本末尾
    return range.startOffset === (range.startContainer.textContent || '').length;
  } else if (range.startContainer === lastParagraph) {
    // 光标在段落节点中，检查是否在最后一个子节点之后
    return range.startOffset === range.startContainer.childNodes.length;
  } else {
    // 其他情况，可能是在段落内的某个元素中
    // 检查当前元素是否是最后一个元素
    const lastNode = lastParagraph.lastChild;
    return range.startContainer === lastNode && 
           range.startOffset === (lastNode.nodeType === Node.TEXT_NODE ? lastNode.length : lastNode.childNodes.length);
  }
};

// 保存当前页面滚动位置的函数
const savePageScrollPosition = () => {
  return {
    x: window.pageXOffset || document.documentElement.scrollLeft,
    y: window.pageYOffset || document.documentElement.scrollTop
  };
};

// 恢复页面滚动位置的函数
const restorePageScrollPosition = (position) => {
  window.scrollTo(position.x, position.y);
};

// 添加一个辅助函数，获取文档中的最后一个段落
const getLastParagraph = () => {
  if (!editorRef.value) return null;
  
  // 获取所有段落
  const paragraphs = editorRef.value.querySelectorAll('p');
  
  // 返回最后一个段落，如果没有则返回null
  return paragraphs.length > 0 ? paragraphs[paragraphs.length - 1] : null;
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

// 聚焦到标题占位符
const focusTitle = () => {
  if (!editorRef.value) return;
  
  const titlePlaceholder = editorRef.value.querySelector('.title-placeholder');
  if (titlePlaceholder) {
    // 确保标题占位符为空
    if (titlePlaceholder.innerHTML !== '') {
      titlePlaceholder.innerHTML = '';
    }
    
    // 设置光标到标题开始位置
    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(titlePlaceholder);
      range.collapse(true);
      
      selection.removeAllRanges();
      selection.addRange(range);
    }
    
    // 聚焦到标题元素
    titlePlaceholder.focus();
    
    console.log('已聚焦到标题占位符');
  }
};

// 暴露方法和引用
defineExpose({
  editorRef,
  focus: () => editorRef.value?.focus(),
  setReadOnlyContent,
  focusTitle
});

// 直接DOM事件监听器，确保不会错过input事件
onMounted(() => {
  if (editorRef.value) {
    updateEditorContent(props.modelValue);
    countWords();
    
    // 确保标题占位符是空的，让CSS伪元素显示
    nextTick(() => {
      const titlePlaceholder = editorRef.value?.querySelector('.title-placeholder');
      if (titlePlaceholder) {
        console.log('检查标题占位符元素:', titlePlaceholder);
        console.log('标题占位符内容:', titlePlaceholder.innerHTML);
        console.log('标题占位符属性:', titlePlaceholder.getAttribute('data-placeholder'));
        
        // 如果标题占位符不为空，清空它
        if (titlePlaceholder.innerHTML.trim() !== '') {
          console.log('清空标题占位符内容');
          titlePlaceholder.innerHTML = '';
        }
        
        // 确保有data-placeholder属性
        if (!titlePlaceholder.getAttribute('data-placeholder')) {
          titlePlaceholder.setAttribute('data-placeholder', '请输入标题');
        }
        
        // 自动聚焦到标题占位符，让真实光标在标题位置闪烁
        setTimeout(() => {
          focusTitle();
        }, 100); // 稍微延迟确保DOM完全渲染
      }
    });
    
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

// 修改处理编辑器点击事件的函数
const handleEditorClick = (event) => {
  // 跳过如果编辑器不存在
  if (!editorRef.value) return;
  
  const target = event.target;
  
  // 处理标题占位符点击
  if (target.classList.contains('title-placeholder')) {
    // 确保标题占位符为空，让CSS伪元素显示占位符
    if (target.innerHTML !== '') {
      target.innerHTML = '';
    }
    
    // 设置光标到标题开始位置
    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(target);
      range.collapse(true);
      
      selection.removeAllRanges();
      selection.addRange(range);
    }
    
    // 确保编辑器获得焦点
    target.focus();
    return;
  }
  
  // 处理代码块后的段落点击
  if (target.classList.contains('after-code-block-paragraph') ||
      target.closest('.after-code-block-paragraph')) {
    
    const paragraph = target.classList.contains('after-code-block-paragraph') 
                     ? target 
                     : target.closest('.after-code-block-paragraph');
    
    // 设置光标到这个段落
    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(paragraph);
      range.collapse(true); // 光标在开始位置
      
      selection.removeAllRanges();
      selection.addRange(range);
      
      // 确保编辑器获得焦点
      editorRef.value.focus();
    }
    return;
  }
  
  // 其他正常的点击处理，让浏览器处理光标位置
};

// 加载Agent列表
const loadAgents = async () => {
  try {
    const agentList = await agentService.getAllAgents();
    agents.value = agentList;
    
    // 默认选择第一个Agent
    if (agentList.length > 0 && !selectedAgent.value) {
      selectedAgent.value = agentList[0];
    }
  } catch (error) {
    console.error('加载AI助手列表失败:', error);
  }
};

// 显示Agent输入框
const showAgentInputAt = (position, range) => {
  // 保存当前位置和Range
  cursorPosition.value = position;
  activeRange.value = range;
  
  // 显示输入框
  showAgentInput.value = true;
  
  // 加载Agent列表
  if (agents.value.length === 0) {
    loadAgents();
  }
  
  // 输入框聚焦
  nextTick(() => {
    agentInputRef.value?.focus();
  });
};

// 关闭Agent输入框
const closeAgentInput = () => {
  showAgentInput.value = false;
  agentInputText.value = '';
};

// 发送消息到Agent
const sendToAgent = () => {
  if (!agentInputText.value.trim() || !selectedAgent.value) return;
  
  // 传递给父组件处理发送逻辑
  emit('send-to-agent', {
    agentId: selectedAgent.value.id,
    content: agentInputText.value.trim(),
    range: activeRange.value
  });
  
  // 关闭输入框
  closeAgentInput();
};

// 处理粘贴事件
const handlePaste = async (event) => {
  // 检查是否在只读区域内
  if (preventEditInReadOnlyArea(event)) {
    return;
  }

  // 检查剪贴板中是否有图片
  const clipboardItems = event.clipboardData?.items;
  if (!clipboardItems) return;

  let hasImage = false;

  for (let i = 0; i < clipboardItems.length; i++) {
    const item = clipboardItems[i];
    
    // 检查是否为图片类型
    if (item.type.indexOf('image') !== -1) {
      hasImage = true;
      
      // 阻止默认粘贴行为
      event.preventDefault();
      
      // 显示加载提示
      message.loading({content: '正在上传图片...', key: 'imageUpload', duration: 0});
      
      try {
        // 从剪贴板获取图片文件
        const file = item.getAsFile();
        
        // 设置加载中的占位图
        const placeholderId = `img-upload-${Date.now()}`;
        insertImagePlaceholder(placeholderId);
        
        // 上传图片
        const imageUrl = await uploadService.uploadImage(file);
        
        // 将占位符替换为实际图片
        replacePlaceholderWithImage(placeholderId, imageUrl);
        
        // 提示上传成功
        message.success({content: '图片上传成功', key: 'imageUpload'});
      } catch (error) {
        console.error('图片粘贴处理失败:', error);
        message.error({content: '图片上传失败', key: 'imageUpload'});
        
        // 移除占位符
        removePlaceholder();
      }
      
      break;
    }
  }
  
  // 如果没有图片，让浏览器处理默认粘贴行为
  if (!hasImage) {
    // 处理纯文本粘贴，避免粘贴带有样式的内容
    handleTextPaste(event);
  }
};

// 处理纯文本粘贴
const handleTextPaste = (event) => {
  // 获取纯文本
  const text = event.clipboardData.getData('text/plain');
  
  // 如果没有文本，使用默认行为
  if (!text) return;
  
  // 阻止默认粘贴行为
  event.preventDefault();
  
  // 使用execCommand粘贴纯文本
  document.execCommand('insertText', false, text);
};

// 处理拖放事件
const handleDrop = async (event) => {
  // 检查是否在只读区域内
  if (preventEditInReadOnlyArea(event)) {
    return;
  }

  // 检查是否拖放的是文件
  const files = event.dataTransfer?.files;
  if (!files || files.length === 0) return;

  // 检查是否为图片
  const file = files[0];
  if (!file.type.startsWith('image/')) return;
  
  // 阻止默认行为
  event.preventDefault();
  event.stopPropagation();
  
  // 显示加载提示
  message.loading({content: '正在上传图片...', key: 'imageUpload', duration: 0});
  
  try {
    // 设置加载中的占位图
    const placeholderId = `img-upload-${Date.now()}`;
    insertImagePlaceholder(placeholderId);
    
    // 上传图片
    const imageUrl = await uploadService.uploadImage(file);
    
    // 将占位符替换为实际图片
    replacePlaceholderWithImage(placeholderId, imageUrl);
    
    // 提示上传成功
    message.success({content: '图片上传成功', key: 'imageUpload'});
  } catch (error) {
    console.error('图片拖放处理失败:', error);
    message.error({content: '图片上传失败', key: 'imageUpload'});
    
    // 移除占位符
    removePlaceholder();
  }
};

// 插入图片占位符
const insertImagePlaceholder = (id) => {
  // 确保有光标位置
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return;
  
  const range = selection.getRangeAt(0);
  
  // 创建加载占位符元素
  const placeholder = document.createElement('div');
  placeholder.id = id;
  placeholder.className = 'image-upload-placeholder';
  placeholder.innerHTML = `
    <div class="upload-spinner"></div>
    <div class="upload-text">图片上传中...</div>
  `;
  
  // 插入占位符
  range.insertNode(placeholder);
  
  // 移动光标到占位符后面
  range.setStartAfter(placeholder);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
  
  // 触发更新
  emit('update:modelValue', getFullContent());
};

// 将占位符替换为实际图片
const replacePlaceholderWithImage = (placeholderId, imageUrl) => {
  const placeholder = document.getElementById(placeholderId);
  if (!placeholder) return;
  
  // 创建图片元素
  const imgContainer = document.createElement('div');
  imgContainer.className = 'resizable-image-container';
  imgContainer.contentEditable = 'false';
  
  const img = document.createElement('img');
  img.src = imageUrl;
  img.alt = '用户上传的图片';
  img.className = 'resizable-image';
  
  // 添加调整大小的手柄
  const resizeHandle = document.createElement('div');
  resizeHandle.className = 'resize-handle';
  
  imgContainer.appendChild(img);
  imgContainer.appendChild(resizeHandle);
  
  // 替换占位符
  placeholder.parentNode.replaceChild(imgContainer, placeholder);
  
  // 添加调整大小的事件处理
  setupImageResizing(imgContainer, img);
  
  // 触发更新
  emit('update:modelValue', getFullContent());
};

// 移除占位符
const removePlaceholder = () => {
  const placeholders = document.querySelectorAll('.image-upload-placeholder');
  placeholders.forEach(p => p.remove());
  
  // 触发更新
  emit('update:modelValue', getFullContent());
};

// 设置图片缩放功能
const setupImageResizing = (container, img) => {
  const resizeHandle = container.querySelector('.resize-handle');
  if (!resizeHandle || !img) return;
  
  let startX, startY, startWidth, startHeight;
  let isResizing = false;
  
  // 鼠标按下事件
  const onMouseDown = (e) => {
    isResizing = true;
    startX = e.clientX;
    startY = e.clientY;
    startWidth = img.offsetWidth;
    startHeight = img.offsetHeight;
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    
    e.preventDefault();
    e.stopPropagation();
  };
  
  // 鼠标移动事件
  const onMouseMove = (e) => {
    if (!isResizing) return;
    
    // 计算新尺寸
    const deltaX = e.clientX - startX;
    const newWidth = startWidth + deltaX;
    
    // 计算等比例的高度
    const aspectRatio = startHeight / startWidth;
    const newHeight = newWidth * aspectRatio;
    
    // 应用新尺寸
    if (newWidth > 100) {
      img.style.width = `${newWidth}px`;
      img.style.height = `${newHeight}px`;
    }
    
    e.preventDefault();
  };
  
  // 鼠标松开事件
  const onMouseUp = (e) => {
    isResizing = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    
    // 更新编辑器内容以保存尺寸
    emit('update:modelValue', getFullContent());
    e.preventDefault();
  };
  
  // 添加事件监听
  resizeHandle.addEventListener('mousedown', onMouseDown);
};

// 处理/符号
const handleSlashSymbol = (event) => {
  console.log('检测到/键被按下，准备触发输入框');
  event.preventDefault(); // 阻止默认/符号插入
  
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return false;
  
  const originalRange = selection.getRangeAt(0);
  
  try {
    // 先克隆原始范围，避免后续操作影响它
    const savedRange = originalRange.cloneRange();
    
    // 创建一个独立的范围用于插入临时标记
    const tempRange = originalRange.cloneRange();
    
    // 创建临时标记用于获取准确位置
    const tempSpan = document.createElement('span');
    tempSpan.id = 'temp-cursor-marker';
    tempSpan.style.position = 'absolute';
    tempSpan.style.width = '1px';
    tempSpan.style.height = '1px';
    tempSpan.style.opacity = '0';
    
    // 插入临时标记到光标位置
    tempRange.insertNode(tempSpan);
    
    // 获取标记位置（相对于视口）
    const markerRect = tempSpan.getBoundingClientRect();
    
    // 获取编辑器位置（相对于视口）
    const editorRect = editorRef.value.getBoundingClientRect();
    
    // 获取编辑器的offsetParent以计算正确的offsetLeft
    const editorOffsetLeft = editorRef.value.offsetLeft;
    
    // 计算编辑区域中的实际可编辑宽度信息
    const editorContent = {
      left: editorRect.left,
      right: editorRect.right,
      width: editorRect.width,
      editorOffsetLeft: editorOffsetLeft
    };
    
    console.log('光标位置信息:', {
      markerPosition: { x: markerRect.left, y: markerRect.bottom },
      editorPosition: { left: editorRect.left, right: editorRect.right, width: editorRect.width },
      editorOffset: editorOffsetLeft
    });
    
    // 立即移除临时标记
    if (tempSpan.parentNode) {
      tempSpan.parentNode.removeChild(tempSpan);
    }
    
    // 恢复原始选区到保存的位置
    selection.removeAllRanges();
    selection.addRange(savedRange);
    
    // 发送事件显示弹窗在光标所在行下方，传递保存的范围
    emit('show-agent-modal', { 
      range: savedRange, // 传递保存的原始范围
      cursorPosition: {
        // 提供绝对位置（相对于视口）
        viewport: {
          y: markerRect.bottom,
          x: markerRect.left
        },
        // 提供相对位置（相对于编辑器）
        editor: {
          y: markerRect.bottom - editorRect.top,
          x: markerRect.left - editorRect.left
        }
      },
      editorInfo: editorContent
    });
    
    return true;
  } catch (error) {
    console.error('计算光标位置时出错:', error);
    
    // 备用方案：使用原始范围和鼠标事件坐标
    const editorRect = editorRef.value.getBoundingClientRect();
    const editorOffsetLeft = editorRef.value.offsetLeft;
    const backupRange = originalRange.cloneRange();
    
    emit('show-agent-modal', { 
      range: backupRange, // 使用备用的原始范围克隆
      cursorPosition: {
        viewport: {
          y: event.clientY || 0,
          x: event.clientX || 0
        },
        editor: {
          y: (event.clientY || 0) - editorRect.top,
          x: (event.clientX || 0) - editorRect.left
        }
      },
      editorInfo: {
        left: editorRect.left,
        right: editorRect.right,
        width: editorRect.width,
        editorOffsetLeft: editorOffsetLeft
      }
    });
    
    return true;
  }
};
</script>

<style scoped>
/* 标题占位符样式 */
.title-placeholder {
  position: relative;
  font-size: 28px !important;
  font-weight: 600 !important;
  margin: 0 0 20px 0 !important;
  padding: 10px 0 !important;
  border: none !important;
  outline: none !important;
  background: transparent !important;
  line-height: 1.2 !important;
  min-height: 1.2em; /* 确保有足够的高度 */
  color: #333 !important; /* 改为正常颜色，让真实光标可见 */
  display: block !important; /* 确保显示为块级元素 */
}

/* 使用伪元素显示占位符文本 */
.editor-content .title-placeholder:empty::before {
  content: attr(data-placeholder) !important;
  color: #999 !important;
  font-style: italic !important;
  position: absolute !important;
  left: 0 !important;
  top: 10px !important;
  pointer-events: none !important; /* 不可选中 */
  user-select: none !important; /* 不可选中 */
  z-index: 0 !important; /* 降低层级，让真实光标显示在上方 */
  display: block !important;
  font-size: 28px !important;
  font-weight: 600 !important;
  line-height: 1.2 !important;
}

/* 备用选择器，确保占位符能显示 */
h1.title-placeholder:empty::before {
  content: "请输入标题" !important;
  color: #999 !important;
  font-style: italic !important;
  position: absolute !important;
  left: 0 !important;
  top: 10px !important;
  pointer-events: none !important;
  user-select: none !important;
  z-index: 0 !important; /* 降低层级，让真实光标显示在上方 */
  display: block !important;
  font-size: 28px !important;
  font-weight: 600 !important;
  line-height: 1.2 !important;
}

/* 聚焦时的占位符样式 */
.editor-content .title-placeholder:focus:empty::before {
  color: #ccc !important; /* 聚焦时占位符更淡，突出真实光标 */
}

/* 当标题有内容时的样式 */
.title-placeholder:not(:empty) {
  color: #333 !important;
  font-style: normal !important;
}

/* 确保聚焦时有光标 */
.title-placeholder:focus {
  color: #333 !important;
  font-style: normal !important;
}

/* 当有内容时隐藏伪元素 */
.title-placeholder:not(:empty)::before {
  display: none !important;
}

/* 编辑器内容区域样式 */
.editor-content {
  flex: 1;
  overflow: visible; /* 保持visible，让父容器处理滚动 */
  min-height: auto; /* 改为auto，不强制100%高度 */
  width: 100%;
  outline: none;
  line-height: 1.6;
  font-size: 1rem;
  color: #333;
  padding: 50px 80px 100px 80px; /* 保持底部内边距 */
  background-color: #fff;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.05);
  border-radius: 0 4px 4px 0;
  position: relative; /* 确保相对定位，作为绝对定位元素的参考 */
  max-height: none; /* 移除高度限制 */
  z-index: 1; /* 确保有正确的层叠顺序 */
}

/* 响应式样式 */
@media (min-width: 1200px) {
  .editor-content {
    padding: 50px 100px 20px 100px;
  }
}

@media (max-width: 768px) {
  .editor-content {
    padding: 50px 30px 20px 30px;
  }
}

/* 不可编辑区域样式 */
.read-only-content {
  color: #666;
  background-color: #f8f9fa;
  padding: 1em;
  margin-bottom: 1em;
  border-left: 3px solid #007bff;
  border-radius: 0 4px 4px 0;
  position: relative;
}

.read-only-content:after {
  content: '';
  display: block;
  height: 1px;
  margin-top: 1em;
  background: linear-gradient(to right, rgba(0, 0, 0, 0.12), transparent);
}

.editable-content {
  padding-top: 1em;
  min-height: 100px;
}

.editable-content p:last-child {
  margin-bottom: 200px;
}

/* 底部占位元素样式 - 移除 */

/* 图片上传占位符样式 */
:deep(.image-upload-placeholder) {
  width: 300px;
  height: 150px;
  background-color: #f5f7fa;
  border: 2px dashed #d9e1ec;
  border-radius: 8px;
  margin: 10px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

:deep(.upload-spinner) {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(0, 123, 255, 0.2);
  border-top-color: #007bff;
  border-radius: 50%;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

:deep(.upload-text) {
  color: #6c757d;
  font-size: 14px;
}

/* 可调整大小的图片容器样式 */
:deep(.resizable-image-container) {
  position: relative;
  display: inline-block;
  margin: 10px 0;
  clear: both;
}

:deep(.resizable-image) {
  max-width: 100%;
  height: auto;
  display: block;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: default;
}

:deep(.resize-handle) {
  position: absolute;
  width: 10px;
  height: 10px;
  background-color: #ffffff;
  border: 1px solid #007bff;
  border-radius: 2px;
  bottom: -5px;
  right: -5px;
  cursor: nwse-resize;
  z-index: 100;
}

:deep(.resizable-image-container:hover .resize-handle) {
  display: block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 气泡式加载指示器 */
.typing-indicator {
  display: inline-flex;
  align-items: center;
  background: #f0f0f0;
  padding: 0.5em 1em;
  border-radius: 1em;
  margin-top: 0.5em;
  color: #666;
  animation: fade 0.3s;
}

.typing-dots {
  display: inline-flex;
  margin-right: 5px;
}

.dot {
  width: 6px;
  height: 6px;
  background: #666;
  border-radius: 50%;
  margin: 0 1px;
  animation: jump 1.4s infinite;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes jump {
  0%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-8px);
  }
}

@keyframes fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 用户提及样式 */
.user-mention {
  background-color: rgba(0, 123, 255, 0.08);
  color: #1890ff;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.agent-response-paragraph {
  margin-top: 1em;
  position: relative;
  padding-left: 4px;
}

/* 确保段落内容中的代码块能够正确显示 */
.agent-response-paragraph pre {
  margin: 1em 0;
  padding: 1em;
  background-color: #f6f8fa;
  border-radius: 6px;
  overflow-x: auto;
  position: relative;
}

.agent-response-paragraph pre code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  font-size: 90%;
  color: #333;
}

/* 代码块语言标识 */
.agent-response-paragraph pre[data-language]:before {
  content: attr(data-language);
  position: absolute;
  top: 0;
  right: 0;
  padding: 3px 8px;
  font-size: 12px;
  color: #666;
  background-color: #f6f8fa;
  border-bottom-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom: 1px solid #e1e4e8;
  border-left: 1px solid #e1e4e8;
}

/* 代码块复制按钮 */
.code-copy-button {
  position: absolute;
  top: 5px;
  right: 5px;
  padding: 4px 8px;
  font-size: 12px;
  color: #666;
  background-color: rgba(255, 255, 255, 0.8);
  border: 1px solid #e1e4e8;
  border-radius: 4px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.agent-response-paragraph pre:hover .code-copy-button {
  opacity: 1;
}

.code-copy-button:hover {
  background-color: #fff;
  color: #333;
}

.code-copy-button.copied {
  color: #28a745;
  border-color: #28a745;
}

/* 调整代码块后的段落边距 */
.after-code-block-paragraph {
  margin-top: 1em;
}

/* Agent输入框样式 */
.agent-input-container {
  padding: 0 10px;
  box-sizing: border-box;
  position: absolute; /* 使用绝对定位 */
  left: 0;
  right: 0;
  z-index: 1000; /* 确保显示在编辑内容上方 */
}

.agent-input-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  border: 1px solid #e0e3e9;
  margin: 4px 0;
  animation: slideIn 0.2s ease;
}

.agent-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background-color: #f9f9f9;
  border-bottom: 1px solid #f0f0f0;
}

.agent-selector {
  display: flex;
  align-items: center;
}

.agent-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  margin-right: 8px;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}

.agent-input-body {
  display: flex;
  align-items: center;
  padding: 8px 12px;
}

.agent-input-field {
  flex: 1;
  border: none;
  background-color: #f5f7fa;
  border-radius: 20px;
  padding: 8px 12px;
  height: 36px;
  font-size: 14px;
  outline: none;
}

.agent-input-field:focus {
  background-color: #e8f0fe;
}

.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1677ff;
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  margin-left: 8px;
  cursor: pointer;
}

.send-button:disabled {
  background-color: #b8d2f8;
  cursor: not-allowed;
}

@keyframes slideIn {
  from { 
    opacity: 0; 
    transform: translateY(-10px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

<style>
/* 全局样式，确保标题占位符能正确显示 */
.title-placeholder {
  position: relative !important;
  font-size: 28px !important;
  font-weight: 600 !important;
  margin: 0 0 20px 0 !important;
  padding: 10px 0 !important;
  border: none !important;
  outline: none !important;
  background: transparent !important;
  line-height: 1.2 !important;
  min-height: 1.2em !important;
  color: #333 !important; /* 改为正常颜色，让真实光标可见 */
  display: block !important;
}

.title-placeholder:empty::before {
  content: attr(data-placeholder) !important;
  color: #999 !important;
  font-style: italic !important;
  position: absolute !important;
  left: 0 !important;
  top: 10px !important;
  pointer-events: none !important;
  user-select: none !important;
  z-index: 0 !important; /* 降低层级，让真实光标显示在上方 */
  display: block !important;
  font-size: 28px !important;
  font-weight: 600 !important;
  line-height: 1.2 !important;
}

.title-placeholder:focus:empty::before {
  color: #ccc !important; /* 聚焦时占位符更淡，突出真实光标 */
}

.title-placeholder:not(:empty) {
  color: #333 !important;
  font-style: normal !important;
}

.title-placeholder:focus {
  color: #333 !important;
  font-style: normal !important;
}

.title-placeholder:not(:empty)::before {
  display: none !important;
}
</style> 