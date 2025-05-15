<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router';
import { ref, onMounted, reactive, nextTick, h, getCurrentInstance, computed, onBeforeMount, inject, watch } from 'vue';
import { createApp } from 'vue';
import { message } from 'ant-design-vue';
import authService from '../services/auth';
import chatService from '../services/chat';
import noteService from '../services/note';
import Editor from '../components/Editor.vue';
import mermaid from 'mermaid';
import MermaidRenderer from '@/components/MermaidRenderer.vue';
import MarkMap from '@/components/MarkMap.vue';
import { isMindMapContent as isMindMapContentFromService, 
         formatMessageContent as formatMessageContentFromService, 
         formatMessagesToHtml as formatMessagesToHtmlFromService } from '../services/markdownService';
import { renderCodeBlocks } from '../services/renderService';
import { debounce } from 'lodash';

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
const route = useRoute();
const editorContent = ref('<p>请输入内容...</p>');
const editorTitle = ref('新笔记');
const wordCount = ref(0);
const saved = ref(true);
const editorRef = ref(null);

// 从全局布局获取会话ID和会话列表
const currentSessionId = inject('currentSessionId');
const sessions = inject('sessions');
const fetchSessions = inject('fetchSessions');
const fetchNotes = inject('fetchNotes');

// 笔记相关数据
const currentNoteId = ref<number | null>(null);
const isAutoSaveEnabled = ref(true);
const lastSavedContent = ref('');
const firstUserInputDetected = ref(false);

// 自动保存的防抖函数
const debouncedSave = debounce(async (content: string) => {
  if (!isAutoSaveEnabled.value || !currentNoteId.value) return;
  
  try {
    // 只有当内容变化时才保存
    if (content !== lastSavedContent.value) {
      // 检测是否有标题变化（用户的第一句话）
      let title = editorTitle.value;
      
      // 如果检测到第一行输入，并且之前没有检测到用户输入
      if (!firstUserInputDetected.value) {
        // 从内容中提取第一行作为标题
        const firstLine = content.replace(/<(?:.|\n)*?>/gm, '')
                                 .trim()
                                 .split('\n')[0]
                                 .substring(0, 50);
        
        if (firstLine && firstLine.length > 0) {
          title = firstLine;
          editorTitle.value = title;
          firstUserInputDetected.value = true;
        }
      }
      
      console.log('自动保存笔记内容...');
      await noteService.autoSaveNote(currentNoteId.value, content, title);
      lastSavedContent.value = content;
      saved.value = true;
      
      // 保存成功后刷新笔记列表
      if (fetchNotes) {
        console.log('刷新侧边栏笔记列表...');
        fetchNotes();
      }
    }
  } catch (error) {
    console.error('自动保存失败:', error);
    saved.value = false;
  }
}, 2000);

// 监听路由参数变化
onBeforeMount(() => {
  // 首先检查URL中是否有笔记ID参数
  if (route.query.note) {
    // 无论是否有会话ID，只要有笔记ID就加载笔记内容
    const noteId = parseInt(route.query.note as string);
    if (!isNaN(noteId)) {
      console.log(`从URL参数设置笔记ID: ${noteId}`);
      currentNoteId.value = noteId;
      
      // 如果同时有会话ID，也设置会话ID，但优先加载笔记内容
      if (route.query.id) {
        const sessionId = parseInt(route.query.id as string);
        if (!isNaN(sessionId)) {
          currentSessionId.value = sessionId;
          console.log(`URL中同时有会话ID: ${sessionId}，但优先加载笔记内容`);
        }
      } else {
        currentSessionId.value = null;
      }
      
      // 加载笔记内容
      fetchNoteDetail(noteId);
    }
  }
  // 如果只有会话ID参数，没有笔记ID参数
  else if (route.query.id) {
    const sessionId = parseInt(route.query.id as string);
    if (!isNaN(sessionId)) {
      // 设置当前会话ID并获取详情
      currentSessionId.value = sessionId;
      fetchSessionDetail(sessionId);
      
      // 尝试查找关联的笔记ID，但不加载笔记内容
      fetchNoteBySessionId(sessionId);
    }
  } else if (route.query.new) {
    // 如果URL中有new参数，表示用户想创建一个新笔记
    editorContent.value = '<p></p>';
    editorTitle.value = '新笔记';
    currentSessionId.value = null;
    currentNoteId.value = null;
  } else {
    // 如果URL中没有任何参数，且用户已登录，检查是否有默认笔记
    if (authService.isAuthenticated()) {
      const defaultNoteId = authService.getDefaultNoteId();
      if (defaultNoteId) {
        console.log(`发现默认笔记ID: ${defaultNoteId}，自动加载`);
        currentNoteId.value = defaultNoteId;
        fetchNoteDetail(defaultNoteId);

        // 加载成功后清除默认笔记ID，这样只有首次登录会自动打开
        localStorage.removeItem('default_note_id');
      } else {
        // 如果没有默认笔记，加载用户的笔记列表
        console.log('没有默认笔记，加载笔记列表');
        fetchNotes(1, true);
      }
    } else {
      // 未登录状态，加载笔记列表
      fetchNotes(1, true);
    }
  }
});

// 监听会话ID变化
watch(() => route.query, (newQuery) => {
  // 首先检查URL中是否有笔记ID参数
  if (newQuery.note) {
    // 无论是否有会话ID，只要有笔记ID就加载笔记内容
    const noteId = parseInt(newQuery.note as string);
    if (!isNaN(noteId)) {
      console.log(`从URL参数变化设置笔记ID: ${noteId}`);
      currentNoteId.value = noteId;
      
      // 如果同时有会话ID，也设置会话ID，但优先加载笔记内容
      if (newQuery.id) {
        const sessionId = parseInt(newQuery.id as string);
        if (!isNaN(sessionId)) {
          currentSessionId.value = sessionId;
          console.log(`URL中同时有会话ID: ${sessionId}，但优先加载笔记内容`);
        }
      } else {
        currentSessionId.value = null;
      }
      
      // 加载笔记内容
      fetchNoteDetail(noteId);
    }
  }
  // 如果只有会话ID参数，没有笔记ID参数
  else if (newQuery.id) {
    const sessionId = parseInt(newQuery.id as string);
    if (!isNaN(sessionId)) {
      currentSessionId.value = sessionId;
      fetchSessionDetail(sessionId);
      
      // 尝试查找关联的笔记ID，但不加载笔记内容
      fetchNoteBySessionId(sessionId);
    }
  } else if (newQuery.new) {
    // 如果URL中有new参数，表示用户想创建一个新笔记
    editorContent.value = '<p></p>';
    editorTitle.value = '新笔记';
    currentSessionId.value = null;
    currentNoteId.value = null;
  }
}, { deep: true });

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
        editorTitle.value = sessionData.title || '未命名笔记';
        
        // 在DOM更新后处理代码块和图表，但避免在此时渲染思维导图
        nextTick(() => {
          // 首次加载时，先不渲染思维导图，等待DOM完全加载
          renderContentComponents(false);
          
          // 在页面完全加载后，再强制渲染思维导图
          setTimeout(() => {
            if (document.readyState === 'complete') {
              console.log('页面完全加载，强制渲染思维导图');
              renderContentComponents(true);
            } else {
              // 如果页面尚未完全加载，等待加载完成再渲染
              window.addEventListener('load', () => {
                console.log('页面加载完成，开始完整渲染');
                renderContentComponents(true);
              }, { once: true });
            }
          }, 1500);
        });
      }
    } else {
      throw new Error('获取会话详情失败');
    }
  } catch (error) {
    console.error('获取会话详情失败:', error);
    message.error('获取笔记详情失败，请稍后重试');
  }
};

// 获取笔记详情
const fetchNoteDetail = async (noteId: number) => {
  try {
    console.log(`开始获取笔记详情，ID: ${noteId}`);
    currentNoteId.value = noteId;
    
    // 检查笔记关联的会话
    if (route.query.sessionId) {
      currentSessionId.value = Number(route.query.sessionId);
    } else {
      // 如果URL中没有sessionId，则清空currentSessionId
      console.log('笔记未关联会话，清空currentSessionId');
      currentSessionId.value = null;
    }
    
    // 加载笔记内容
    const noteRes = await noteService.getNoteDetail(noteId);
    console.log('笔记详情获取成功:', noteRes);
    
    // 安全地访问数据，确保即使数据格式不符合预期也不会崩溃
    const note = noteRes?.data || noteRes || {};
    
    // 判断是否是新创建的笔记
    const isNewNote = !note.content || note.content === '';
    
    // 设置编辑器内容和标题
    editorContent.value = isNewNote ? '# ' : (note.content || '<p></p>');
    editorTitle.value = note.title || '无标题笔记';
    
    // 在DOM更新后立即渲染组件
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
          const content = note.content || '';
          if (content.includes('```markdown') || content.includes('# ')) {
            console.log('检测到可能包含思维导图的内容，再次尝试渲染');
            renderContentComponents(true);
          }
        }, 800);
      } catch (error) {
        console.error('思维导图渲染失败:', error);
      }
    });
    
    // 保存最近打开的笔记ID到localStorage
    localStorage.setItem('lastNoteId', noteId.toString());
    
    saved.value = true;
  } catch (error) {
    console.error('获取笔记详情失败:', error);
    
    // 尝试使用错误中附带的默认笔记数据
    if (error && (error as any).noteData) {
      console.log('使用错误中的默认笔记数据');
      const defaultNote = (error as any).noteData;
      editorContent.value = defaultNote.content || '<p>笔记加载失败，请刷新页面重试</p>';
      editorTitle.value = defaultNote.title || '无法加载笔记';
      saved.value = true;
      return;
    }
    
    // 错误处理，使用import导入axios而不是直接引用
    const isAxiosError = (err) => err && err.isAxiosError;
    if (isAxiosError(error) && error.response?.status === 404) {
      // 处理笔记不存在的情况
      message.error('笔记不存在');
      router.push('/');
    } else {
      message.error('获取笔记详情失败');
    }
  }
};

// 通过会话ID查找关联的笔记
const fetchNoteBySessionId = async (sessionId: number) => {
  try {
    const noteData = await noteService.getNoteBySessionId(sessionId);
    if (noteData) {
      currentNoteId.value = noteData.id;
      console.log(`从会话ID查找到并设置笔记ID: ${noteData.id}`);
      
      // 不再更新编辑器内容，否则会覆盖会话内容
      // editorContent.value = noteData.content || '<p></p>';
      // editorTitle.value = noteData.title || '未命名笔记';
      // lastSavedContent.value = noteData.content || '';
      firstUserInputDetected.value = true; // 已存在的笔记不需要检测第一行
      
      // 更新URL，添加note参数但不改变编辑器内容
      router.replace(`/?id=${sessionId}&note=${noteData.id}`);
    }
  } catch (error) {
    console.error('根据会话ID查找笔记失败:', error);
  }
};

// 更新编辑器内容
const updateContent = (content: string) => {
  editorContent.value = content;
  saved.value = false; // 内容变化时，标记为未保存
  
  // 调用防抖保存函数
  debouncedSave(content);
};

// 更新字数
const updateWordCount = (count: number) => {
  wordCount.value = count;
};

const handleLogout = () => {
  authService.logout();
  router.push('/login');
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

// 格式化消息内容，处理Markdown和代码块
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
  // 仅获取会话详情，不查找关联的笔记
  fetchSessionDetail(sessionId);
};

// 切换侧边栏折叠状态
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
};

// 新建笔记或会话
const handleNewNote = () => {
  // 总是使用会话逻辑
  // 实现新建会话逻辑 - 只清空编辑器，不直接创建会话
  editorContent.value = '<p></p>';
  editorTitle.value = '新笔记';
  currentSessionId.value = null; // 清空当前会话ID
};

// 创建新会话
const createNewSession = async () => {
  try {
    // 调用创建会话API
    const response = await chatService.createSession('新笔记');
    if (response && response.id) {
      // 创建成功，刷新会话列表并切换到新会话
      await fetchSessions();
      currentSessionId.value = response.id;
      editorContent.value = '<p></p>';
      editorTitle.value = response.title || '新笔记';
      message.success('新笔记创建成功');
    } else {
      message.error('创建笔记失败');
    }
  } catch (error) {
    console.error('创建笔记失败:', error);
    message.error('创建笔记失败');
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

// 处理加载更多
const handleLoadMore = () => {
  if (pagination.loading || !pagination.hasMore) return;
  
  const nextPage = pagination.current + 1;
  if (nextPage <= pagination.pages) {
    fetchSessions(nextPage, true);
  }
};

// DOM缓存对象，避免重复查询选择器
const domCache = {
  renderingInProgress: false,
  renderTimeout: null as number | null,
  // 跟踪已处理的元素，避免重复渲染
  processedElements: new Set<string>()
};

// 封装渲染方法，添加防抖和防重渲染逻辑
const renderContentComponents = (forceRender = true) => {
  // 如果已经有渲染进行中，清除之前的定时器
  if (domCache.renderTimeout) {
    clearTimeout(domCache.renderTimeout);
  }
  
  // 避免短时间内多次渲染
  if (domCache.renderingInProgress) {
    console.log('已有渲染任务进行中，跳过重复渲染');
    return;
  }
  
  // 设置渲染中状态
  domCache.renderingInProgress = true;
  
  // 在开始渲染前记录是否已加载完毕
  const isDocumentLoaded = document.readyState === 'complete';
  console.log(`开始准备渲染，document.readyState = ${document.readyState}, forceRender = ${forceRender}`);
  
  // 清空已处理元素的集合
  domCache.processedElements.clear();
  
  // 添加延时执行
  domCache.renderTimeout = setTimeout(async () => {
    try {
      const editorContainer = document.querySelector('.editor-content');
      if (!editorContainer) {
        console.log('未找到编辑器容器，跳过渲染');
        return;
      }
      
      console.log(`开始处理渲染，forceRender = ${forceRender}, isDocumentLoaded = ${isDocumentLoaded}`);
      
      // 导入渲染服务
      const { renderCodeBlocks, renderMermaidDynamically, renderMarkMaps, setupMermaidAutoRender, cleanupMarkmapElements } = await import('../services/renderService');
      
      // 在渲染前彻底清理思维导图元素
      cleanupMarkmapElements();
      
      // 创建唯一标识函数，用于跟踪已处理的元素
      const createElementId = (el: Element, content: string): string => {
        // 使用内容的哈希和元素位置作为唯一标识
        const contentHash = content.substring(0, 50); // 取内容前50个字符
        const parent = el.closest('.agent-response-paragraph');
        const siblings = Array.from(parent?.children || []);
        const index = siblings.indexOf(el as HTMLElement);
        return `${contentHash}_${index}`;
      };
      
      // 预处理：直接检测并标记所有可能包含思维导图内容的元素
      const potentialMarkdownElements = document.querySelectorAll('pre > code.language-markdown, pre > code.language-md, .markmap-content, p');
      potentialMarkdownElements.forEach(el => {
        const content = el.textContent || '';
        // 使用markdownService中的isMindMapContent函数检查
        if (isMindMapContent(content)) {
          // 创建元素的唯一标识
          const elementId = createElementId(el, content);
          
          // 如果已处理过该元素，跳过
          if (domCache.processedElements.has(elementId)) {
            console.log('跳过已处理过的思维导图元素');
            return;
          }
          
          // 标记为已处理
          domCache.processedElements.add(elementId);
          
          console.log('预处理：找到思维导图内容元素，添加标记');
          el.setAttribute('data-contains-markmap-content', 'true');
          el.classList.add('original-markmap-content');
          el.setAttribute('data-element-id', elementId); // 添加唯一标识
          
          // 标记父元素
          const parentPre = el.closest('pre');
          if (parentPre) {
            parentPre.classList.add('markmap-to-process');
            parentPre.setAttribute('data-element-id', elementId); // 添加唯一标识
            
            // 只有在强制渲染时才隐藏原始内容
            if (forceRender && isDocumentLoaded) {
              parentPre.style.display = 'none';
            }
          }
          
          // 找到最近的agent-response-paragraph元素
          const agentResponseParagraph = el.closest('.agent-response-paragraph');
          if (agentResponseParagraph) {
            agentResponseParagraph.setAttribute('data-contains-markmap', 'true');
          }
          
          // 只有在强制渲染时才隐藏原始内容
          if (forceRender && isDocumentLoaded && el instanceof HTMLElement) {
            el.style.display = 'none';
          }
        }
      });
      
      // 传递已处理元素集合到全局
      (window as any)['processedMarkMapElements'] = Array.from(domCache.processedElements);
      
      // 处理代码块 - 文档加载完成且有强制渲染标记时才处理思维导图
      if (forceRender && isDocumentLoaded) {
        console.log('执行完整渲染，包括思维导图');
        await renderCodeBlocks(true);
      } else {
        console.log('流式输出中，暂不渲染思维导图');
        // 仅处理普通代码块，不处理思维导图
        await renderCodeBlocks(false);
      }
      
      // 处理mermaid图表 - 可以在流式输出过程中处理
      console.log('处理mermaid图表');
      renderMermaidDynamically();
      
      // 只有在强制渲染且文档加载完成时才处理思维导图
      if (forceRender && isDocumentLoaded) {
        // 处理思维导图
        console.log('处理思维导图');
        
        // 立即调用渲染思维导图
        renderMarkMaps();
      } else {
        console.log('流式输出中，仅标记思维导图内容，暂不渲染');
        
        // 获取自动渲染控制器，但不触发渲染
        const autoRenderController = setupMermaidAutoRender();
        
        // 将控制器保存到全局，以便流式输出结束时触发渲染
        (window as any).autoRenderController = autoRenderController;
      }
      
      console.log('渲染处理完成');
    } catch (error) {
      console.error('渲染组件时出错:', error);
    } finally {
      // 重置渲染状态，允许下次渲染
      setTimeout(() => {
        domCache.renderingInProgress = false;
        domCache.renderTimeout = null;
      }, 500);
    }
  }, 800);
};
</script>

<template>
  <div class="home-container">
    <MermaidRenderer>
      <div class="notebook-layout">
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
              :note-id="currentNoteId"
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
  overflow-y: auto; /* 允许主内容区域滚动 */
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
  overflow: visible; /* 允许内容溢出 */
  padding: 16px 32px 0;
  width: 90%;  /* 将宽度减少为原来的90% */
  margin: 0 auto;  /* 居中显示 */
  position: relative;
}

/* 确保编辑器工具栏固定 */
:deep(.editor-container .editor-toolbar) {
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f9f9f9;
  border-radius: 8px 8px 0 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
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
  margin-top: auto; /* 使用auto margin将其推至容器底部 */
  position: sticky; /* 使底部状态栏固定 */
  bottom: 0; /* 固定在底部 */
  background-color: white; /* 确保背景色遮挡滚动内容 */
  z-index: 90; /* 确保在内容上方，但低于顶部工具栏 */
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

/* 确保在同一个agent-response-paragraph中，只有第一个思维导图显示控制按钮 */
.agent-response-paragraph .markmap-component-wrapper:not(:first-of-type) .fit-button,
.agent-response-paragraph .markmap-component-wrapper ~ .markmap-component-wrapper .fit-button {
  display: none !important;
}

/* 隐藏重复渲染的思维导图 */
.agent-response-paragraph[data-contains-markmap="true"] pre[data-markmap-processed="true"],
.agent-response-paragraph[data-markmap-rendered="true"] pre[data-markmap-processed="true"] {
  display: none !important;
}

/* 隐藏所有思维导图渲染后的原始markdown内容 */
.markmap-component-wrapper + pre,
.markmap-component-wrapper + p[data-markmap-processed],
.markmap-component-wrapper + p[data-markmap-completed], 
.markmap-component-wrapper + div,
.markmap-component-wrapper ~ pre[data-markmap-processed],
.markmap-component-wrapper ~ code.language-markdown,
.agent-response-paragraph[data-contains-markmap="true"] > div:not(.markmap-component-wrapper) > pre > code.language-markdown,
.agent-response-paragraph[data-contains-markmap="true"] > p,
.agent-response-paragraph[data-contains-markmap="true"] pre,
.agent-response-paragraph[data-markmap-rendered="true"] > div:not(.markmap-component-wrapper) > pre > code.language-markdown,
.agent-response-paragraph[data-markmap-rendered="true"] > pre > code.language-markdown,
.agent-response-paragraph[data-markmap-rendered="true"] > p[data-markmap-processed],
.agent-response-paragraph[data-markmap-rendered="true"] > p[data-markmap-completed],
div[data-markmap-processed="true"],
div[data-markmap-completed="true"],
[data-contains-markmap-content="true"],
.original-markmap-content,
pre.markmap-processed,
p.markmap-processed,
.markmap-component-wrapper ~ pre,
.markmap-component-wrapper ~ .markmap-content,
.markmap-content {
  display: none !important;
}

/* 隐藏包含data-markmap-content属性的元素 */
[data-markmap-content] {
  display: none !important;
}

/* 确保在agent-response-paragraph中显示第一个思维导图后，隐藏其余内容 */
.agent-response-paragraph[data-contains-markmap="true"] > *:not(.markmap-component-wrapper):not(h1):not(h2):not(h3):not(h4):not(h5):not(h6),
.agent-response-paragraph[data-markmap-rendered="true"] > *:not(.markmap-component-wrapper):not(h1):not(h2):not(h3):not(h4):not(h5):not(h6) {
  display: none !important;
}

/* 显示思维导图组件和标题 */
.agent-response-paragraph[data-contains-markmap="true"] > .markmap-component-wrapper,
.agent-response-paragraph[data-markmap-rendered="true"] > .markmap-component-wrapper {
  display: block !important;
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