<script setup lang="ts">
import { ref, nextTick, inject, watch, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import authService from '../services/auth';
import Editor from '../components/editor/Editor.vue';
import MermaidRenderer from '@/components/rendering/MermaidRenderer.vue';
import AgentSidebar from '../components/Agent/AgentSidebar.vue';

// 导入 composables
import { useNoteManager } from '../composables/useNoteManager';
import { useSessionManager } from '../composables/useSessionManager';
import { useRouteManager } from '../composables/useRouteManager';
import { useSidebarManager } from '../composables/useSidebarManager';

// 使用 composables
const noteManager = useNoteManager();
const sessionManager = useSessionManager();
const routeManager = useRouteManager();
const sidebarManager = useSidebarManager();

// 从全局布局获取数据
const fetchNotes = inject('fetchNotes');
const noteRenamedEvent = inject('noteRenamedEvent');

// 组件引用
const editorRef = ref(null);
const agentSidebarRef = ref(null);
const wordCount = ref(0);

// 侧边栏宽度管理
const sidebarWidth = ref(400);

// 处理侧边栏宽度变化
const handleSidebarResize = (newWidth: number) => {
  sidebarWidth.value = newWidth;
};

// 从localStorage恢复侧边栏宽度
const restoreSidebarWidth = () => {
  try {
    const savedWidth = localStorage.getItem('agent-sidebar-width');
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width >= 300 && width <= 600) {
        sidebarWidth.value = width;
      }
    }
  } catch (error) {
    console.warn('无法从localStorage恢复侧边栏宽度:', error);
  }
};

// 初始化路由逻辑
routeManager.initializeRoute(
  async (noteId: number) => {
    // 先清理侧边栏历史记录
    sessionManager.clearSidebarHistory();
    
    const result = await noteManager.fetchNoteDetail(noteId);
    if (result && result.note) {
      // 如果笔记有关联的session_id，加载会话历史记录到侧边栏
      if (result.note.session_id && !routeManager.route.query.sessionId) {
        console.log(`笔记关联了会话ID: ${result.note.session_id}，设置currentSessionId并加载历史记录`);
        sessionManager.currentSessionId.value = result.note.session_id;
        
        try {
          await sessionManager.loadSessionHistoryToSidebar(result.note.session_id);
        } catch (error) {
          console.error('加载关联会话历史记录失败:', error);
        }
      } else {
        console.log('笔记没有关联的session_id或URL中已有sessionId，清空会话历史');
      }
    }
  },
  async (sessionId: number) => {
    const result = await sessionManager.fetchSessionDetail(sessionId);
    if (result) {
      noteManager.editorContent.value = result.content;
      noteManager.editorTitle.value = result.title;
      
      // 处理复杂的渲染逻辑
      if (result.needsComplexRendering) {
        nextTick(async () => {
          try {
            // 先立即尝试渲染一次
            console.log('立即强制渲染思维导图，不等待DOM完全加载');
            
            // 导入需要的渲染服务
            const { renderContentComponents, cleanupMarkmapElements } = await import('../services/renderService');
        
            // 先清理所有已存在的思维导图元素
            cleanupMarkmapElements();
            
            // 立即强制渲染一次
            renderContentComponents(true);
            
            // 设置短延迟后再次尝试渲染，确保内容完全加载
            setTimeout(() => {
              console.log('设置短延迟再次尝试渲染思维导图');
              renderContentComponents(true);
            }, 300);
            
            // 如果检测到特殊内容，给予更长的时间再尝试一次
            setTimeout(() => {
              const content = result.note.content || '';
              if (content.includes('```markdown') || content.includes('# ')) {
                console.log('检测到可能包含思维导图的内容，再次尝试渲染');
                renderContentComponents(true);
          }
            }, 800);
          } catch (error) {
            console.error('思维导图渲染失败:', error);
          }
        });
      } else {
        nextTick(() => {
          renderContentComponents(true);
      });
      }
    }
  },
  async (sessionId: number) => {
    const noteData = await noteManager.fetchNoteBySessionId(sessionId);
    if (noteData) {
      // 更新URL，添加note参数但不改变编辑器内容
      routeManager.updateUrlParams({ note: noteData.id });
    }
  },
  () => {
    sessionManager.clearSidebarHistory();
    noteManager.createNewNote();
  },
  fetchNotes
);

// 监听路由变化
routeManager.watchRouteChanges(
  async (noteId: number) => {
    // 先清理侧边栏历史记录
    sessionManager.clearSidebarHistory();
    
    const result = await noteManager.fetchNoteDetail(noteId);
    if (result && result.note) {
      // 如果笔记有关联的session_id，加载会话历史记录到侧边栏
      if (result.note.session_id && !routeManager.route.query.sessionId) {
        console.log(`笔记关联了会话ID: ${result.note.session_id}，设置currentSessionId并加载历史记录`);
        sessionManager.currentSessionId.value = result.note.session_id;
        
        try {
          await sessionManager.loadSessionHistoryToSidebar(result.note.session_id);
        } catch (error) {
          console.error('加载关联会话历史记录失败:', error);
        }
      } else {
        console.log('笔记没有关联的session_id或URL中已有sessionId，清空会话历史');
      }
      
      // 处理复杂的渲染逻辑
      if (result.needsComplexRendering) {
        nextTick(async () => {
          try {
            // 先立即尝试渲染一次
            console.log('立即强制渲染思维导图，不等待DOM完全加载');
            
            // 导入需要的渲染服务
            const { renderContentComponents, cleanupMarkmapElements } = await import('../services/renderService');
            
            // 先清理所有已存在的思维导图元素
            cleanupMarkmapElements();
            
            // 立即强制渲染一次
            renderContentComponents(true);
            
            // 设置短延迟后再次尝试渲染，确保内容完全加载
            setTimeout(() => {
              console.log('设置短延迟再次尝试渲染思维导图');
              renderContentComponents(true);
            }, 300);
            
            // 如果检测到特殊内容，给予更长的时间再尝试一次
            setTimeout(() => {
              const content = result.note.content || '';
              if (content.includes('```markdown') || content.includes('# ')) {
                console.log('检测到可能包含思维导图的内容，再次尝试渲染');
                renderContentComponents(true);
              }
            }, 800);
          } catch (error) {
            console.error('思维导图渲染失败:', error);
          }
        });
      } else {
        nextTick(() => {
          renderContentComponents(true);
        });
      }
    }
  },
  async (sessionId: number) => {
    const result = await sessionManager.fetchSessionDetail(sessionId);
    if (result) {
      noteManager.editorContent.value = result.content;
      noteManager.editorTitle.value = result.title;
      
      // 处理复杂的渲染逻辑
      if (result.needsComplexRendering) {
        nextTick(async () => {
          try {
            // 先立即尝试渲染一次
            console.log('立即强制渲染思维导图，不等待DOM完全加载');
            
            // 导入需要的渲染服务
            const { renderContentComponents, cleanupMarkmapElements } = await import('../services/renderService');
            
            // 先清理所有已存在的思维导图元素
            cleanupMarkmapElements();
            
            // 立即强制渲染一次
            renderContentComponents(true);
            
            // 设置短延迟后再次尝试渲染，确保内容完全加载
            setTimeout(() => {
              console.log('设置短延迟再次尝试渲染思维导图');
              renderContentComponents(true);
            }, 300);
            
            // 如果检测到特殊内容，给予更长的时间再尝试一次
            setTimeout(() => {
              const content = result.note.content || '';
              if (content.includes('```markdown') || content.includes('# ')) {
                console.log('检测到可能包含思维导图的内容，再次尝试渲染');
                renderContentComponents(true);
              }
            }, 800);
          } catch (error) {
            console.error('思维导图渲染失败:', error);
          }
        });
      } else {
      nextTick(() => {
        renderContentComponents(true);
      });
    }
    }
  },
  async (sessionId: number) => {
    const noteData = await noteManager.fetchNoteBySessionId(sessionId);
    if (noteData) {
      // 更新URL，添加note参数但不改变编辑器内容
      routeManager.updateUrlParams({ note: noteData.id });
    }
  },
  () => {
    sessionManager.clearSidebarHistory();
    noteManager.createNewNote();
  },
  sessionManager.clearSidebarHistory
);

// 更新字数
const updateWordCount = (count: number) => {
  wordCount.value = count;
};

// 处理登出
const handleLogout = () => {
  authService.logout();
  routeManager.router.push('/login');
};

// 新建笔记
const handleNewNote = () => {
  sessionManager.clearSidebarHistory();
  noteManager.createNewNote();
};

// 处理侧边栏模式切换
const handleToggleSidebarMode = (data: any) => {
  // 将当前侧边栏状态合并到data中
  const dataWithCurrentState = {
    ...data,
    agentResponse: sessionManager.sidebarAgentResponse.value,
    isAgentResponding: sessionManager.sidebarIsAgentResponding.value,
    historyIndex: sessionManager.sidebarHistoryIndex.value,
    historyLength: sessionManager.sidebarHistoryLength.value
  };
  
  const result = sidebarManager.handleToggleSidebarMode(dataWithCurrentState, editorRef, sessionManager.sidebarConversationHistory);
  
  if (result) {
    sessionManager.sidebarAgentResponse.value = result.agentResponse;
    sessionManager.sidebarIsAgentResponding.value = result.isAgentResponding;
    sessionManager.sidebarHistoryIndex.value = result.historyIndex;
    sessionManager.sidebarHistoryLength.value = result.historyLength;
  }
};

// 处理侧边栏发送消息
const handleSidebarSend = async (data: any) => {
  try {
    // 使用可靠的方法获取当前笔记ID
    let currentNoteId = noteManager.getCurrentNoteId();
    
    // 如果还是没有笔记ID，尝试从URL获取
    if (!currentNoteId && routeManager.route.query.note) {
      const noteIdFromUrl = parseInt(routeManager.route.query.note as string);
      if (!isNaN(noteIdFromUrl)) {
        console.log('从URL获取笔记ID:', noteIdFromUrl);
        currentNoteId = noteIdFromUrl;
        noteManager.currentNoteId.value = noteIdFromUrl;
        localStorage.setItem('lastNoteId', noteIdFromUrl.toString());
      }
    }
    
    console.log('发送消息时的笔记ID:', currentNoteId);
    
    // 如果仍然没有笔记ID，给出警告但不阻止发送
    if (!currentNoteId) {
      console.warn('警告：发送消息时没有找到笔记ID，消息可能无法正确关联到笔记');
    }
    
    // 定义工具状态处理回调
    const handleToolStatus = (toolStatus: any) => {
      if (toolStatus && agentSidebarRef.value && agentSidebarRef.value.handleToolStatus) {
        console.log('Home.vue 收到工具状态更新:', toolStatus);
        console.log('调用 AgentSidebar.handleToolStatus');
        agentSidebarRef.value.handleToolStatus(toolStatus);
      }
    };
    
    // 创建一个包装的ref对象，确保传递正确的值
    const noteIdRef = ref(currentNoteId);
    
    await sessionManager.handleSidebarSend(data, noteIdRef, handleToolStatus);
  } catch (error) {
    console.error('发送消息失败:', error);
  }
};

// 处理侧边栏插入文本
const handleSidebarInsert = (text: string) => {
  sidebarManager.handleSidebarInsert(text, editorRef, noteManager.editorContent);
};

// 处理侧边栏导航历史
const handleSidebarNavigateHistory = (payload: any) => {
  sessionManager.handleSidebarNavigateHistory(payload);
};

// 处理侧边栏编辑消息
const handleSidebarEditMessage = (data: any) => {
  sessionManager.handleSidebarEditMessage(data);
};

// 处理笔记编辑预览事件（从AgentSidebar传递到Editor）
const handleNoteEditPreview = (previewData: any) => {
  console.log('[Home.vue] 收到来自AgentSidebar的笔记编辑预览事件:', previewData);
  
  // 检查是否有Editor组件的引用，并将预览事件传递给它
  if (editorRef.value && typeof editorRef.value.onNoteEditPreview === 'function') {
    editorRef.value.onNoteEditPreview(previewData);
    console.log('[Home.vue] 已将预览事件传递给Editor');
  } else {
    console.warn('[Home.vue] 无法找到Editor的onNoteEditPreview方法');
  }
};

// 关闭侧边栏
const closeSidebar = () => {
  const result = sidebarManager.closeSidebar(editorRef);
  sessionManager.sidebarAgentResponse.value = result.agentResponse;
  sessionManager.sidebarIsAgentResponding.value = result.isAgentResponding;
  sessionManager.sidebarHistoryIndex.value = result.historyIndex;
  sessionManager.sidebarHistoryLength.value = result.historyLength;
};

// 处理会话历史记录加载
const handleConversationHistoryLoaded = (data: any) => {
  console.log('接收到会话历史记录加载事件:', data);
  
  if (data.history && data.history.length > 0) {
    console.log(`设置侧边栏历史记录，条数: ${data.history.length}`);
    sessionManager.sidebarConversationHistory.value = [...data.history];
    sessionManager.sidebarHistoryLength.value = data.history.length;
    sessionManager.sidebarHistoryIndex.value = data.history.length - 1;
  } else {
    console.log('清空侧边栏历史记录');
    sessionManager.sidebarConversationHistory.value = [];
    sessionManager.sidebarHistoryLength.value = 0;
    sessionManager.sidebarHistoryIndex.value = -1;
  }
};

// 渲染内容组件
const renderContentComponents = async (forceRender = true) => {
  try {
    const { renderContentComponents } = await import('../services/renderService');
    renderContentComponents(forceRender);
  } catch (error) {
    console.error('渲染组件时出错:', error);
  }
};

// 监听笔记重命名事件
watch(noteRenamedEvent, (newEvent) => {
  if (newEvent && newEvent.title && newEvent.noteId && noteManager.currentNoteId.value) {
    if (newEvent.noteId === noteManager.currentNoteId.value) {
      console.log('收到当前笔记重命名事件，新标题:', newEvent.title);
      noteManager.editorTitle.value = newEvent.title;
      noteManager.updateEditorFirstLineTitle(newEvent.title, editorRef.value);
    }
  }
}, { deep: true });

// 组件挂载后初始化
onMounted(() => {
  // 恢复侧边栏宽度
  restoreSidebarWidth();
  
  // 确保笔记ID正确初始化
  nextTick(() => {
    sidebarManager.initializeEditorMode(editorRef);
    
    // 如果URL中有笔记ID但noteManager中没有，尝试同步
    if (routeManager.route.query.note && !noteManager.currentNoteId.value) {
      const noteIdFromUrl = parseInt(routeManager.route.query.note as string);
      if (!isNaN(noteIdFromUrl)) {
        console.log('组件挂载时从URL同步笔记ID:', noteIdFromUrl);
        noteManager.currentNoteId.value = noteIdFromUrl;
        localStorage.setItem('lastNoteId', noteIdFromUrl.toString());
      }
    }
  });
});
</script>

<template>
  <div class="home-container">
    <MermaidRenderer>
      <div class="notebook-layout">
        <!-- 主内容区 -->
        <div class="main-content" :class="{ 'has-sidebar': sidebarManager.showSidebar.value }">
          <!-- 编辑器内容 -->
          <div class="editor-content-wrapper">
            <Editor 
              v-model="noteManager.editorContent.value"
              @update:model-value="noteManager.updateContent"
              @word-count="updateWordCount"
              @toggle-sidebar-mode="handleToggleSidebarMode"
              @sidebar-send="handleSidebarSend"
              @sidebar-insert="handleSidebarInsert"
              @sidebar-navigate-history="handleSidebarNavigateHistory"
              @conversation-history-loaded="handleConversationHistoryLoaded"
              @note-edit-preview="handleNoteEditPreview"
              ref="editorRef"
              :conversation-id="sessionManager.currentSessionId.value"
              :note-id="noteManager.currentNoteId.value"
            />
            
            <div class="editor-footer">
              <div class="word-count">{{ wordCount }} 个字</div>
              <div v-if="noteManager.saved.value" class="saved-status">已自动保存</div>
            </div>
          </div>
        </div>
        
        <!-- 侧边栏 -->
        <Transition name="sidebar">
          <div v-if="sidebarManager.showSidebar.value" class="sidebar-wrapper" key="sidebar" :style="{ width: sidebarWidth + 'px' }">
            <AgentSidebar
              :visible="sidebarManager.showSidebar.value"
              :agentResponse="sessionManager.sidebarAgentResponse.value" 
              :isAgentResponding="sessionManager.sidebarIsAgentResponding.value"
              :historyIndex="sessionManager.sidebarHistoryIndex.value"
              :historyLength="sessionManager.sidebarHistoryLength.value"
              :conversationHistory="sessionManager.sidebarConversationHistory.value"
              :conversationId="sessionManager.currentSessionId.value"
              @close="closeSidebar"
              @send="handleSidebarSend"
              @request-insert="handleSidebarInsert" 
              @navigate-history="handleSidebarNavigateHistory"
              @edit-message="handleSidebarEditMessage"
              @resize="handleSidebarResize"
              @note-edit-preview="handleNoteEditPreview"
              ref="agentSidebarRef"
            />
          </div>
        </Transition>
      </div>
    </MermaidRenderer>
  </div>
</template>

<style scoped>
.notebook-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  background-color: #f9f9f9;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif;
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: white;
  position: relative;
  transition: all 0.3s ease;
  margin-left: 0;
  height: 100vh;
}

/* 编辑器内容区样式 */
.editor-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 32px 0;
  width: 90%;
  margin: 0 auto;
  position: relative;
  max-height: 100vh;
}

/* 底部状态栏样式 */
.editor-footer {
  padding: 12px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #888;
  font-size: 13px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  margin-top: auto;
  background-color: white;
  flex-shrink: 0;
  position: relative;
  z-index: 90;
}

.word-count {
  margin-right: auto;
}

.saved-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.saved-status::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #4caf50;
  display: inline-block;
}

/* 侧边栏样式 */
.sidebar-wrapper {
  flex-shrink: 0;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: transparent; /* 确保包装器背景透明 */
}

/* 侧边栏滚动条美化 */
.sidebar-wrapper::-webkit-scrollbar {
  width: 6px;
}

.sidebar-wrapper::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}

.sidebar-wrapper::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  transition: background 0.2s ease;
}

.sidebar-wrapper::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* Firefox 侧边栏滚动条样式 */
.sidebar-wrapper {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

/* 侧边栏动画 - 优化版本 */
.sidebar-enter-active {
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.sidebar-leave-active {
  transition: transform 0.25s cubic-bezier(0.55, 0.06, 0.68, 0.19);
}

.sidebar-enter-from {
  transform: translateX(100%);
}

.sidebar-leave-to {
  transform: translateX(100%);
}

/* 确保侧边栏包装器始终透明 */
.sidebar-wrapper {
  background: transparent !important;
}

/* 确保侧边栏内容立即可见 */
.sidebar-enter-active .agent-sidebar,
.sidebar-leave-active .agent-sidebar {
  background: #ffffff;
  opacity: 1;
  visibility: visible;
}

@media (max-width: 768px) {
  .editor-content-wrapper {
    padding-left: 20px;
    padding-right: 20px;
  }
}
</style> 