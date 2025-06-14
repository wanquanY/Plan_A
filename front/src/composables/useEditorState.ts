import { ref, reactive } from 'vue';

export interface EditorStateConfig {
  initialValue?: string;
  conversationId?: string | null;
  noteId?: string | null;
}

export function useEditorState(config: EditorStateConfig = {}) {
  // 基本状态
  const wordCount = ref(0);
  const isComposing = ref(false);
  const showAgentSelector = ref(false);
  const currentRange = ref(null);
  const selectedHeading = ref('p');
  const showOutline = ref(false);
  const showAgentModal = ref(false);
  const interactionMode = ref<'modal' | 'sidebar'>('modal');
  const currentCursorRange = ref(null);
  
  // UI状态
  const modalPosition = ref({ y: 0, x: 0 });
  const editorInfo = ref({ 
    left: 0, 
    right: 0, 
    width: 0, 
    editorOffsetLeft: 0 
  });
  
  // AI助手相关状态
  const currentAgentResponse = ref('');
  const isAgentResponding = ref(false);
  const currentSentMessageData = ref(null);
  const conversationHistory = ref<Array<{ user: string; agent: string }>>([]);
  const historyDisplayIndex = ref(-1);
  const lastLoadedSessionId = ref(null);
  const currentToolStatus = ref(null);
  
  // 控制状态
  const showTools = ref(false);
  const showHistory = ref(false);
  const showWordCloud = ref(false);
  const loading = ref(false);
  const saving = ref(false);
  
  // 编辑预览相关状态
  const pendingEditData = ref(null);
  const originalContentForPreview = ref('');
  const previewedContent = ref('');

  // 重置状态的方法
  const resetState = () => {
    wordCount.value = 0;
    showAgentSelector.value = false;
    currentRange.value = null;
    showAgentModal.value = false;
    currentCursorRange.value = null;
    currentAgentResponse.value = '';
    isAgentResponding.value = false;
    currentSentMessageData.value = null;
    conversationHistory.value = [];
    historyDisplayIndex.value = -1;
    currentToolStatus.value = null;
    pendingEditData.value = null;
    originalContentForPreview.value = '';
    previewedContent.value = '';
  };

  // 更新编辑器信息
  const updateEditorInfo = (info: Partial<typeof editorInfo.value>) => {
    editorInfo.value = { ...editorInfo.value, ...info };
  };

  // 更新模态位置
  const updateModalPosition = (position: { y: number; x: number }) => {
    modalPosition.value = position;
  };

  return {
    // 状态
    wordCount,
    isComposing,
    showAgentSelector,
    currentRange,
    selectedHeading,
    showOutline,
    showAgentModal,
    interactionMode,
    currentCursorRange,
    modalPosition,
    editorInfo,
    currentAgentResponse,
    isAgentResponding,
    currentSentMessageData,
    conversationHistory,
    historyDisplayIndex,
    lastLoadedSessionId,
    currentToolStatus,
    showTools,
    showHistory,
    showWordCloud,
    loading,
    saving,
    pendingEditData,
    originalContentForPreview,
    previewedContent,
    
    // 方法
    resetState,
    updateEditorInfo,
    updateModalPosition,
  };
} 