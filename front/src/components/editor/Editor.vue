<template>
  <div class="editor-container">
    <EditorToolbar
      class="editor-toolbar-fixed"
      :editor-ref="editorContentRef?.editorRef"
      :selected-heading="selectedHeading"
      :interaction-mode="interactionMode"
      @apply-formatting="applyFormat"
      @set-heading="setHeading"
      @set-letter-spacing="setLetterSpacing"
      @set-line-height="setLineHeight"
      @set-font-size="setFontSize"
      @undo="undoAction"
      @redo="redoAction"
      @toggle-outline="toggleOutline"
      @toggle-sidebar-mode="toggleSidebarMode"
    />
    
    <div class="editor-content-wrapper">
      <DocumentOutline 
        v-if="showOutline && editorContentRef" 
        :editorRef="editorContentRef" 
        class="document-outline"
        ref="documentOutlineRef"
      />
      
      <div class="editor-main">
        <EditorContent
          ref="editorContentRef"
          :modelValue="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          :show-agent-selector="showAgentSelector"
          @word-count="updateWordCount"
          @key-down="handleKeyDown"
          @show-agent-selector="showAgentSelectorAt"
          @show-agent-modal="showAgentModalAt"
          @send-to-agent="handleSendToAgent"
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
    </div>
    
    <AgentResponseHandler 
      ref="agentResponseHandlerRef" 
      @agent-response-chunk="onAgentResponseChunk"
      @agent-response-complete="onAgentResponseComplete"
      @agent-response-error="onAgentResponseError"
    />
    <AgentInputModal
      :visible="showAgentModal"
      :position="modalPosition"
      :editor-info="editorInfo"
      :agentResponse="currentAgentResponse" 
      :isAgentResponding="isAgentResponding"
      :historyIndex="historyDisplayIndex"
      :historyLength="conversationHistory.length"
      @close="showAgentModal = false"
      @send="handleAgentMessage"
      @request-insert="handleInsertResponse" 
      @navigate-history="handleHistoryNavigation"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, watch, computed } from 'vue';
import EditorToolbar from './EditorToolbar.vue';
import EditorContent from './EditorContent.vue';
import MentionHandler from '../rendering/MentionHandler.vue';
import AgentResponseHandler from '../Agent/AgentResponseHandler.vue';
import DocumentOutline from './DocumentOutline.vue';
import AgentInputModal from '../Agent/AgentInputModal.vue';
import chatService from '../../services/chat';

// Props声明
const props = defineProps({
  modelValue: {
    type: String,
    default: '<p>开始写作...</p>'
  },
  conversationId: {
    type: [Number, String, null],
    default: null
  },
  noteId: {
    type: [Number, String, null],
    default: null
  }
});

// 事件声明
const emit = defineEmits(['update:modelValue', 'word-count', 'update:conversationId', 'toggle-sidebar-mode', 'sidebar-send', 'sidebar-insert', 'sidebar-navigate-history', 'conversation-history-loaded']);

// 状态变量
const wordCount = ref(0);
const isComposing = ref(false);
const showAgentSelector = ref(false);
const currentRange = ref(null);
const selectedHeading = ref('p');
const showOutline = ref(false); // 默认不显示大纲
const showAgentModal = ref(false);
const interactionMode = ref('modal'); // 'modal' | 'sidebar'
const currentCursorRange = ref(null);
const modalPosition = ref({ y: 0, x: 0 });
const editorInfo = ref({ left: 0, right: 0, width: 0, editorOffsetLeft: 0 });

// 新状态变量
const currentAgentResponse = ref('');
const isAgentResponding = ref(false);
const currentSentMessageData = ref(null);
const conversationHistory = ref([]); // { user: string, agent: string }[]
const historyDisplayIndex = ref(-1);
const lastLoadedSessionId = ref(null); // 跟踪最后加载的会话ID，避免重复加载

// 组件引用
const editorContentRef = ref(null);
const agentResponseHandlerRef = ref(null);
const documentOutlineRef = ref(null);
const mentionHandlerRef = ref(null);

// 确保 toggleOutline 方法存在且正确
const toggleOutline = () => {
  showOutline.value = !showOutline.value;
};

// 切换侧边栏模式 - 现在只发射事件给父组件
const toggleSidebarMode = () => {
  const newMode = interactionMode.value === 'modal' ? 'sidebar' : 'modal';
  console.log(`切换交互模式: ${interactionMode.value} -> ${newMode}`);
  
  emit('toggle-sidebar-mode', {
    currentMode: interactionMode.value,
    newMode: newMode,
    showInterface: true, // 表示要直接显示对应的界面
    agentResponse: currentAgentResponse.value,
    isAgentResponding: isAgentResponding.value,
    historyIndex: historyDisplayIndex.value,
    historyLength: conversationHistory.value.length
  });
};

// 加载会话历史记录
const loadConversationHistory = async (sessionId: number | string | null) => {
  // 如果会话ID与上次加载的相同，跳过重复加载
  if (sessionId && sessionId === lastLoadedSessionId.value) {
    console.log(`会话ID ${sessionId} 已经加载过，跳过重复加载`);
    return;
  }
  
  if (!sessionId) {
    // 没有会话ID，清空历史记录
    conversationHistory.value = [];
    historyDisplayIndex.value = -1;
    currentAgentResponse.value = '';
    lastLoadedSessionId.value = null;
    console.log('没有会话ID，清空历史记录');
    
    // 即使没有历史记录，也通知Home.vue清空侧边栏
    emit('conversation-history-loaded', {
      sessionId: sessionId,
      history: [],
      length: 0
    });
    return;
  }

  try {
    console.log(`开始加载会话 ${sessionId} 的历史记录`);
    const history = await chatService.getSessionAgentHistory(Number(sessionId));
    
    if (history && history.length > 0) {
      conversationHistory.value = history;
      historyDisplayIndex.value = history.length - 1; // 默认显示最新的记录
      currentAgentResponse.value = history[history.length - 1].agent; // 显示最新的AI回复
      lastLoadedSessionId.value = sessionId; // 记录已加载的会话ID
      console.log(`加载了 ${history.length} 条历史记录，当前显示索引: ${historyDisplayIndex.value}`);
      
      // 通知Home.vue更新侧边栏的会话历史
      emit('conversation-history-loaded', {
        sessionId: sessionId,
        history: history,
        length: history.length
      });
    } else {
      conversationHistory.value = [];
      historyDisplayIndex.value = -1;
      currentAgentResponse.value = '';
      lastLoadedSessionId.value = sessionId; // 即使没有历史记录，也记录会话ID避免重复请求
      console.log('没有找到历史记录');
      
      // 即使没有历史记录，也通知Home.vue清空侧边栏
      emit('conversation-history-loaded', {
        sessionId: sessionId,
        history: [],
        length: 0
      });
    }
  } catch (error) {
    console.error('加载历史记录失败:', error);
    conversationHistory.value = [];
    historyDisplayIndex.value = -1;
    currentAgentResponse.value = '';
    lastLoadedSessionId.value = sessionId; // 即使失败，也记录会话ID避免重复请求
    
    // 加载失败时也通知Home.vue清空侧边栏
    emit('conversation-history-loaded', {
      sessionId: sessionId,
      history: [],
      length: 0
    });
  }
};

// 监听会话ID变化
watch(() => props.conversationId, (newId) => {
  if (agentResponseHandlerRef.value) {
    console.log(`编辑器接收到会话ID: ${newId || 'null'}，设置到AgentResponseHandler`);
    // 无论newId是否为null都要设置，确保新建会话时能正确清空
    agentResponseHandlerRef.value.setConversationId(newId ? String(newId) : null);
  }
  
  // 加载会话的历史记录
  loadConversationHistory(newId);
}, { immediate: true });

// 监听笔记ID变化
watch(() => props.noteId, (newId) => {
  if (agentResponseHandlerRef.value) {
    console.log(`编辑器接收到笔记ID: ${newId || 'null'}，设置到AgentResponseHandler`);
    // 无论newId是否为null都要设置，确保新建笔记时能正确传递ID
    agentResponseHandlerRef.value.setCurrentNoteId(newId ? String(newId) : null);
    
    // 调试输出：确认AgentResponseHandler内部的noteId已被设置
    setTimeout(() => {
      console.log('AgentResponseHandler中当前的笔记ID:', agentResponseHandlerRef.value.getCurrentNoteId());
    }, 100);
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

// 监听conversationId变化，同步到AgentResponseHandler
watch(() => props.conversationId, (newConversationId) => {
  if (agentResponseHandlerRef.value && typeof agentResponseHandlerRef.value.setConversationId === 'function') {
    agentResponseHandlerRef.value.setConversationId(newConversationId);
    console.log('[Editor.vue] conversationId changed, updated AgentResponseHandler:', newConversationId);
  }
});

// 监听noteId变化，同步到AgentResponseHandler
watch(() => props.noteId, (newNoteId) => {
  if (agentResponseHandlerRef.value && typeof agentResponseHandlerRef.value.setCurrentNoteId === 'function') {
    agentResponseHandlerRef.value.setCurrentNoteId(newNoteId);
    console.log('[Editor.vue] noteId changed, updated AgentResponseHandler:', newNoteId);
  }
});

// 格式化操作
const applyFormat = ({ command, value }) => {
  // 应用格式化命令
  document.execCommand(command, false, value);
  
  // 获取应用格式化后的内容
  const newContent = getFullContent();
  
  // 发出内容更新事件
  emit('update:modelValue', newContent);
  
  // 聚焦编辑器以保持光标位置
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 设置标题
const setHeading = (heading: string) => {
  // 保存当前的内容状态（撤销前）
  const currentContent = editorContentRef.value ? getFullContent() : props.modelValue;
  
  // 应用格式化
  document.execCommand('formatBlock', false, heading);
  selectedHeading.value = heading;
  
  // 获取应用格式化后的内容
  const newContent = editorContentRef.value ? getFullContent() : props.modelValue;
  
  // 发出内容更新事件，确保变化被记录
  emit('update:modelValue', newContent);
  
  // 聚焦编辑器以保持光标位置
  nextTick(() => {
    editorContentRef.value?.focus();
  });
};

// 获取完整内容的辅助方法
const getFullContent = () => {
  if (editorContentRef.value && editorContentRef.value.editorRef) {
    return editorContentRef.value.editorRef.innerHTML;
  }
  return props.modelValue;
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
  
  // 获取应用格式化后的内容
  const newContent = getFullContent();
  
  // 发出内容更新事件
  emit('update:modelValue', newContent);
  
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
    
    // 获取应用格式化后的内容
    const newContent = getFullContent();
    
    // 发出内容更新事件
    emit('update:modelValue', newContent);
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
    
    // 获取应用格式化后的内容
    const newContent = getFullContent();
    
    // 发出内容更新事件
    emit('update:modelValue', newContent);
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
    // 选择器已经渲染完成，可以计算位置
    if (mentionHandlerRef.value) {
      mentionHandlerRef.value.updateSelectorPosition();
    }
  });
};

// 当选择了AI助手
const onAgentSelected = (agent) => {
  showAgentSelector.value = false;
  
  // 通过更新编辑器内容触发变更事件
  setTimeout(() => {
    const newContent = getFullContent();
    emit('update:modelValue', newContent);
    
    // 给输入框一点时间来渲染，然后确保它获得焦点
    setTimeout(() => {
      // 查找刚刚添加的输入框并聚焦
      const agentInputs = document.querySelectorAll('.agent-input');
      if (agentInputs.length > 0) {
        // 获取最后一个输入框（最新添加的）
        const latestInput = agentInputs[agentInputs.length - 1] as HTMLInputElement;
        if (latestInput) {
          latestInput.focus();
        }
      }
    }, 100);
  }, 0);
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
        // 检查提及是否已被处理过
        if (lastMention.getAttribute('data-processed') === 'true') {
          console.log('该@提及已被处理过，忽略Enter键操作');
          return; // 直接返回，不阻止默认换行行为
        }
        
        // 获取用户输入
        const userInput = agentResponseHandlerRef.value.extractUserInput(editorRef, lastMention);
        
        if (userInput && userInput.trim()) {
          // 获取AI助手ID
          const agentId = lastMention.getAttribute('data-agent-id');
          
          if (agentId) {
            event.preventDefault(); // 阻止默认的换行行为
            
            // 将当前提及标记为已处理，防止重复触发
            lastMention.setAttribute('data-processed', 'true');
            
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

// 处理发送消息到Agent
const handleSendToAgent = (data) => {
  console.log('发送消息到Agent', data);
  
  // 获取AgentResponseHandler引用
  const agentResponseHandler = agentResponseHandlerRef.value;
  if (!agentResponseHandler) {
    console.error('无法获取AgentResponseHandler引用');
    return;
  }
  
  // 调用AgentResponseHandler的handleInputChat方法
  agentResponseHandler.handleInputChat(
    data.inputElement,
    data.agentId,
    data.content,
    data.containerElement
  );
};

// 显示Agent输入弹窗
const showAgentModalAt = (data) => {
  console.log('显示Agent输入界面，接收到的定位数据:', data);
  console.log('当前交互模式:', interactionMode.value);
  
  // 立即保存当前光标范围，避免位置丢失
  if (data.range) {
    try {
      // 验证传入的范围是否有效
      const container = data.range.startContainer;
      if (document.contains(container)) {
        // 克隆并保存当前范围
        currentCursorRange.value = data.range.cloneRange();
        console.log('[Editor.vue] 已保存光标位置，容器:', container.nodeName, '偏移:', data.range.startOffset);
        
        // 验证保存的范围
        const testContainer = currentCursorRange.value.startContainer;
        console.log('[Editor.vue] 验证保存的范围，容器:', testContainer.nodeName, '偏移:', currentCursorRange.value.startOffset);
        
        // 添加一个临时标记来验证位置
        const debugSpan = document.createElement('span');
        debugSpan.textContent = '🔍';
        debugSpan.style.color = 'red';
        debugSpan.style.fontSize = '10px';
        debugSpan.id = 'debug-cursor-position';
        
        try {
          const debugRange = currentCursorRange.value.cloneRange();
          debugRange.insertNode(debugSpan);
          console.log('[Editor.vue] 调试标记已插入，位置验证成功');
          
          // 2秒后移除调试标记
          setTimeout(() => {
            const debugElement = document.getElementById('debug-cursor-position');
            if (debugElement && debugElement.parentNode) {
              debugElement.parentNode.removeChild(debugElement);
              console.log('[Editor.vue] 调试标记已移除');
            }
          }, 2000);
        } catch (debugError) {
          console.warn('[Editor.vue] 调试标记插入失败:', debugError);
        }
        
      } else {
        console.warn('[Editor.vue] 传入的范围容器不在文档中');
        currentCursorRange.value = null;
      }
    } catch (error) {
      console.warn('[Editor.vue] 无法保存光标位置:', error);
      currentCursorRange.value = null;
    }
  } else {
    // 如果没有传入范围，尝试获取当前选择
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      try {
        const currentRange = selection.getRangeAt(0);
        currentCursorRange.value = currentRange.cloneRange();
        console.log('[Editor.vue] 从当前选择保存光标位置');
      } catch (error) {
        console.warn('[Editor.vue] 无法从当前选择保存光标位置:', error);
        currentCursorRange.value = null;
      }
    } else {
      console.warn('[Editor.vue] 没有可用的光标位置');
      currentCursorRange.value = null;
    }
  }
  
  // 根据当前模式显示对应界面
  if (interactionMode.value === 'sidebar') {
    // 侧边栏模式：发射事件给父组件显示侧边栏
    emit('toggle-sidebar-mode', {
      currentMode: interactionMode.value,
      showSidebar: true, // 明确表示要显示侧边栏
      agentResponse: currentAgentResponse.value,
      isAgentResponding: isAgentResponding.value,
      historyIndex: historyDisplayIndex.value,
      historyLength: conversationHistory.value.length
    });
    showAgentModal.value = false;
    console.log('侧边栏模式：发射事件显示侧边栏');
  } else {
    // 弹窗模式：显示弹窗
    // 设置弹窗位置（使用视口位置）
    if (data.cursorPosition && data.cursorPosition.viewport) {
      modalPosition.value = {
        y: data.cursorPosition.viewport.y,
        x: data.cursorPosition.viewport.x
      };
    }
    
    // 保存编辑器信息，用于计算输入框位置
    if (data.editorInfo) {
      editorInfo.value = {
        ...data.editorInfo,
        // 确保传递所有必要的编辑器信息
        left: data.editorInfo.left,
        right: data.editorInfo.right,
        width: data.editorInfo.width,
        editorOffsetLeft: data.editorInfo.editorOffsetLeft
      };
      
      console.log('已更新编辑器信息:', editorInfo.value);
    }
    
    // 显示弹窗
    showAgentModal.value = true;
    console.log('弹窗模式：显示弹窗');
  }
};

// 处理Agent消息发送
const handleAgentMessage = (data) => {
  console.log('[Editor.vue] handleAgentMessage, data:', data);
  console.log('[Editor.vue] Current conversationId:', props.conversationId);
  
  // 如果当前是侧边栏模式，发射事件给父组件
  if (interactionMode.value === 'sidebar') {
    emit('sidebar-send', {
      ...data,
      conversationId: props.conversationId,
      noteId: props.noteId
    });
    return;
  }
  
  // 弹窗模式下的原有逻辑
  currentSentMessageData.value = data; // Store sent message data
  isAgentResponding.value = true;
  currentAgentResponse.value = ''; // Clear previous response

  if (agentResponseHandlerRef.value) {
    console.log('[Editor.vue] agentResponseHandlerRef.value is:', agentResponseHandlerRef.value);
    
    // 设置当前会话ID到AgentResponseHandler
    if (typeof agentResponseHandlerRef.value.setConversationId === 'function') {
      agentResponseHandlerRef.value.setConversationId(props.conversationId);
      console.log('[Editor.vue] Set conversationId to AgentResponseHandler:', props.conversationId);
    }
    
    // 设置当前笔记ID到AgentResponseHandler  
    if (typeof agentResponseHandlerRef.value.setCurrentNoteId === 'function' && props.noteId) {
      agentResponseHandlerRef.value.setCurrentNoteId(props.noteId);
      console.log('[Editor.vue] Set noteId to AgentResponseHandler:', props.noteId);
    }
    
    if (typeof agentResponseHandlerRef.value.triggerChatRequest === 'function') {
      console.log('[Editor.vue] Calling agentResponseHandlerRef.value.triggerChatRequest');
      agentResponseHandlerRef.value.triggerChatRequest(
        data.agentId,
        data.content
      );
    } else {
      console.error('[Editor.vue] triggerChatRequest is NOT a function on agentResponseHandlerRef.value');
      isAgentResponding.value = false;
      currentAgentResponse.value = 'Error: Agent handler function not found.';
    }
  } else {
    console.error('[Editor.vue] AgentResponseHandler ref not available at call time');
    isAgentResponding.value = false;
    currentAgentResponse.value = 'Error: Agent handler not ready.';
  }
};

// Event Handlers for AgentResponseHandler events
const onAgentResponseChunk = (chunk: string) => {
  console.log('[Editor.vue] Received chunk:', chunk);
  currentAgentResponse.value += chunk;
};

const onAgentResponseComplete = (data: { responseText: string, conversationId?: string | number }) => {
  console.log('[Editor.vue] Response complete:', data);
  currentAgentResponse.value = data.responseText; // Chunk might have already built it
  isAgentResponding.value = false;

  // Add to history if there was a preceding user message data
  if (currentSentMessageData.value && currentSentMessageData.value.content) {
    console.log('[Editor.vue] Storing to history - User:', currentSentMessageData.value.content, 'Agent:', data.responseText);
    conversationHistory.value.push({
      user: currentSentMessageData.value.content,
      agent: data.responseText
    });
    historyDisplayIndex.value = conversationHistory.value.length - 1;
    // 重置加载标记，确保下次能够重新加载更新后的历史记录
    lastLoadedSessionId.value = null;
    console.log('[Editor.vue] Added to conversation history. New length:', conversationHistory.value.length, 'Current index:', historyDisplayIndex.value);
  } else {
    console.warn('[Editor.vue] No currentSentMessageData found, cannot save to history reliably.');
    // Handle cases where AI responds without direct user input if necessary, 
    // or simply update current response without adding to history.
    // For now, if no user input, we might not want to push to history or reset index.
  }

  if (data.conversationId && props.conversationId !== data.conversationId) {
    emit('update:conversationId', data.conversationId);
    console.log('[Editor.vue] Updated conversationId to:', data.conversationId);
  }
  // TODO: Clear input in AgentInputModal if needed
  // For example, if AgentInputModal has a ref and a clearInput method: agentInputModalRef.value.clearInput();
};

const onAgentResponseError = (error) => {
  console.error('[Editor.vue] Agent response error:', error);
  isAgentResponding.value = false;
  currentAgentResponse.value = `抱歉，AI助手出错了: ${error.message || '未知错误'}`;
};

// New method for handling history navigation
const handleHistoryNavigation = (payload: { direction: 'prev' | 'next' }) => {
  // 如果当前是侧边栏模式，发射事件给父组件
  if (interactionMode.value === 'sidebar') {
    emit('sidebar-navigate-history', payload);
    return;
  }
  
  // 弹窗模式下的原有逻辑
  if (!conversationHistory.value || conversationHistory.value.length === 0) return;

  const { direction } = payload;
  let newIndex = historyDisplayIndex.value;

  if (direction === 'prev' && historyDisplayIndex.value > 0) {
    newIndex--;
  } else if (direction === 'next' && historyDisplayIndex.value < conversationHistory.value.length - 1) {
    newIndex++;
  }

  if (newIndex !== historyDisplayIndex.value) {
    historyDisplayIndex.value = newIndex;
    const historicResponse = conversationHistory.value[newIndex].agent;
    currentAgentResponse.value = historicResponse;
    console.log('[Editor.vue] Displaying historic response:', historicResponse);
    console.log('[Editor.vue] Full history for debugging:', JSON.parse(JSON.stringify(conversationHistory.value)));
    console.log(`[Editor.vue] Navigated history to index: ${newIndex}. Displaying new agent response.`);
  }
};

// Handler for inserting content from modal into editor
const handleInsertResponse = (responseText: string) => {
  // 如果当前是侧边栏模式，发射事件给父组件
  if (interactionMode.value === 'sidebar') {
    emit('sidebar-insert', responseText);
    return;
  }
  
  // 弹窗模式下的原有逻辑
  insertContentAtCursor(responseText);
};

// 新增专门的插入方法，供外部直接调用，避免递归
const insertContentAtCursor = (responseText: string) => {
  console.log('[Editor.vue] Request to insert:', responseText);
  console.log('[Editor.vue] Current cursor range exists:', !!currentCursorRange.value);
  
  if (!editorContentRef.value || !responseText) {
    console.warn('[Editor.vue] Editor instance or responseText not available for insert.');
    if (!responseText) console.warn('[Editor.vue] responseText for insert is empty');
    if (!editorContentRef.value) console.warn('[Editor.vue] editorContentRef.value is null');
    return;
  }

  // 获取原生contenteditable元素
  const editorElement = editorContentRef.value.editorRef;
  if (!editorElement) {
    console.warn('[Editor.vue] Editor element not found');
    return;
  }

  try {
    // 聚焦编辑器
    editorElement.focus();

    // 获取当前选择
    const selection = window.getSelection();
    let range = null;

    // 首先检查是否有保存的光标位置
    if (currentCursorRange.value) {
      try {
        // 检查保存的范围是否仍然有效
        const container = currentCursorRange.value.startContainer;
        const offset = currentCursorRange.value.startOffset;
        
        console.log('[Editor.vue] 检查保存的光标位置，容器:', container.nodeName, '偏移:', offset);
        
        // 验证保存的范围是否仍在文档中
        if (document.contains(container)) {
          // 验证偏移值是否在有效范围内
          const maxOffset = container.nodeType === Node.TEXT_NODE 
            ? container.textContent.length 
            : container.childNodes.length;
          
          const validOffset = Math.min(offset, maxOffset);
          
          // 创建新的范围
          range = document.createRange();
          range.setStart(container, validOffset);
          range.setEnd(container, validOffset);
          
          // 设置选择
          selection.removeAllRanges();
          selection.addRange(range);
          console.log('[Editor.vue] 成功恢复保存的光标位置，偏移:', validOffset);
        } else {
          console.warn('[Editor.vue] 保存的光标位置已失效，容器不在文档中');
          currentCursorRange.value = null;
        }
      } catch (e) {
        console.warn('[Editor.vue] 保存的光标范围检查失败:', e);
        currentCursorRange.value = null;
      }
    }

    // 如果没有有效的保存范围，尝试使用当前选择
    if (!range && selection.rangeCount > 0) {
      range = selection.getRangeAt(0);
      console.log('[Editor.vue] 使用当前选择位置');
    }

    // 如果仍然没有有效范围，寻找合适的插入位置
    if (!range) {
      console.log('[Editor.vue] 寻找合适的插入位置');
      range = document.createRange();
      
      // 寻找合适的插入位置
      const editableContent = editorElement.querySelector('.editable-content') || editorElement;
      
      // 先尝试找到调试标记的位置
      const debugMarker = document.getElementById('debug-cursor-position');
      if (debugMarker) {
        console.log('[Editor.vue] 找到调试标记，在其位置插入');
        range.setStartBefore(debugMarker);
        range.setEndBefore(debugMarker);
        
        // 移除调试标记
        if (debugMarker.parentNode) {
          debugMarker.parentNode.removeChild(debugMarker);
        }
      } else {
        // 没有调试标记，使用默认逻辑
        const paragraphs = editableContent.querySelectorAll('p');
        
        if (paragraphs.length > 0) {
          // 找到最后一个段落
          const lastParagraph = paragraphs[paragraphs.length - 1];
          
          // 将光标设置到最后一个段落的末尾
          if (lastParagraph.lastChild && lastParagraph.lastChild.nodeType === Node.TEXT_NODE) {
            range.setStart(lastParagraph.lastChild, lastParagraph.lastChild.textContent.length);
            range.setEnd(lastParagraph.lastChild, lastParagraph.lastChild.textContent.length);
          } else {
            range.selectNodeContents(lastParagraph);
            range.collapse(false); // 移动到末尾
          }
          console.log('[Editor.vue] 插入位置设置到最后一个段落末尾');
        } else {
          // 如果没有段落，在可编辑区域开始处创建
          range.selectNodeContents(editableContent);
          range.collapse(true);
          console.log('[Editor.vue] 插入位置设置到可编辑区域开始');
        }
      }
      
      selection.removeAllRanges();
      selection.addRange(range);
    }

    console.log('[Editor.vue] 最终插入位置 - 容器:', range.startContainer.nodeName, '偏移:', range.startOffset);

    // 清理响应文本并转换为HTML
    const cleanText = responseText.trim();
    
    // 删除选择的内容（如果有）
    if (!range.collapsed) {
      range.deleteContents();
      console.log('[Editor.vue] 删除选中内容');
    }

    // 处理插入逻辑 - 如果光标在段落中间，需要特殊处理
    const startContainer = range.startContainer;
    const startOffset = range.startOffset;
    
    // 检查是否在文本节点中间
    if (startContainer.nodeType === Node.TEXT_NODE && startOffset > 0 && startOffset < startContainer.textContent.length) {
      console.log('[Editor.vue] 光标在文本节点中间，分割文本节点');
      
      // 分割当前文本节点
      const textBefore = startContainer.textContent.substring(0, startOffset);
      const textAfter = startContainer.textContent.substring(startOffset);
      
      // 创建新的段落来插入内容
      const newParagraph = document.createElement('p');
      
      // 处理响应文本
      const paragraphs = cleanText.split(/\n\s*\n/).filter(p => p.trim());
      if (paragraphs.length > 0) {
        // 第一个段落继续当前行
        const firstParagraph = paragraphs[0].trim().split('\n');
        firstParagraph.forEach((line, lineIndex) => {
          if (lineIndex > 0) {
            newParagraph.appendChild(document.createElement('br'));
          }
          newParagraph.appendChild(document.createTextNode(line));
        });
      }
      
      // 更新当前文本节点为前半部分
      startContainer.textContent = textBefore;
      
      // 创建包含后半部分文本的新文本节点
      const afterTextNode = document.createTextNode(textAfter);
      
      // 找到当前段落
      const currentParagraph = startContainer.parentElement;
      
      // 插入新段落
      if (currentParagraph && currentParagraph.parentNode) {
        // 在当前段落后插入新内容
        currentParagraph.parentNode.insertBefore(newParagraph, currentParagraph.nextSibling);
        
        // 如果有后续文本，创建新段落
        if (textAfter.trim()) {
          const afterParagraph = document.createElement('p');
          afterParagraph.appendChild(afterTextNode);
          currentParagraph.parentNode.insertBefore(afterParagraph, newParagraph.nextSibling);
        }
        
        // 处理剩余段落
        if (paragraphs.length > 1) {
          let insertAfter = textAfter.trim() ? afterParagraph : newParagraph;
          
          for (let i = 1; i < paragraphs.length; i++) {
            const p = document.createElement('p');
            const lines = paragraphs[i].trim().split('\n');
            lines.forEach((line, lineIndex) => {
              if (lineIndex > 0) {
                p.appendChild(document.createElement('br'));
              }
              p.appendChild(document.createTextNode(line));
            });
            
            insertAfter.parentNode.insertBefore(p, insertAfter.nextSibling);
            insertAfter = p;
          }
        }
        
        // 设置光标到新内容的末尾
        const finalParagraph = textAfter.trim() ? afterParagraph : newParagraph;
        range.setStartAfter(finalParagraph);
        range.setEndAfter(finalParagraph);
      }
    } else {
      // 光标在段落开始或结束，使用原有逻辑
      const fragment = document.createDocumentFragment();
      
      // 将响应文本按段落分割
      const paragraphs = cleanText.split(/\n\s*\n/).filter(p => p.trim());
      
      if (paragraphs.length === 0) {
        // 如果没有段落，插入一个空段落
        const emptyP = document.createElement('p');
        emptyP.innerHTML = '<br>';
        fragment.appendChild(emptyP);
        console.log('[Editor.vue] 插入空段落');
      } else {
        console.log('[Editor.vue] 创建', paragraphs.length, '个段落');
        paragraphs.forEach((paragraph, index) => {
          const p = document.createElement('p');
          // 处理段落内的换行
          const lines = paragraph.trim().split('\n');
          lines.forEach((line, lineIndex) => {
            if (lineIndex > 0) {
              p.appendChild(document.createElement('br'));
            }
            p.appendChild(document.createTextNode(line));
          });
          fragment.appendChild(p);
        });
      }

      // 插入内容
      range.insertNode(fragment);
      console.log('[Editor.vue] 内容已插入到DOM');

      // 将光标移动到插入内容的末尾
      range.collapse(false);
    }

    selection.removeAllRanges();
    selection.addRange(range);
    console.log('[Editor.vue] 光标已移动到插入内容末尾');

    // 清除保存的光标位置，避免后续插入出现问题
    currentCursorRange.value = null;

    // 触发输入事件以更新modelValue
    const inputEvent = new Event('input', { bubbles: true });
    editorElement.dispatchEvent(inputEvent);

    console.log('[Editor.vue] Content inserted successfully at cursor position');

  } catch (error) {
    console.error('[Editor.vue] Error inserting content:', error);
  }

  // currentAgentResponse.value = ''; // Clear response from modal display - 注释掉，让内容插入后仍然保留
  // showAgentModal.value = false; // Optionally close modal after insert
};

// 组件挂载后聚焦编辑器
onMounted(() => {
  nextTick(() => {
    editorContentRef.value?.focus();
    
    // 初始化AgentResponseHandler的会话ID和笔记ID
    if (agentResponseHandlerRef.value) {
      if (typeof agentResponseHandlerRef.value.setConversationId === 'function') {
        agentResponseHandlerRef.value.setConversationId(props.conversationId);
        console.log('[Editor.vue] onMounted: Set conversationId to AgentResponseHandler:', props.conversationId);
      }
      
      if (typeof agentResponseHandlerRef.value.setCurrentNoteId === 'function' && props.noteId) {
        agentResponseHandlerRef.value.setCurrentNoteId(props.noteId);
        console.log('[Editor.vue] onMounted: Set noteId to AgentResponseHandler:', props.noteId);
      }
    }
    
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
  getWordCount: () => wordCount.value,
  // 暴露编辑器DOM元素的引用
  editorRef: computed(() => editorContentRef.value?.editorRef),
  setInteractionMode: (mode: 'modal' | 'sidebar') => {
    interactionMode.value = mode;
    console.log(`编辑器交互模式设置为: ${mode}`);
  },
  getCurrentAgentData: () => ({
    agentResponse: currentAgentResponse.value,
    isAgentResponding: isAgentResponding.value,
    historyIndex: historyDisplayIndex.value,
    historyLength: conversationHistory.value.length,
    conversationHistory: conversationHistory.value // 添加完整的会话历史记录
  }),
  // 修改为使用新的方法，避免递归调用
  handleInsertResponse: (responseText: string) => {
    console.log('[Editor.vue] 外部调用handleInsertResponse:', responseText);
    insertContentAtCursor(responseText);
  },
  closeModal: () => {
    // 关闭弹窗
    showAgentModal.value = false;
    console.log('弹窗已关闭');
  },
  showDemoModal: (position = { x: 0, y: 0 }) => {
    // 确保之前的弹窗状态被清理
    showAgentModal.value = false;
    currentAgentResponse.value = '';
    isAgentResponding.value = false;
    
    // 计算弹窗位置 - 使用正确的弹窗宽度650px
    const MODAL_WIDTH = 650;
    const calculatedPosition = position.x === 0 && position.y === 0 ? {
      y: Math.max(200, window.innerHeight * 0.3), // 距离顶部30%的位置，但至少200px
      x: Math.max(50, (window.innerWidth - MODAL_WIDTH) / 2) // 水平居中，使用实际弹窗宽度
    } : position;
    
    // 设置编辑器信息，确保弹窗能正确定位
    if (editorContentRef.value && editorContentRef.value.editorRef) {
      const editorElement = editorContentRef.value.editorRef;
      const rect = editorElement.getBoundingClientRect();
      editorInfo.value = {
        left: rect.left,
        right: rect.right,
        width: rect.width,
        editorOffsetLeft: rect.left
      };
    }
    
    // 显示演示弹窗
    modalPosition.value = calculatedPosition;
    currentAgentResponse.value = '这是弹窗模式的演示界面。您可以在这里与AI助手交互。\n\n尝试在编辑器中输入 @ 来唤起AI助手，或者直接在这里发送消息。';
    showAgentModal.value = true;
    console.log('显示演示弹窗，位置:', calculatedPosition);
    
    // 5秒后自动关闭演示弹窗
    setTimeout(() => {
      if (showAgentModal.value && currentAgentResponse.value.includes('演示界面')) {
        showAgentModal.value = false;
        currentAgentResponse.value = '';
      }
    }, 5000);
  },
  showModalWithContent: (contentData) => {
    // 确保之前的弹窗状态被清理
    showAgentModal.value = false;
    
    // 计算弹窗位置 - 使用正确的弹窗宽度650px
    const MODAL_WIDTH = 650;
    const calculatedPosition = {
      y: Math.max(200, window.innerHeight * 0.3),
      x: Math.max(50, (window.innerWidth - MODAL_WIDTH) / 2)
    };
    
    // 设置编辑器信息，确保弹窗能正确定位
    if (editorContentRef.value && editorContentRef.value.editorRef) {
      const editorElement = editorContentRef.value.editorRef;
      const rect = editorElement.getBoundingClientRect();
      editorInfo.value = {
        left: rect.left,
        right: rect.right,
        width: rect.width,
        editorOffsetLeft: rect.left
      };
    }
    
    // 设置弹窗位置和内容
    modalPosition.value = calculatedPosition;
    currentAgentResponse.value = contentData.response;
    isAgentResponding.value = contentData.isResponding;
    historyDisplayIndex.value = contentData.historyIndex;
    
    // 如果有会话历史记录，也更新到编辑器中
    if (contentData.conversationHistory && contentData.conversationHistory.length > 0) {
      conversationHistory.value = [...contentData.conversationHistory];
      console.log('更新会话历史记录，条数:', conversationHistory.value.length);
    }
    
    // 显示弹窗
    showAgentModal.value = true;
    console.log('显示内容弹窗，位置:', calculatedPosition, '内容长度:', contentData.response.length);
  }
});
</script>

<style>
.editor-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%; /* 改为100%，适应父容器高度 */
  position: relative;
  overflow: hidden; /* 改为hidden，避免冲突 */
}

.editor-toolbar-fixed {
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f9f9f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  width: 100%;
  flex-shrink: 0; /* 确保工具栏不会收缩 */
}

.editor-content-wrapper {
  display: flex;
  flex: 1;
  position: relative;
  overflow: hidden; /* 改为hidden，让父容器控制滚动 */
  min-width: 0; /* 允许flex子元素收缩 */
  min-height: 0; /* 允许flex子元素收缩 */
}

.document-outline {
  flex-shrink: 0;
  position: sticky;
  top: 60px; /* 工具栏高度 */
  align-self: flex-start;
  max-height: calc(100vh - 60px); /* 使用max-height而不是固定height */
  overflow-y: auto; /* 大纲内容如果过长，允许滚动 */
}

.editor-main {
  flex: 1;
  position: relative;
  overflow-y: auto; /* 改为auto，允许编辑器内容滚动 */
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许收缩 */
}

.editor-footer {
  position: sticky;
  bottom: 0;
  z-index: 90;
  background-color: white;
  border-top: 1px solid #eee;
  padding: 10px 20px;
  display: flex;
  justify-content: space-between;
  color: #888;
  font-size: 14px;
  margin-top: auto;
  flex-shrink: 0; /* 确保底部栏不会收缩 */
}
</style> 