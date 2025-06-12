<template>
  <div class="editor-container">
    <EditorToolbar
      class="editor-toolbar-fixed"
      :editor-ref="editorContentRef?.editorRef"
      :selected-heading="editorState.selectedHeading.value"
      :interaction-mode="editorState.interactionMode.value"
      @apply-formatting="handleApplyFormatting"
      @set-heading="handleSetHeading"
      @set-letter-spacing="handleSetLetterSpacing"
      @set-line-height="handleSetLineHeight"
      @set-font-size="handleSetFontSize"
      @undo="handleUndo"
      @redo="handleRedo"
      @toggle-outline="toggleOutline"
      @toggle-sidebar-mode="toggleSidebarMode"
      @insert-canvas="handleInsertCanvas"
    />
    
    <div class="editor-content-wrapper">
      <DocumentOutline 
        v-if="editorState.showOutline.value && editorContentRef" 
        :editorRef="editorContentRef" 
        class="document-outline"
        ref="documentOutlineRef"
      />
      
      <div class="editor-main">
        <EditorContent
          ref="editorContentRef"
          :modelValue="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          :show-agent-selector="editorState.showAgentSelector.value"
          @word-count="updateWordCount"
          @key-down="handleKeyDown"
          @show-agent-selector="showAgentSelectorAt"
          @show-agent-modal="showAgentModalAt"
          @send-to-agent="handleSendToAgent"
          @composition-start="editorState.isComposing.value = true"
          @composition-end="editorState.isComposing.value = false"
          @input-update="handleInputUpdate"
        />
        
        <MentionHandler
          :show-selector="editorState.showAgentSelector.value"
          :current-range="editorState.currentRange.value"
          @close="editorState.showAgentSelector.value = false"
          @agent-selected="onAgentSelected"
          ref="mentionHandlerRef"
        />
      </div>
    </div>
    
    <AgentResponseHandler 
      ref="agentResponseHandlerRef" 
      @agent-response-chunk="$emit('agent-response-chunk', $event)"
      @agent-response-complete="$emit('agent-response-complete', $event)"
      @agent-response-error="$emit('agent-response-error', $event)"
      @agent-tool-status="$emit('agent-tool-status', $event)"
      @note-content-updated="$emit('note-content-updated', $event)"
      @note-edit-preview="onNoteEditPreview"
    />
    
    <AgentInputModal
      ref="agentInputModalRef"
      :visible="editorState.showAgentModal.value"
      :position="editorState.modalPosition.value"
      :editor-info="editorState.editorInfo.value"
      :agentResponse="editorState.currentAgentResponse.value" 
      :isAgentResponding="editorState.isAgentResponding.value"
      :historyIndex="editorState.historyDisplayIndex.value"
      :historyLength="editorState.conversationHistory.value.length"
      @close="editorState.showAgentModal.value = false"
      @send="handleAgentMessage"
      @request-insert="handleInsertResponse" 
      @navigate-history="handleHistoryNavigation"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted, createApp, onUnmounted } from 'vue';
import EditorToolbar from './EditorToolbar.vue';
import EditorContent from './EditorContent.vue';
import MentionHandler from '../rendering/MentionHandler.vue';
import AgentResponseHandler from '../Agent/AgentResponseHandler.vue';
import DocumentOutline from './DocumentOutline.vue';
import AgentInputModal from '../Agent/AgentInputModal.vue';
import EmbeddedCanvas from '../Canvas/EmbeddedCanvas.vue';

// Composables
import { useEditorState } from '../../composables/useEditorState';
import { useEditorFormatting } from '../../composables/useEditorFormatting';
import { useCursorManager } from '../../composables/useCursorManager';
import { usePreviewManager } from '../../composables/usePreviewManager';

// Props
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

// Emits
const emit = defineEmits([
  'update:modelValue', 
  'word-count', 
  'update:conversationId', 
  'toggle-sidebar-mode', 
  'sidebar-send', 
  'sidebar-insert', 
  'sidebar-navigate-history', 
  'conversation-history-loaded', 
  'title-updated',
  'agent-response-chunk',
  'agent-response-complete', 
  'agent-response-error',
  'agent-tool-status',
  'note-content-updated'
]);

// 使用composables
const editorState = useEditorState();
const formatting = useEditorFormatting();
const cursorManager = useCursorManager();
const previewManager = usePreviewManager();

// 组件引用
const editorContentRef = ref(null);
const agentResponseHandlerRef = ref(null);
const documentOutlineRef = ref(null);
const mentionHandlerRef = ref(null);
const agentInputModalRef = ref(null);

// 画板实例管理
const canvasInstances = new Map();

// 格式化事件处理
const handleApplyFormatting = (params: any) => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.applyFormat(params, editorRef, emit);
};

const handleSetHeading = (heading: string) => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.setHeading(heading, editorRef, emit);
  editorState.selectedHeading.value = heading;
};

const handleSetLetterSpacing = (spacing: string) => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.setLetterSpacing(spacing, editorRef, emit);
};

const handleSetLineHeight = (height: string) => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.setLineHeight(height, editorRef, emit);
};

const handleSetFontSize = (size: string) => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.setFontSize(size, editorRef, emit);
};

const handleUndo = () => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.undoAction(editorRef);
};

const handleRedo = () => {
  const editorRef = editorContentRef.value?.editorRef;
  formatting.redoAction(editorRef);
};

// 插入画板处理
const handleInsertCanvas = () => {
  console.log('[EditorContainer] 插入画板');
  const editorRef = editorContentRef.value?.editorRef;
  if (!editorRef) {
    console.error('[EditorContainer] editorRef 不存在');
    return;
  }

  // 生成唯一的画板ID
  const canvasId = `canvas-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  console.log('[EditorContainer] 生成的画板ID:', canvasId);
  
  // 创建占位元素
  const placeholderHTML = `<div class="canvas-placeholder" data-canvas-id="${canvasId}" contenteditable="false"></div>`;
  
  // 获取当前光标位置并插入占位元素
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    
    // 在当前段落后插入画板
    const currentParagraph = range.startContainer.nodeType === Node.TEXT_NODE 
      ? range.startContainer.parentElement?.closest('p')
      : range.startContainer.closest?.('p');
    
    if (currentParagraph) {
      const placeholderElement = document.createElement('div');
      placeholderElement.innerHTML = placeholderHTML;
      currentParagraph.parentNode?.insertBefore(placeholderElement.firstElementChild!, currentParagraph.nextSibling);
    } else {
      const placeholderElement = document.createElement('div');
      placeholderElement.innerHTML = placeholderHTML;
      range.insertNode(placeholderElement.firstElementChild!);
    }
    
    // 将光标移动到画板后面
    const newParagraph = document.createElement('p');
    newParagraph.innerHTML = '<br>';
    const insertedPlaceholder = document.querySelector(`[data-canvas-id="${canvasId}"]`);
    if (insertedPlaceholder) {
      insertedPlaceholder.parentNode?.insertBefore(newParagraph, insertedPlaceholder.nextSibling);
      
      // 设置光标到新段落
      const newRange = document.createRange();
      newRange.setStart(newParagraph, 0);
      newRange.collapse(true);
      selection.removeAllRanges();
      selection.addRange(newRange);
      
      // 在下一个tick中用Vue组件替换占位元素
      nextTick(() => {
        mountCanvasComponent(canvasId);
      });
    }
    
    // 不要在这里立即更新内容，等组件挂载完成后再更新
    // 避免覆盖刚挂载的Vue组件
  }
};

// 动态挂载画板组件
const mountCanvasComponent = (canvasId: string) => {
  console.log('[EditorContainer] 动态挂载画板组件:', canvasId);
  
  const placeholder = document.querySelector(`[data-canvas-id="${canvasId}"]`);
  if (!placeholder) {
    console.error('[EditorContainer] 找不到占位元素:', canvasId);
    return;
  }
  
  // 创建一个新的Vue应用实例
  const canvasApp = createApp(EmbeddedCanvas, {
    canvasId: canvasId,
    onDelete: (id: string) => handleCanvasDelete(id),
    onResize: (data: { canvasId: string; width: number; height: number }) => handleCanvasResize(data),
    onSelect: (id: string) => handleCanvasSelect(id),
    onDeselect: (id: string) => handleCanvasDeselect(id)
  });
  
  // 挂载到占位元素
  const canvasInstance = canvasApp.mount(placeholder);
  
  // 移除占位符样式，添加已挂载标识
  placeholder.classList.remove('canvas-placeholder');
  placeholder.classList.add('canvas-mounted');
  
  // 保存实例引用以便后续管理
  canvasInstances.set(canvasId, {
    app: canvasApp,
    instance: canvasInstance
  });
  
  console.log('[EditorContainer] 画板组件挂载完成:', canvasId);
  
  // 在组件挂载完成后，延迟更新编辑器内容
  nextTick(() => {
    const editorRef = editorContentRef.value?.editorRef;
    if (editorRef) {
      const newContent = formatting.getFullContent(editorRef);
      emit('update:modelValue', newContent);
      console.log('[EditorContainer] 画板挂载后更新内容完成');
    }
  });
};

// 处理画板删除
const handleCanvasDelete = (canvasId: string) => {
  console.log('[EditorContainer] 删除画板:', canvasId);
  
  // 卸载Vue实例
  const canvasData = canvasInstances.get(canvasId);
  if (canvasData) {
    canvasData.app.unmount();
    canvasInstances.delete(canvasId);
  }
  
  // 移除DOM元素
  const canvasElement = document.querySelector(`[data-canvas-id="${canvasId}"]`);
  if (canvasElement) {
    canvasElement.remove();
  }
  
  // 更新编辑器内容
  const editorRef = editorContentRef.value?.editorRef;
  if (editorRef) {
    const newContent = formatting.getFullContent(editorRef);
    emit('update:modelValue', newContent);
  }
};

// 处理画板大小调整
const handleCanvasResize = (data: { canvasId: string; width: number; height: number }) => {
  console.log('[EditorContainer] 画板大小调整:', data);
    
    // 更新编辑器内容
    const editorRef = editorContentRef.value?.editorRef;
    if (editorRef) {
      const newContent = formatting.getFullContent(editorRef);
      emit('update:modelValue', newContent);
    }
};

// 处理画板选中
const handleCanvasSelect = (canvasId: string) => {
  console.log('[EditorContainer] 画板选中:', canvasId);
  
  // 取消选中其他画板
  canvasInstances.forEach((canvasData, id) => {
    if (id !== canvasId && canvasData.instance && typeof canvasData.instance.deselectCanvas === 'function') {
      canvasData.instance.deselectCanvas();
    }
  });
};

// 处理画板取消选中
const handleCanvasDeselect = (canvasId: string) => {
  console.log('[EditorContainer] 画板取消选中:', canvasId);
  };
  
// 初始化已存在的画板组件
const initializeExistingCanvases = () => {
  console.log('[EditorContainer] 开始初始化已存在的画板组件');
  
  // 1. 查找占位符元素
  const existingPlaceholders = document.querySelectorAll('.canvas-placeholder[data-canvas-id]');
  console.log('[EditorContainer] 找到已存在的画板占位元素数量:', existingPlaceholders.length);
  
  existingPlaceholders.forEach((placeholder) => {
    const canvasId = placeholder.getAttribute('data-canvas-id');
    if (canvasId && !canvasInstances.has(canvasId)) {
      console.log('[EditorContainer] 初始化已存在的画板:', canvasId);
      mountCanvasComponent(canvasId);
    } else if (canvasId && canvasInstances.has(canvasId)) {
      console.log('[EditorContainer] 画板已存在实例，跳过:', canvasId);
    }
  });

  // 2. 查找完整的画板wrapper元素
  const existingCanvases = document.querySelectorAll('.embedded-canvas-wrapper[data-canvas-id]');
  console.log('[EditorContainer] 找到已存在的完整画板数量:', existingCanvases.length);
  
  existingCanvases.forEach((canvas) => {
    const canvasId = canvas.getAttribute('data-canvas-id');
    if (canvasId && !canvasInstances.has(canvasId)) {
      console.log('[EditorContainer] 重新挂载已存在的画板:', canvasId);
      // 检查是否有子元素，如果没有则需要重新挂载
      const hasChildren = canvas.children.length > 0;
      console.log('[EditorContainer] 画板元素子元素数量:', canvas.children.length);
      
      if (!hasChildren || !canvas.querySelector('.canvas-board')) {
        console.log('[EditorContainer] 画板元素内容缺失，需要重新挂载');
        // 创建占位元素
        const placeholder = document.createElement('div');
        placeholder.className = 'canvas-placeholder';
        placeholder.setAttribute('data-canvas-id', canvasId);
        placeholder.setAttribute('contenteditable', 'false');
        
        // 替换现有元素
        canvas.parentNode?.replaceChild(placeholder, canvas);
        
        // 挂载新的Vue组件
        mountCanvasComponent(canvasId);
      } else {
        console.log('[EditorContainer] 画板元素内容完整，但需要重新绑定事件');
        // 画板内容完整，但可能需要重新绑定Vue组件实例
        try {
          const canvasApp = createApp(EmbeddedCanvas, {
            canvasId: canvasId,
            onDelete: (id: string) => handleCanvasDelete(id),
            onResize: (data: { canvasId: string; width: number; height: number }) => handleCanvasResize(data),
            onSelect: (id: string) => handleCanvasSelect(id),
            onDeselect: (id: string) => handleCanvasDeselect(id)
          });
          
          const canvasInstance = canvasApp.mount(canvas);
          
          canvasInstances.set(canvasId, {
            app: canvasApp,
            instance: canvasInstance
          });
          
          console.log('[EditorContainer] 画板组件重新绑定完成:', canvasId);
        } catch (error) {
          console.error('[EditorContainer] 重新绑定画板组件失败:', error);
        }
      }
    } else if (canvasId && canvasInstances.has(canvasId)) {
      console.log('[EditorContainer] 画板已存在实例，跳过:', canvasId);
    }
  });
  
  // 3. 检查所有包含canvas-id的div元素（可能的画板HTML结构）
  const allCanvasElements = document.querySelectorAll('div[data-canvas-id]');
  console.log('[EditorContainer] 找到所有包含data-canvas-id的元素数量:', allCanvasElements.length);
  
  allCanvasElements.forEach((element) => {
    const canvasId = element.getAttribute('data-canvas-id');
    const className = element.className;
    console.log('[EditorContainer] 发现画板元素:', canvasId, 'class:', className);
    
    if (canvasId && !canvasInstances.has(canvasId) && 
        !element.classList.contains('canvas-placeholder') && 
        !element.classList.contains('embedded-canvas-wrapper')) {
      console.log('[EditorContainer] 发现未知类型的画板元素，尝试转换为占位符:', canvasId);
      
      // 转换为占位符元素
      element.className = 'canvas-placeholder';
      element.setAttribute('contenteditable', 'false');
      element.innerHTML = ''; // 清空内容
      
      // 挂载Vue组件
      mountCanvasComponent(canvasId);
      }
  });
  
  console.log('[EditorContainer] 画板初始化完成，当前管理的画板实例数量:', canvasInstances.size);
};

// 其他事件处理
const toggleOutline = () => {
  editorState.showOutline.value = !editorState.showOutline.value;
};

const toggleSidebarMode = () => {
  const newMode = editorState.interactionMode.value === 'modal' ? 'sidebar' : 'modal';
  console.log(`[EditorContainer] 切换交互模式: ${editorState.interactionMode.value} -> ${newMode}`);
  
  emit('toggle-sidebar-mode', {
    currentMode: editorState.interactionMode.value,
    newMode: newMode,
    showInterface: true,
    agentResponse: editorState.currentAgentResponse.value,
    isAgentResponding: editorState.isAgentResponding.value,
    historyIndex: editorState.historyDisplayIndex.value,
    historyLength: editorState.conversationHistory.value.length
  });
};

const updateWordCount = (count: number) => {
  editorState.wordCount.value = count;
  emit('word-count', count);
};

const handleInputUpdate = ({ hasAgentMention, hasSendingIndicator, selection, content }: any) => {
  if (content) {
    emit('update:modelValue', content);
    console.log('Editor内容已更新，字符数:', content.length);
  }
};

const handleKeyDown = ({ event, editorRef, selection }: any) => {
  if (event.key === 'Enter' && !event.shiftKey && !editorState.isComposing.value) {
    const lastMention = agentResponseHandlerRef.value?.findLastMention(editorRef);
    
    if (lastMention && agentResponseHandlerRef.value && !agentResponseHandlerRef.value.isProcessing) {
      const isInMentionLine = cursorManager.isCursorInSameLineWithMention(selection, lastMention);
      
      if (isInMentionLine) {
        if (lastMention.getAttribute('data-processed') === 'true') {
          console.log('该@提及已被处理过，忽略Enter键操作');
          return;
        }
        
        const userInput = agentResponseHandlerRef.value.extractUserInput(editorRef, lastMention);
        
        if (userInput && userInput.trim()) {
          const agentId = lastMention.getAttribute('data-agent-id');
          
          if (agentId) {
            event.preventDefault();
            lastMention.setAttribute('data-processed', 'true');
            agentResponseHandlerRef.value.handleChat(agentId, userInput, editorRef);
          }
        }
      }
    }
  }
};

const showAgentSelectorAt = (range: any) => {
  editorState.currentRange.value = range;
  editorState.showAgentSelector.value = true;
  
  nextTick(() => {
    if (mentionHandlerRef.value) {
      mentionHandlerRef.value.updateSelectorPosition();
    }
  });
};

const onAgentSelected = (agent: any) => {
  editorState.showAgentSelector.value = false;
  
  setTimeout(() => {
    const newContent = formatting.getFullContent(editorContentRef.value?.editorRef);
    emit('update:modelValue', newContent);
    
    setTimeout(() => {
      const agentInputs = document.querySelectorAll('.agent-input');
      if (agentInputs.length > 0) {
        const latestInput = agentInputs[agentInputs.length - 1] as HTMLInputElement;
        if (latestInput) {
          latestInput.focus();
        }
      }
    }, 100);
  }, 0);
};

const handleSendToAgent = (data: any) => {
  console.log('发送消息到Agent', data);
  
  const agentResponseHandler = agentResponseHandlerRef.value;
  if (!agentResponseHandler) {
    console.error('无法获取AgentResponseHandler引用');
    return;
  }
  
  agentResponseHandler.handleInputChat(
    data.inputElement,
    data.agentId,
    data.content,
    data.containerElement
  );
};

const showAgentModalAt = (data: any) => {
  console.log('显示Agent输入界面，接收到的定位数据:', data);
  console.log('当前交互模式:', editorState.interactionMode.value);
  
  // 保存光标范围
  if (data.range) {
    try {
      const container = data.range.startContainer;
      if (document.contains(container)) {
        editorState.currentCursorRange.value = data.range.cloneRange();
        console.log('[EditorContainer] 已保存光标位置');
      } else {
        console.warn('[EditorContainer] 传入的范围容器不在文档中');
        editorState.currentCursorRange.value = null;
      }
    } catch (error) {
      console.warn('[EditorContainer] 无法保存光标位置:', error);
      editorState.currentCursorRange.value = null;
    }
  }
  
  // 根据当前模式显示对应界面
  if (editorState.interactionMode.value === 'sidebar') {
    emit('toggle-sidebar-mode', {
      currentMode: editorState.interactionMode.value,
      showSidebar: true,
      agentResponse: editorState.currentAgentResponse.value,
      isAgentResponding: editorState.isAgentResponding.value,
      historyIndex: editorState.historyDisplayIndex.value,
      historyLength: editorState.conversationHistory.value.length
    });
    editorState.showAgentModal.value = false;
  } else {
    // 弹窗模式：设置位置和编辑器信息，然后显示弹窗
    if (data.cursorPosition && data.cursorPosition.viewport) {
      editorState.updateModalPosition({
        y: data.cursorPosition.viewport.y,
        x: data.cursorPosition.viewport.x
      });
    }
    
    if (data.editorInfo) {
      editorState.updateEditorInfo(data.editorInfo);
    }
    
    // 重要：在显示弹窗之前，确保弹窗已经有历史数据
    // 如果当前有历史记录，确保弹窗能看到最新的回复
    if (editorState.conversationHistory.value.length > 0) {
      // 默认显示最后一条（最新的）历史记录
      const lastIndex = editorState.conversationHistory.value.length - 1;
      editorState.historyDisplayIndex.value = lastIndex;
      
      const lastHistoryItem = editorState.conversationHistory.value[lastIndex];
      if (lastHistoryItem && lastHistoryItem.agent) {
        // 显示最新的历史回复
        editorState.currentAgentResponse.value = lastHistoryItem.agent;
        console.log('[EditorContainer] 弹窗显示最新历史记录，索引:', lastIndex);
      }
    } else {
      // 没有历史记录时重置状态
      editorState.historyDisplayIndex.value = -1;
      editorState.currentAgentResponse.value = '';
    }
    
    console.log('[EditorContainer] 弹窗显示时的状态:', {
      agentResponse: editorState.currentAgentResponse.value,
      isAgentResponding: editorState.isAgentResponding.value,
      historyIndex: editorState.historyDisplayIndex.value,
      historyLength: editorState.conversationHistory.value.length,
      hasConversationHistory: editorState.conversationHistory.value.length > 0
    });
    
    editorState.showAgentModal.value = true;
    console.log('弹窗模式：显示弹窗');
  }
};

const handleAgentMessage = (data: any) => {
  console.log('[EditorContainer] handleAgentMessage, data:', data);
  
  if (editorState.interactionMode.value === 'sidebar') {
    emit('sidebar-send', {
      ...data,
      conversationId: props.conversationId,
      noteId: props.noteId
    });
    return;
  }
  
  // 弹窗模式下的逻辑
  editorState.currentSentMessageData.value = data;
  editorState.isAgentResponding.value = true;
  editorState.currentAgentResponse.value = '';

  if (agentResponseHandlerRef.value) {
    if (typeof agentResponseHandlerRef.value.setConversationId === 'function') {
      agentResponseHandlerRef.value.setConversationId(props.conversationId);
    }
    
    if (typeof agentResponseHandlerRef.value.setCurrentNoteId === 'function' && props.noteId) {
      agentResponseHandlerRef.value.setCurrentNoteId(props.noteId);
    }
    
    if (typeof agentResponseHandlerRef.value.triggerChatRequest === 'function') {
      // 传递模型信息（如果有的话）
      agentResponseHandlerRef.value.triggerChatRequest(
        data.agentId, 
        data.content, 
        null, // responseParagraph
        data.model // 模型信息
      );
    }
  }
};

const handleHistoryNavigation = (payload: any) => {
  if (editorState.interactionMode.value === 'sidebar') {
    emit('sidebar-navigate-history', payload);
    return;
  }
  
  // 弹窗模式下的逻辑
  if (!editorState.conversationHistory.value || editorState.conversationHistory.value.length === 0) return;

  const { direction } = payload;
  let newIndex = editorState.historyDisplayIndex.value;

  if (direction === 'prev' && editorState.historyDisplayIndex.value > 0) {
    newIndex--;
  } else if (direction === 'next' && editorState.historyDisplayIndex.value < editorState.conversationHistory.value.length - 1) {
    newIndex++;
  }

  if (newIndex !== editorState.historyDisplayIndex.value) {
    editorState.historyDisplayIndex.value = newIndex;
    const historicResponse = editorState.conversationHistory.value[newIndex].agent;
    editorState.currentAgentResponse.value = historicResponse;
  }
};

const handleInsertResponse = async (responseText: string, fromSidebar = false) => {
  // 如果是从侧边栏来的插入请求，不要再次发出sidebar-insert事件，直接插入
  if (editorState.interactionMode.value === 'sidebar' && !fromSidebar) {
    emit('sidebar-insert', responseText);
    return;
  }
  
  // 插入内容到光标位置
  const editorRef = editorContentRef.value?.editorRef;
  await cursorManager.insertContentAtCursor(
    responseText, 
    editorRef, 
    editorState.currentCursorRange.value
  );
  
  // 清除保存的光标位置
  editorState.currentCursorRange.value = null;
};

// 加载会话历史记录
const loadConversationHistory = async (sessionId: number | string | null) => {
  // 如果会话ID与上次加载的相同，跳过重复加载
  if (sessionId && sessionId === editorState.lastLoadedSessionId.value) {
    console.log(`[EditorContainer] 会话ID ${sessionId} 已经加载过，跳过重复加载`);
    return;
  }
  
  if (!sessionId) {
    // 没有会话ID，清空历史记录
    editorState.conversationHistory.value = [];
    editorState.historyDisplayIndex.value = -1;
    editorState.currentAgentResponse.value = '';
    editorState.lastLoadedSessionId.value = null;
    console.log('[EditorContainer] 没有会话ID，清空历史记录');
    
    // 即使没有历史记录，也通知父组件清空侧边栏
    emit('conversation-history-loaded', {
      sessionId: sessionId,
      history: [],
      length: 0
    });
    return;
  }

  try {
    console.log(`[EditorContainer] 开始加载会话 ${sessionId} 的历史记录`);
    const { default: chatService } = await import('../../services/chat');
    const history = await chatService.getSessionAgentHistory(Number(sessionId));
    
    if (history && history.length > 0) {
      editorState.conversationHistory.value = history;
      editorState.historyDisplayIndex.value = history.length - 1; // 默认显示最新的记录
      editorState.currentAgentResponse.value = history[history.length - 1].agent; // 显示最新的AI回复
      editorState.lastLoadedSessionId.value = sessionId; // 记录已加载的会话ID
      console.log(`[EditorContainer] 加载了 ${history.length} 条历史记录，当前显示索引: ${editorState.historyDisplayIndex.value}`);
      
      // 通知父组件更新侧边栏的会话历史
      emit('conversation-history-loaded', {
        sessionId: sessionId,
        history: history,
        length: history.length
      });
    } else {
      editorState.conversationHistory.value = [];
      editorState.historyDisplayIndex.value = -1;
      editorState.currentAgentResponse.value = '';
      editorState.lastLoadedSessionId.value = sessionId; // 即使没有历史记录，也记录会话ID避免重复请求
      console.log('[EditorContainer] 没有找到历史记录');
      
      // 即使没有历史记录，也通知父组件清空侧边栏
      emit('conversation-history-loaded', {
        sessionId: sessionId,
        history: [],
        length: 0
      });
    }
  } catch (error) {
    console.error('[EditorContainer] 加载历史记录失败:', error);
    editorState.conversationHistory.value = [];
    editorState.historyDisplayIndex.value = -1;
    editorState.currentAgentResponse.value = '';
    editorState.lastLoadedSessionId.value = sessionId; // 即使失败，也记录会话ID避免重复请求
    
    // 加载失败时也通知父组件清空侧边栏
    emit('conversation-history-loaded', {
      sessionId: sessionId,
      history: [],
      length: 0
    });
  }
};

const onNoteEditPreview = async (previewData: any) => {
  console.log('[EditorContainer] 收到笔记编辑预览事件:', previewData);
  
  if (props.noteId && previewData.noteId && parseInt(props.noteId) === previewData.noteId) {
    console.log('[EditorContainer] 显示当前笔记的编辑预览');
    
    previewManager.pendingEditData.value = previewData;
    previewManager.originalContentForPreview.value = props.modelValue || '';
    
    const editorElement = editorContentRef.value?.editorRef;
    await previewManager.insertPreviewContentInEditor(
      previewData, 
      editorElement,
      handleAcceptInlinePreview,
      handleRejectInlinePreview
    );
  }
};

const handleAcceptInlinePreview = async (previewData: any) => {
  console.log('[EditorContainer] 用户接受内联预览编辑');
  
  try {
    previewManager.clearExistingPreview();
    
    // 调用后端API应用预览编辑
    if (props.noteId) {
      const { default: noteService } = await import('../../services/note');
      await noteService.applyEditPreview(parseInt(props.noteId), {
        content: previewData.content,
        title: previewData.title
      });
    }
    
    // 渲染新内容的markdown
    let renderedContent = previewData.content;
    try {
      const { processMarkdown } = await import('../../services/agentResponseService');
      renderedContent = processMarkdown(previewData.content);
    } catch (error) {
      console.error('渲染markdown失败:', error);
      // 如果渲染失败，至少处理换行
      renderedContent = previewData.content.replace(/\n/g, '<br>');
    }
    
    emit('update:modelValue', renderedContent);
    
    if (previewData.title) {
      emit('title-updated', previewData.title);
    }
    
    previewManager.pendingEditData.value = null;
    previewManager.originalContentForPreview.value = '';
    
    previewManager.showSuccessMessage('编辑已应用并保存');
    
    // 延迟渲染特殊组件（代码块、图表等）
    setTimeout(async () => {
      try {
        const { renderContentComponents } = await import('../../services/renderService');
        renderContentComponents(true);
      } catch (error) {
        console.error('渲染特殊组件失败:', error);
      }
    }, 100);
    
  } catch (error) {
    console.error('[EditorContainer] 应用编辑失败:', error);
    previewManager.showErrorMessage('应用编辑失败，请重试');
  }
};

const handleRejectInlinePreview = (originalContent: string) => {
  console.log('[EditorContainer] 用户拒绝内联预览编辑');
  
  const editorElement = editorContentRef.value?.editorRef;
  if (editorElement) {
    editorElement.innerHTML = originalContent;
  }
  
  previewManager.clearExistingPreview();
  previewManager.pendingEditData.value = null;
  previewManager.originalContentForPreview.value = '';
  
  previewManager.showInfoMessage('编辑已取消');
};

// 监听modelValue变化
watch(() => props.modelValue, (newValue, oldValue) => {
  console.log('EditorContainer接收到新内容，长度:', newValue.length);
  
  if (editorContentRef.value && editorContentRef.value.editorRef) {
    if (editorContentRef.value.editorRef.innerHTML !== newValue) {
      if (oldValue && Math.abs(oldValue.length - newValue.length) < 10 && 
          oldValue.replace(/\s+/g, '') === newValue.replace(/\s+/g, '')) {
        console.log('内容变化很小，可能是格式化导致，忽略更新');
        return;
      }
      
      // 检查是否有已挂载的画板组件，如果有则跳过DOM重写
      const mountedCanvases = document.querySelectorAll('.canvas-mounted[data-canvas-id]');
      if (mountedCanvases.length > 0) {
        console.log(`[EditorContainer] 发现${mountedCanvases.length}个已挂载的画板组件，跳过DOM重写以保护组件`);
        return;
      }
      
      console.log('更新编辑器DOM内容');
      editorContentRef.value.editorRef.innerHTML = newValue;
      
      nextTick(async () => {
        try {
          console.log('内容更新后触发markdown渲染');
          const { renderContentComponents } = await import('../../services/renderService');
          renderContentComponents(true);
          
          // 内容更新后，尝试重新初始化画板组件
          console.log('[EditorContainer] 内容更新后重新初始化画板组件');
          initializeExistingCanvases();
        } catch (error) {
          console.error('渲染markdown内容失败:', error);
        }
      });
    }
  }
}, { immediate: true });

// 监听conversationId变化，同步到AgentResponseHandler
watch(() => props.conversationId, (newId) => {
  if (agentResponseHandlerRef.value) {
    console.log(`编辑器接收到会话ID: ${newId || 'null'}，设置到AgentResponseHandler`);
    // 无论newId是否为null都要设置，确保新建会话时能正确清空
    agentResponseHandlerRef.value.setConversationId(newId ? String(newId) : null);
  }
  
  // 加载会话的历史记录
  loadConversationHistory(newId);
}, { immediate: true });

// 监听noteId变化，同步到AgentResponseHandler
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

// 组件挂载后聚焦编辑器
onMounted(() => {
  nextTick(() => {
    editorContentRef.value?.focus();
    
    // 初始化已存在的画板组件
    initializeExistingCanvases();
    
    // 初始化AgentResponseHandler
    if (agentResponseHandlerRef.value) {
      if (typeof agentResponseHandlerRef.value.setConversationId === 'function') {
        agentResponseHandlerRef.value.setConversationId(props.conversationId);
      }
      
      if (typeof agentResponseHandlerRef.value.setCurrentNoteId === 'function' && props.noteId) {
        agentResponseHandlerRef.value.setCurrentNoteId(props.noteId);
      }
    }
  });
});

// 清理事件监听器
onUnmounted(() => {
  // 清理所有画板实例
  canvasInstances.forEach((canvasData) => {
    if (canvasData.app) {
      canvasData.app.unmount();
    }
  });
  canvasInstances.clear();
});

// 设置交互模式
const setInteractionMode = (mode: 'modal' | 'sidebar') => {
  console.log(`[EditorContainer] setInteractionMode被调用，从 ${editorState.interactionMode.value} 切换到 ${mode}`);
  editorState.interactionMode.value = mode;
  console.log(`[EditorContainer] interactionMode已更新为: ${editorState.interactionMode.value}`);
};

// 获取当前Agent数据
const getCurrentAgentData = () => {
  return {
    agentResponse: editorState.currentAgentResponse.value,
    isAgentResponding: editorState.isAgentResponding.value,
    historyIndex: editorState.historyDisplayIndex.value,
    historyLength: editorState.conversationHistory.value.length,
    conversationHistory: editorState.conversationHistory.value
  };
};

// 关闭模态窗口
const closeModal = () => {
  editorState.showAgentModal.value = false;
};

// 显示模态窗口并填充内容
const showModalWithContent = (data: any) => {
  if (data.response) {
    editorState.currentAgentResponse.value = data.response;
  }
  if (data.isResponding !== undefined) {
    editorState.isAgentResponding.value = data.isResponding;
  }
  if (data.conversationHistory) {
    editorState.conversationHistory.value = data.conversationHistory;
  }
  
  // 如果传入了历史记录，默认显示最后一条（最新的）
  if (data.conversationHistory && data.conversationHistory.length > 0) {
    const lastIndex = data.conversationHistory.length - 1;
    editorState.historyDisplayIndex.value = lastIndex;
    
    // 如果没有传入特定的response，使用最新历史记录的agent回复
    if (!data.response) {
      const lastHistoryItem = data.conversationHistory[lastIndex];
      if (lastHistoryItem && lastHistoryItem.agent) {
        editorState.currentAgentResponse.value = lastHistoryItem.agent;
        console.log('[EditorContainer] showModalWithContent显示最新历史记录，索引:', lastIndex);
      }
    }
  } else {
    // 如果明确传入了historyIndex，使用它
    if (data.historyIndex !== undefined) {
      editorState.historyDisplayIndex.value = data.historyIndex;
    }
  }
  
  editorState.showAgentModal.value = true;
};

// 暴露方法给父组件
defineExpose({
  onNoteEditPreview,
  focus: () => editorContentRef.value?.focus(),
  getContent: () => formatting.getFullContent(editorContentRef.value?.editorRef),
  setContent: (content: string) => emit('update:modelValue', content),
  setInteractionMode,
  getCurrentAgentData,
  closeModal,
  showModalWithContent,
  handleInsertResponse,
  editorContentRef: () => editorContentRef.value,
  restoreEditorState: (stateData: any) => {
    if (editorContentRef.value && editorContentRef.value.restoreEditorState) {
      return editorContentRef.value.restoreEditorState(stateData)
    }
    return false
  }
});
</script>

<style>
/* 复制原来的样式 */
.editor-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.editor-toolbar-fixed {
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f9f9f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  width: 100%;
  flex-shrink: 0;
}

.editor-content-wrapper {
  display: flex;
  flex: 1;
  position: relative;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}

.document-outline {
  flex-shrink: 0;
  position: sticky;
  top: 60px;
  align-self: flex-start;
  max-height: calc(100vh - 60px);
  overflow-y: auto;
}

.editor-main {
  flex: 1;
  position: relative;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 预览编辑高亮样式 - 类似VS Code */
.preview-deleted-content {
  background-color: #ffeef0;
  border-left: 4px solid #f85149;
  margin: 8px 0;
  padding: 8px 12px;
  position: relative;
  text-decoration: line-through;
  opacity: 0.8;
}

.preview-deleted-content::before {
  content: "删除";
  position: absolute;
  top: -8px;
  left: 8px;
  background-color: #f85149;
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.preview-added-content {
  background-color: #e6ffed;
  border-left: 4px solid #2ea043;
  margin: 8px 0;
  padding: 8px 12px;
  position: relative;
  animation: fadeInGlow 0.5s ease-in-out;
}

.preview-added-content::before {
  content: "新增";
  position: absolute;
  top: -8px;
  left: 8px;
  background-color: #2ea043;
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.preview-added-content.inline {
  display: inline;
  margin: 0;
  padding: 2px 4px;
  border-left: none;
  border-radius: 3px;
  background-color: #d1f4d9;
  border: 1px solid #2ea043;
}

.preview-added-content.inline::before {
  display: none;
}

/* 发光动画效果 */
@keyframes fadeInGlow {
  0% {
    opacity: 0;
    box-shadow: 0 0 0 rgba(46, 160, 67, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(46, 160, 67, 0.3);
  }
  100% {
    opacity: 1;
    box-shadow: 0 0 0 rgba(46, 160, 67, 0);
  }
}

/* 从右下角滑入的动画 */
@keyframes slideInBottomRight {
  from {
    opacity: 0;
    transform: translate(10px, 10px);
  }
  to {
    opacity: 1;
    transform: translate(0, 0);
  }
}

/* 浮动操作按钮 */
.preview-floating-buttons {
  position: absolute;
  bottom: 10px;
  right: 15px;
  z-index: 1000;
  animation: slideInBottomRight 0.3s ease-out;
}

.preview-floating-buttons .button-group {
  display: flex;
  gap: 6px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  padding: 4px;
  border: 1px solid #e1e4e8;
}

.preview-action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.preview-action-btn.accept {
  background-color: #2ea043;
  color: white;
}

.preview-action-btn.accept:hover {
  background-color: #2c974b;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3);
}

.preview-action-btn.reject {
  background-color: #f85149;
  color: white;
}

.preview-action-btn.reject:hover {
  background-color: #dc3545;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(248, 81, 73, 0.3);
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 鼠标悬停在预览内容上的效果 */
.preview-added-content:hover {
  background-color: #d1f4d9;
  border-left-color: #22863a;
}

.preview-deleted-content:hover {
  background-color: #ffd6cc;
  border-left-color: #d73a49;
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .preview-added-content {
    background-color: #0d1117;
    border-left-color: #2ea043;
    color: #58a6ff;
  }
  
  .preview-deleted-content {
    background-color: #0d1117;
    border-left-color: #f85149;
    color: #f85149;
  }
  
  .preview-floating-buttons .button-group {
    background: #21262d;
    border-color: #30363d;
  }
}

/* 画板占位元素样式 */
.canvas-placeholder {
  width: 100%;
  height: 200px;
  border: 2px dashed #d0d7de;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f6f8fa;
  color: #656d76;
  font-size: 14px;
  margin: 16px 0;
  transition: all 0.2s ease;
}

/* 只有在真正为空时才显示占位文字 */
.canvas-placeholder:empty::before {
  content: '正在加载画板组件...';
}

/* 当有子元素时不显示占位文字 */
.canvas-placeholder:not(:empty) {
  border: none;
  background: transparent;
  height: auto;
  padding: 0;
}

.canvas-placeholder:hover {
  border-color: #8b949e;
  background-color: #f3f4f6;
}

/* 当画板已挂载时，不显示悬停效果 */
.canvas-placeholder:not(:empty):hover {
  border-color: transparent;
  background-color: transparent;
}

/* 确保嵌入式画板组件正常显示 */
.canvas-placeholder .embedded-canvas-wrapper,
.canvas-placeholder .canvas-board {
  border: none !important;
  margin: 0 !important;
  background: transparent !important;
}

/* 已挂载的画板容器样式 */
.canvas-mounted {
  width: 100%;
  margin: 16px 0;
  border: none;
  background: transparent;
  padding: 0;
  display: block;
}

/* 确保已挂载的画板完全覆盖容器 */
.canvas-mounted .embedded-canvas-wrapper {
  width: 100%;
  margin: 0;
}
</style> 