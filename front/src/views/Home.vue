<script setup lang="ts">
import { useRouter } from 'vue-router';
import { ref, onMounted, reactive, nextTick, h, getCurrentInstance } from 'vue';
import { createApp } from 'vue';
import { message } from 'ant-design-vue';
import authService from '../services/auth';
import chatService from '../services/chat';
import Editor from '../components/Editor.vue';
import Sidebar from '../components/Sidebar.vue';
import mermaid from 'mermaid';
import MermaidRenderer from '@/components/MermaidRenderer.vue';
import MarkMap from '@/components/MarkMap.vue';
import { isMindMapContent as isMindMapContentFromService, 
         formatMessageContent as formatMessageContentFromService, 
         formatMessagesToHtml as formatMessagesToHtmlFromService } from '../services/markdownService';
import { renderCodeBlocks } from '../services/renderService';

// 初始化mermaid配置
mermaid.initialize({
  startOnLoad: false, // 不自动渲染，我们将在需要的地方手动渲染
  theme: 'default',
  securityLevel: 'loose', // 允许点击事件
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
  fontSize: 14
});

// 使用从markdownService导入的函数
const isMindMapContent = (content) => isMindMapContentFromService(content);

const router = useRouter();
const username = ref('用户');
const editorContent = ref('<p>哈哈哈哈，你可以做什么？</p>');
const editorTitle = ref('AI对人们生活的影响');
const wordCount = ref(0);
const saved = ref(true);
const sessions = ref([]);
const activeTab = ref('notes'); // 'notes' 或 'sessions'
const currentSessionId = ref(null);
const sidebarCollapsed = ref(false);
const editorRef = ref(null);

// 从token中解析用户名（简化示例）
onMounted(() => {
  const token = localStorage.getItem('access_token') || '';
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.sub) {
        username.value = payload.sub;
      }
    } catch (e) {
      console.error('解析token失败', e);
    }
  }
  
  // 获取会话列表
  fetchSessions();
  
  // 添加复制代码功能
  document.addEventListener('click', handleCodeCopyClick);
});

// 获取会话列表
const fetchSessions = async () => {
  try {
    console.log('开始请求会话列表...');
    const sessionsData = await chatService.getSessions();
    console.log('会话列表请求完成，结果:', sessionsData ? '成功' : '失败', sessionsData ? `获取到${sessionsData.length}条会话记录` : '');
    if (sessionsData) {
      sessions.value = sessionsData;
      console.log('会话列表更新成功，当前会话数量:', sessions.value.length);
    }
  } catch (error) {
    console.error('获取会话列表失败:', error);
  }
};

// 获取会话详情
const fetchSessionDetail = async (sessionId) => {
  try {
    if (!sessionId) return;
    
    const sessionData = await chatService.getSessionDetail(parseInt(sessionId));
    
    if (sessionData) {
      currentSessionId.value = parseInt(sessionId);
      
      if (sessionData.messages && sessionData.messages.length > 0) {
        // 将会话消息转换为HTML格式
        console.log(`格式化${sessionData.messages.length}条消息`);
        
        // 预处理消息内容，移除不必要的空行
        const cleanedMessages = sessionData.messages.map(msg => {
          // 创建一个浅拷贝，以免修改原始数据
          const cleanedMsg = {...msg};
          
          // 移除前后空白
          cleanedMsg.content = cleanedMsg.content.trim();
          
          // 移除多余的换行
          cleanedMsg.content = cleanedMsg.content.replace(/\n{3,}/g, '\n\n');
          
          return cleanedMsg;
        });
        
        const messagesHtml = formatMessagesToHtmlFromService(cleanedMessages, sessionData.title);
        editorContent.value = messagesHtml;
        editorTitle.value = sessionData.title || '未命名会话';
        
        // 在DOM更新后处理代码块和图表
        nextTick(() => {
          // 处理代码块和图表
          setTimeout(() => {
            const editorContainer = document.querySelector('.editor-content');
            if (!editorContainer) return;
            
            // 导入渲染服务
            import('../services/renderService').then(({ renderCodeBlocks, renderMermaidDynamically, renderMarkMaps }) => {
              // 处理普通代码块，但保留mermaid代码块和思维导图代码块
              renderCodeBlocks(false).then(() => {
                // 处理mermaid图表
                console.log('处理历史会话中的mermaid图表');
                
                // 寻找所有mermaid代码块并处理
                const mermaidCodeBlocks = document.querySelectorAll('pre > code.language-mermaid');
                console.log(`历史会话中找到${mermaidCodeBlocks.length}个Mermaid代码块`);
                
                if (mermaidCodeBlocks.length > 0) {
                  // 处理所有的mermaid代码块
                  mermaidCodeBlocks.forEach((codeBlock) => {
                    const code = codeBlock.textContent || '';
                    const preElement = codeBlock.closest('pre');
                    if (!preElement || preElement.querySelector('.mermaid-container')) return;
                    
                    // 创建一个新的mermaid渲染容器
                    const mermaidContainer = document.createElement('div');
                    mermaidContainer.className = 'mermaid-container';
                    
                    // 创建mermaid元素
                    const mermaidEl = document.createElement('div');
                    const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
                    mermaidEl.id = mermaidId;
                    mermaidEl.className = 'mermaid';
                    mermaidEl.textContent = code;
                    mermaidEl.setAttribute('data-original-content', code);
                    
                    // 添加复制按钮
                    const copyButton = document.createElement('button');
                    copyButton.className = 'copy-button';
                    copyButton.textContent = '复制';
                    copyButton.onclick = () => {
                      navigator.clipboard.writeText(code);
                      copyButton.textContent = '已复制';
                      setTimeout(() => {
                        copyButton.textContent = '复制';
                      }, 2000);
                    };
                    
                    // 组装DOM
                    mermaidContainer.appendChild(mermaidEl);
                    mermaidContainer.appendChild(copyButton);
                    
                    // 替换原始pre元素
                    preElement.replaceWith(mermaidContainer);
                  });
                }
                
                // 延迟渲染所有图表，确保DOM已更新
                setTimeout(() => {
                  console.log('开始渲染历史会话中的图表');
                  
                  // 渲染mermaid图表
                  renderMermaidDynamically();
                  
                  // 渲染思维导图
                  renderMarkMaps();
                  
                  console.log('已处理会话历史记录中的所有图表和思维导图');
                }, 300);
              });
            });
          }, 800);
        });
      }
    } else {
      throw new Error('获取会话详情失败');
    }
  } catch (error) {
    console.error('获取会话详情失败:', error);
    alert('获取会话详情失败，请稍后重试');
  }
};

// 将消息列表转换为HTML显示格式
const formatMessagesToHtml = (messages, title) => {
  if (!messages || messages.length === 0) return '<p>没有会话内容</p>';
  
  // 使用markdownService中的formatMessagesToHtml函数
  return formatMessagesToHtmlFromService(messages, title);
};

// 格式化消息时间
const formatMessageTime = (dateString) => {
  const date = new Date(dateString);
  return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
};

// 格式化消息内容，处理Markdown和代码块（替换原有函数）
const formatMessageContent = (content) => {
  // 使用markdownService中的formatMessageContent函数
  return formatMessageContentFromService(content);
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000); // 差距的秒数
  
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}天前`;
  
  // 超过一周返回具体日期
  return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
};

// 截取会话消息
const truncateMessage = (message, length = 30) => {
  if (!message) return '';
  if (message.length <= length) return message;
  return message.substring(0, length) + '...';
};

const handleLogout = () => {
  authService.logout();
  router.push('/login');
};

// 更新编辑器内容
const updateContent = (content: string) => {
  editorContent.value = content;
  saved.value = true; // 自动保存
};

// 更新字数
const updateWordCount = (count: number) => {
  wordCount.value = count;
};

// 切换标签
const handleTabSwitch = (tab) => {
  // 如果切换到测试页面，跳转到测试路由
  if (tab === 'test') {
    router.push('/test');
    return;
  }
  
  // 处理其他标签切换
  activeTab.value = tab;
};

// 点击会话项
const handleSessionClick = (sessionId) => {
  fetchSessionDetail(sessionId);
};

// 切换侧边栏折叠状态
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
};

// 新建笔记或会话
const handleNewNote = () => {
  if (activeTab.value === 'notes') {
    // 实现新建笔记逻辑
    // 清空编辑器，重置标题等
    editorContent.value = '<p></p>';
    editorTitle.value = '未命名笔记';
    currentSessionId.value = null;
  } else {
    // 实现新建会话逻辑 - 只清空编辑器，不直接创建会话
    editorContent.value = '<p></p>';
    editorTitle.value = '新会话';
    currentSessionId.value = null; // 清空当前会话ID
  }
};

// 创建新会话
const createNewSession = async () => {
  try {
    // 调用创建会话API
    const response = await chatService.createSession('新会话');
    if (response && response.id) {
      // 创建成功，刷新会话列表并切换到新会话
      await fetchSessions();
      currentSessionId.value = response.id;
      editorContent.value = '<p></p>';
      editorTitle.value = response.title || '新会话';
      message.success('新会话创建成功');
    } else {
      message.error('创建会话失败');
    }
  } catch (error) {
    console.error('创建会话失败:', error);
    message.error('创建会话失败');
  }
};

// 处理导航到其他页面
const handleNavigation = (path) => {
  router.push(path);
};

// 处理代码复制点击事件
const handleCodeCopyClick = (event) => {
  const target = event.target;
  // 检查是否点击了复制按钮或其内部元素
  const copyButton = target.closest('.code-copy-button');
  if (copyButton) {
    // 找到代码块
    const codeBlock = copyButton.closest('.code-block-wrapper')?.querySelector('code');
    if (codeBlock) {
      // 获取代码内容并复制到剪贴板
      const codeText = codeBlock.textContent || '';
      navigator.clipboard.writeText(codeText).then(() => {
        // 显示复制成功的动画或效果
        const originalTitle = copyButton.getAttribute('title');
        copyButton.setAttribute('title', '已复制!');
        copyButton.classList.add('copied');
        
        // 2秒后恢复原始状态
        setTimeout(() => {
          copyButton.setAttribute('title', originalTitle);
          copyButton.classList.remove('copied');
        }, 2000);
      }).catch(err => {
        console.error('复制失败:', err);
      });
    }
  }
};

// 添加渲染mermaid图表的功能
const renderMermaidDiagrams = () => {
  // 这个函数已经移动到renderService.ts中，不再需要
  import('../services/renderService').then(({ renderMermaidDiagrams }) => {
    renderMermaidDiagrams();
  });
};

// 确保在历史记录中加载后处理代码块
const ensureCodeBlocksHaveLanguage = () => {
  // 这个函数已经移动到renderService.ts中，不再需要
  import('../services/renderService').then(({ ensureCodeBlocksHaveLanguage }) => {
    ensureCodeBlocksHaveLanguage();
  });
};

// 在全局对象上添加刷新会话列表的方法，允许其他组件和服务调用
if (typeof window !== 'undefined') {
  window.refreshSessions = async () => {
    try {
      console.log('全局刷新会话列表方法被调用');
      const sessionsData = await chatService.getSessions();
      if (sessionsData) {
        // 使用原始导入的ref变量来更新
        sessions.value = sessionsData;
        console.log('会话列表已全局刷新，当前数量:', sessions.value.length);
      }
    } catch (error) {
      console.error('全局刷新会话列表失败:', error);
    }
  };
}
</script>

<template>
  <div class="home-container">
    <MermaidRenderer>
      <div class="notebook-layout">
        <!-- 使用侧边栏组件 -->
        <Sidebar 
          :username="username"
          :editor-title="editorTitle"
          :sessions="sessions"
          :active-tab="activeTab"
          :current-session-id="currentSessionId"
          :collapsed="sidebarCollapsed"
          @logout="handleLogout"
          @switch-tab="handleTabSwitch"
          @session-click="handleSessionClick"
          @toggle-sidebar="toggleSidebar"
          @new-note="handleNewNote"
          @nav-to="handleNavigation"
        />
        
        <!-- 主内容区 -->
        <div class="main-content">
          <!-- 编辑器内容 -->
          <div class="editor-content-wrapper">
            <Editor 
              v-model="editorContent"
              @update:model-value="updateContent"
              @word-count="updateWordCount"
              ref="editorRef"
              :conversation-id="currentSessionId"
            />
            
            <div class="editor-footer">
              <div class="word-count">{{ wordCount }} 个字</div>
              <div v-if="saved" class="saved-status">已自动保存</div>
            </div>
          </div>
        </div>
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
  height: 100%;
  overflow: hidden;
  background-color: white;
  position: relative;
  transition: margin-left 0.3s ease;
  margin-left: 0;
}

/* 编辑器内容区样式 */
.editor-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 32px 0;
  width: 90%;  /* 将宽度减少为原来的90% */
  margin: 0 auto;  /* 居中显示 */
}

/* 编辑器滚动条样式 */
.editor-content :deep(.editor-content) {
  scrollbar-width: thin; /* Firefox */
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent; /* Firefox */
}

.editor-content :deep(.editor-content)::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.editor-content :deep(.editor-content)::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}

.editor-content :deep(.editor-content)::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
  border: none;
}

.editor-content :deep(.editor-content)::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}

.editor-content :deep(.editor-content)::-webkit-scrollbar-corner {
  background-color: transparent;
}

.editor-footer {
  padding: 12px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #888;
  font-size: 13px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  margin-top: 16px;
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

@media (max-width: 768px) {
  .editor-content-wrapper {
    padding-left: 20px;
    padding-right: 20px;
  }
}

.history-messages {
  display: flex;
  flex-direction: column;
  gap: 16px;  /* 消息之间使用固定间距 */
}

.history-user-message,
.history-agent-message {
  margin: 0;
}

.history-user-message {
  background-color: #f5f5f5;
  padding: 12px 16px;
  border-radius: 8px 8px 0 8px;
  align-self: flex-end;
  max-width: 85%;
}

.history-agent-message {
  background-color: #f8f9fa;
  padding: 12px 16px;
  border-left: 3px solid #1677ff;
  border-radius: 0 4px 4px 0;
  max-width: 85%;
}

/* 修复代码块样式 */
.history-agent-message pre,
.history-user-message pre {
  margin: 12px 0;
  white-space: pre-wrap;
}

/* 确保首个段落无上边距，末尾段落无下边距 */
.history-agent-message p:first-child,
.history-user-message p:first-child {
  margin-top: 0;
}

.history-agent-message p:last-child,
.history-user-message p:last-child {
  margin-bottom: 0;
}

/* 复制按钮SVG图标样式 */
.code-copy-button svg {
  width: 16px;
  height: 16px;
}

/* 添加语言标识 */
.code-block-wrapper pre::before {
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

/* mermaid图表容器样式 */
.mermaid-wrapper {
  margin: 0.6em 0;
  position: relative;
  background-color: #f6f8fa;
  border-radius: 3px;
  padding: 15px;
  overflow: auto;
}

.mermaid {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  text-align: center;
}

.mermaid-wrapper .code-copy-button {
  top: 5px;
  right: 5px;
  background-color: rgba(246, 248, 250, 0.8);
}

/* 思维导图样式 */
.markmap-component-wrapper {
  margin: 20px 0;
  padding: 10px;
  background-color: #fafafa;
  border: 1px solid #eaeaea;
  border-radius: 6px;
  min-height: 400px;
  position: relative;
}

.mark-map-component {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.markmap-svg {
  width: 100%;
  min-height: 380px;
}

/* 隐藏工具栏 */
.markmap-toolbar {
  display: none !important;
}

/* 隐藏冗余按钮 */
.markmap-copy-button, .copy-button {
  display: none !important;
}

/* 确保SVG元素居中显示 */
[id^="markmap-"] {
  margin: 0 auto;
  display: block;
}

/* CodeBlock组件样式 */
.code-block-component-wrapper {
  margin: 20px 0;
  position: relative;
  background-color: #f6f8fa;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #eaecef;
}

:deep(.code-block-wrapper) {
  position: relative;
  margin: 0.6em 0;
}

:deep(.code-block-wrapper pre) {
  background-color: #f6f8fa;
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

:deep(.code-block-wrapper code) {
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  background-color: transparent;
  padding: 0;
  margin: 0;
  border-radius: 0;
  white-space: pre;
  display: block;
  overflow-x: auto;
  color: #24292e;
  font-size: 0.95em;
}

:deep(.code-block-wrapper pre::before) {
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

:deep(.code-block-wrapper .code-copy-button) {
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

:deep(.code-block-wrapper:hover .code-copy-button) {
  opacity: 1;
}

:deep(.code-copy-button.copied) {
  background-color: #dcffe4;
  color: #28a745;
  opacity: 1;
}

/* 确保mermaid图表SVG居中显示 */
svg[id^="mermaid-"] {
  display: block !important;
  margin: 0 auto !important;
  max-width: 100% !important;
  width: fit-content !important;
}

/* 移除mermaid容器的强制居中样式 */
.mermaid-container, 
.mermaid-wrapper, 
.mermaid-block,
div[class*="mermaid"] {
  width: 100% !important;
  box-sizing: border-box !important;
}

.mermaid {
  max-width: 100%;
  margin: 0 auto !important;
}

/* 确保SVG元素本身也被正确居中 */
svg[id^="mermaid-"] > * {
  margin: 0 auto !important;
}
</style>

<style>
/* 全局样式 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif;
}

/* 允许编辑器内容区域使用默认样式 */
.editor-content {
  overflow-y: auto;
}

/* 用户消息样式 */
.user-message {
  font-weight: 500;
  border-left: 3px solid #2196f3;
  padding-left: 10px;
  margin: 0.7em 0;
  color: #333;
}

/* 会话记录样式优化 */
.agent-response-paragraph.markdown-content {
  margin-bottom: 10px !important;
}

.agent-response-paragraph.markdown-content p {
  margin: 0.3em 0 !important;
}

.editor-content p {
  margin: 0.5em 0;
  min-height: 1.2em;
}

.editor-content p:empty {
  display: none;
}

/* 消除消息之间的多余间距 */
.user-message + .agent-response-paragraph {
  margin-top: 0.5em !important;
}

.agent-response-paragraph + .user-message {
  margin-top: 1.2em !important;
}

/* 消除连续标签间的额外间距 */
.editor-content p + p,
.editor-content div + p,
.editor-content p + div {
  margin-top: 0.8em;
}

/* 代码块样式 */
.editor-content pre,
.markdown-content pre {
  background-color: #f6f8fa;
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

.editor-content code,
.markdown-content code {
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  background-color: rgba(27, 31, 35, 0.05);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 85%;
}

/* 代码块内部样式优化 */
.editor-content pre code,
.markdown-content pre code {
  background-color: transparent;
  padding: 0;
  margin: 0;
  border-radius: 0;
  white-space: pre;
  display: block;
  overflow-x: auto;
  color: #24292e;
  font-size: 0.95em;
}

/* 确保代码块内容紧凑 */
.editor-content pre code br,
.markdown-content pre code br {
  display: none;
}

/* 代码语法高亮 */
.language-python .kd,
.language-python .k,
.language-python .ow,
.language-javascript .keyword,
.language-javascript .storage,
.language-typescript .keyword,
.language-typescript .storage,
.language-java .keyword,
.language-c .keyword,
.language-cpp .keyword {
  color: #0000ff;
  font-weight: bold;
}

.language-python .s,
.language-python .s1,
.language-python .s2,
.language-javascript .string,
.language-typescript .string,
.language-java .string,
.language-c .string,
.language-cpp .string {
  color: #a31515;
}

.language-python .c,
.language-python .c1,
.language-python .cm,
.language-javascript .comment,
.language-typescript .comment,
.language-java .comment,
.language-c .comment,
.language-cpp .comment {
  color: #008000;
}

.language-python .mi,
.language-python .mf,
.language-javascript .number,
.language-typescript .number,
.language-java .number,
.language-c .number,
.language-cpp .number {
  color: #098658;
}

/* HTML语言特定样式 */
.language-html .tag {
  color: #800000;
}

.language-html .attr-name {
  color: #ff0000;
}

.language-html .attr-value {
  color: #0000ff;
}

/* CSS语言特定样式 */
.language-css .selector {
  color: #800000;
}

.language-css .property {
  color: #ff0000;
}

.language-css .value {
  color: #0000ff;
}

/* 行号和行高亮 */
.editor-content pre code,
.markdown-content pre code {
  counter-reset: line;
  line-height: 1.5em;
}

/* 代码块滚动条 */
.editor-content pre,
.markdown-content pre {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.editor-content pre::-webkit-scrollbar,
.markdown-content pre::-webkit-scrollbar {
  height: 6px;
}

.editor-content pre::-webkit-scrollbar-track,
.markdown-content pre::-webkit-scrollbar-track {
  background: transparent;
}

.editor-content pre::-webkit-scrollbar-thumb,
.markdown-content pre::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

/* 限制代码块之间的距离 */
.editor-content p + .code-block-wrapper,
.markdown-content p + .code-block-wrapper {
  margin-top: 0.6em !important;
}

.code-block-wrapper + p,
.code-block-wrapper + div {
  margin-top: 0.6em !important;
}

/* 代码块容器 */
.code-block-wrapper {
  position: relative;
  margin: 0.6em 0;
}

/* 确保HTML和XML类型的代码块也能正确显示 */
.code-block-wrapper pre .code-copy-button {
  z-index: 10;
  top: 0;
  right: 0;
  border-top-right-radius: 5px; 
  border-top: none;
  border-right: none;
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
</style> 