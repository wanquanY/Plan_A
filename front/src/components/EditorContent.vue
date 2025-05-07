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
  ></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue';
import uploadService from '../services/uploadService';
import { message } from 'ant-design-vue';

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
  
  // 在内容更新后强制运行ensureBottomSpace
  nextTick(() => {
    ensureBottomSpace();
    
    // 查找所有代码块，确保在最后一个代码块后有段落
    setTimeout(() => {
      const codeBlocks = editorRef.value?.querySelectorAll('.code-block-wrapper, pre');
      if (codeBlocks && codeBlocks.length > 0) {
        const lastCodeBlock = codeBlocks[codeBlocks.length - 1];
        let nextElement = lastCodeBlock.nextElementSibling;
        let hasContentAfterCodeBlock = false;
        
        while (nextElement) {
          if (!nextElement.classList.contains('bottom-placeholder')) {
            hasContentAfterCodeBlock = true;
            break;
          }
          nextElement = nextElement.nextElementSibling;
        }
        
        if (!hasContentAfterCodeBlock) {
          const emptyParagraph = document.createElement('p');
          emptyParagraph.innerHTML = '<br>';
          emptyParagraph.className = 'after-code-block-paragraph';
          
          // 获取底部占位元素
          const bottomPlaceholder = editorRef.value.querySelector('.bottom-placeholder');
          
          if (bottomPlaceholder && bottomPlaceholder.parentNode) {
            bottomPlaceholder.parentNode.insertBefore(emptyParagraph, bottomPlaceholder);
          } else {
            editorRef.value.appendChild(emptyParagraph);
          }
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
  
  // 检查是否刚输入了@符号
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
const handleKeyDown = (event: KeyboardEvent) => {
  // 如果正在输入中文，不拦截任何键盘事件
  if (isComposing.value || !editorRef.value) return;
  
  // 检查并防止在只读区域编辑
  if (preventEditInReadOnlyArea(event)) {
    return;
  }
  
  // 处理Tab键
  if (event.key === 'Tab') {
    event.preventDefault(); // 阻止默认的Tab行为（切换焦点）
    
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    
    const range = selection.getRangeAt(0);
    let currentNode = range.commonAncestorContainer;
    
    // 查找当前段落节点
    let paragraphNode = currentNode;
    while (paragraphNode && paragraphNode.nodeName !== 'P') {
      if (paragraphNode.nodeType === 3) { // 文本节点
        paragraphNode = paragraphNode.parentNode;
      } else {
        break;
      }
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
        
        // 保存当前滚动位置
        const scrollTop = editorRef.value.scrollTop;
        const scrollHeight = editorRef.value.scrollHeight;
        
        // 记住当前光标位置的相关信息，以便在内容更新后恢复
        const currentNode = range.startContainer;
        const currentOffset = range.startOffset;
        
        // 为了在更新后能找到同一位置，给最后一个节点添加一个临时标记
        const lastParagraph = getLastParagraph();
        if (lastParagraph) {
          lastParagraph.setAttribute('data-end-marker', 'true');
        }
        
        // 使用setTimeout确保这个事件处理完成后再处理恢复光标位置
        setTimeout(() => {
          // 首先恢复页面滚动位置，防止整个页面跳动
          restorePageScrollPosition(pageScrollPosition);
          
          // 找到带有标记的段落
          const markedParagraph = editorRef.value?.querySelector('[data-end-marker="true"]');
          if (markedParagraph) {
            // 移除标记
            markedParagraph.removeAttribute('data-end-marker');
            
            // 获取下一个段落（即新创建的段落）
            let newParagraph = markedParagraph.nextElementSibling;
            
            // 如果下一个元素不是段落，尝试查找其他新创建的段落
            if (!newParagraph || newParagraph.nodeName !== 'P') {
              const allParagraphs = editorRef.value?.querySelectorAll('p');
              if (allParagraphs && allParagraphs.length > 0) {
                newParagraph = allParagraphs[allParagraphs.length - 1];
              }
            }
            
            // 如果找到新段落，设置光标到它的开始位置
            if (newParagraph) {
              const newRange = document.createRange();
              newRange.setStart(newParagraph, 0);
              newRange.collapse(true);
              
              selection.removeAllRanges();
              selection.addRange(newRange);
              
              // 确保段落可见，但使用更温和的滚动方式
              if (editorRef.value) {
                const editorRect = editorRef.value.getBoundingClientRect();
                const newParagraphRect = newParagraph.getBoundingClientRect();
                
                // 只有当新段落不完全可见时才滚动
                if (newParagraphRect.bottom > editorRect.bottom) {
                  // 使用更温和的滚动方式，避免整页跳动
                  editorRef.value.scrollBy({
                    top: newParagraphRect.bottom - editorRect.bottom + 30, // 额外30px的缓冲空间
                    behavior: 'smooth'
                  });
                }
                
                // 再次确保页面滚动位置不变
                setTimeout(() => {
                  restorePageScrollPosition(pageScrollPosition);
                }, 50);
              }
            }
          }
        }, 0);
      }
      
      // 检查当前段落是否为空
      let node = range.startContainer;
      while (node && node.nodeType !== Node.ELEMENT_NODE) {
        node = node.parentNode;
      }
      
      if (node && (node as HTMLElement).tagName === 'P' && 
          (!node.textContent || node.textContent.trim() === '')) {
        
        // 计算连续空段落的数量
        let emptyParagraphCount = 1; // 当前段落已经是空的
        let prevNode = node.previousSibling;
        
        // 向上计数空段落
        while (prevNode) {
          if (prevNode.nodeType === Node.ELEMENT_NODE && 
              (prevNode as HTMLElement).tagName === 'P' && 
              (!prevNode.textContent || prevNode.textContent.trim() === '')) {
            emptyParagraphCount++;
          } else {
            // 一旦遇到非空段落，停止计数
            break;
          }
          prevNode = prevNode.previousSibling;
        }
        
        // 如果已经有3个或更多连续空段落，阻止创建新段落
        if (emptyParagraphCount >= 3) {
          event.preventDefault();
          console.log('已达到最大空行数量(3)，阻止创建新空行');
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
    
    // 确保末尾有一个可以点击的空白区域
    ensureBottomSpace();
  }
});

// 修改处理编辑器点击事件的函数
const handleEditorClick = (event) => {
  // 跳过如果编辑器不存在
  if (!editorRef.value) return;
  
  const target = event.target;
  
  // 处理底部占位元素的点击
  if (target.classList.contains('bottom-placeholder') || 
      target.closest('.bottom-placeholder')) {
    
    event.preventDefault();
    event.stopPropagation();
    console.log('检测到底部占位区域点击，创建新段落');
    
    // 插入新段落
    insertNewParagraphAtBottom();
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
  
  // 其余的点击处理逻辑保持不变
  // ... existing code ...
};

// 修改确保底部有足够空白区域的函数
const ensureBottomSpace = () => {
  if (!editorRef.value) return;
  
  // 检查是否已经存在底部占位段落
  let bottomPlaceholder = editorRef.value.querySelector('.bottom-placeholder');
  
  // 如果不存在，则创建一个
  if (!bottomPlaceholder) {
    // 创建底部占位元素
    bottomPlaceholder = document.createElement('div');
    bottomPlaceholder.className = 'bottom-placeholder';
    
    // 添加到编辑器末尾
    editorRef.value.appendChild(bottomPlaceholder);
    
    // 为底部占位元素添加点击事件
    bottomPlaceholder.addEventListener('click', (event) => {
      console.log('底部占位元素点击事件触发');
      event.preventDefault();
      event.stopPropagation();
      
      // 创建一个新段落
      insertNewParagraphAtBottom();
    });
  }
  
  // 检查是否有代码块元素
  const codeBlocks = editorRef.value.querySelectorAll('.code-block-wrapper, pre');
  
  // 如果存在代码块，检查最后一个代码块后是否有段落
  if (codeBlocks.length > 0) {
    const lastCodeBlock = codeBlocks[codeBlocks.length - 1];
    
    // 找到这个代码块后的所有兄弟元素
    let nextElement = lastCodeBlock.nextElementSibling;
    let hasContentAfterCodeBlock = false;
    
    // 检查代码块后是否有内容（除了底部占位符）
    while (nextElement) {
      if (!nextElement.classList.contains('bottom-placeholder')) {
        hasContentAfterCodeBlock = true;
        break;
      }
      nextElement = nextElement.nextElementSibling;
    }
    
    // 如果最后一个代码块后没有内容，添加一个新段落
    if (!hasContentAfterCodeBlock) {
      console.log('检测到代码块是最后一个元素，添加一个空段落');
      const emptyParagraph = document.createElement('p');
      emptyParagraph.innerHTML = '<br>';
      emptyParagraph.className = 'after-code-block-paragraph';
      
      // 将空段落插入到代码块后，底部占位符前
      if (bottomPlaceholder.parentNode) {
        bottomPlaceholder.parentNode.insertBefore(emptyParagraph, bottomPlaceholder);
      }
    }
  }
  
  // 确保底部占位符不会被其他操作删除
  setTimeout(() => {
    if (editorRef.value && !editorRef.value.querySelector('.bottom-placeholder')) {
      ensureBottomSpace();
    }
  }, 500);
};

// 修改insertNewParagraphAtBottom函数，大约在730行左右
const insertNewParagraphAtBottom = () => {
  if (!editorRef.value) return;
  
  // 获取底部占位元素
  const bottomPlaceholder = editorRef.value.querySelector('.bottom-placeholder');
  if (!bottomPlaceholder) return;
  
  // 创建新段落
  const newParagraph = document.createElement('p');
  newParagraph.innerHTML = '<br>';
  
  // 插入到底部占位元素之前
  if (bottomPlaceholder.parentNode) {
    bottomPlaceholder.parentNode.insertBefore(newParagraph, bottomPlaceholder);
    
    // 设置光标到新段落
    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(newParagraph);
      range.collapse(true); // 光标在开始位置
      
      selection.removeAllRanges();
      selection.addRange(range);
      
      // 确保编辑器获得焦点
      editorRef.value.focus();
      
      // 使用更温和的滚动行为，避免整页跳动
      const editorRect = editorRef.value.getBoundingClientRect();
      const newParagraphRect = newParagraph.getBoundingClientRect();
      
      // 只有当新段落不完全可见时才滚动
      if (newParagraphRect.bottom > editorRect.bottom) {
        editorRef.value.scrollBy({
          top: newParagraphRect.bottom - editorRect.bottom + 30, // 额外30px的缓冲空间
          behavior: 'smooth'
        });
      }
      
      // 触发内容更新
      emit('update:modelValue', getFullContent());
    }
  }
};

// 添加一个新的辅助函数，确保元素在视口中可见
const ensureElementVisible = (element: HTMLElement) => {
  if (!editorRef.value || !element) return;
  
  const editorRect = editorRef.value.getBoundingClientRect();
  const elementRect = element.getBoundingClientRect();
  
  // 检查元素是否在视口之下（需要向下滚动）
  if (elementRect.bottom > editorRect.bottom) {
    // 使用更温和的滚动方式，避免整页跳动
    editorRef.value.scrollBy({
      top: elementRect.bottom - editorRect.bottom + 30, // 额外30px的缓冲空间
      behavior: 'smooth'
    });
    return;
  }
  
  // 检查元素是否在视口之上（需要向上滚动）
  if (elementRect.top < editorRect.top) {
    // 使用更温和的滚动方式，避免整页跳动
    editorRef.value.scrollBy({
      top: elementRect.top - editorRect.top - 30, // 额外30px的缓冲空间
      behavior: 'smooth'
    });
    return;
  }
  
  // 元素已经可见，不需要滚动
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
</script>

<style scoped>
/* 允许内容溢出，让整个页面负责滚动 */
.editor-content {
  overflow-y: visible;
  min-height: 100%;
  width: 100%;
  outline: none;
  line-height: 1.6;
  font-size: 1rem;
  padding: 0.5em 0;
  color: #333;
}

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

/* 底部占位元素样式 */
.bottom-placeholder {
  height: 200px;
  cursor: text;
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

.agent-response-paragraph::before {
  content: '';
  position: absolute;
  left: -10px;
  height: 100%;
  width: 3px;
  background-color: #1890ff;
  border-radius: 3px;
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
</style> 