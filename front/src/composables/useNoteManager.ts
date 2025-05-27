import { ref, computed, inject } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import noteService from '../services/note';
import { debounce } from 'lodash';

export function useNoteManager() {
  const router = useRouter();
  const route = useRoute();
  
  // 从全局布局获取fetchNotes函数
  const fetchNotes = inject('fetchNotes') as any;
  
  // 笔记相关状态
  const currentNoteId = ref<number | null>(null);
  const editorTitle = ref('新笔记');
  const editorContent = ref('<p>请输入内容...</p>');
  const isAutoSaveEnabled = ref(true);
  const lastSavedContent = ref('');
  const firstUserInputDetected = ref(false);
  const saved = ref(true);

  // 自动保存的防抖函数
  const debouncedSave = debounce(async (content: string) => {
    if (!isAutoSaveEnabled.value || !currentNoteId.value) return;
    
    try {
      // 只有当内容变化时才保存
      if (content !== lastSavedContent.value) {
        // 检测是否有标题变化（从第一行H1标签提取）
        let title = editorTitle.value;
        
        // 从内容中提取第一行H1标签作为标题
        const h1Match = content.match(/<h1[^>]*>(.*?)<\/h1>/i);
        if (h1Match) {
          const h1Content = h1Match[1].replace(/<[^>]*>/g, '').trim(); // 移除HTML标签
          
          // 如果H1内容不是占位符文本，则使用它作为标题
          if (h1Content && h1Content !== '请输入标题' && h1Content.length > 0) {
            title = h1Content.substring(0, 50); // 限制标题长度
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
    } catch (error: any) {
      console.error('自动保存失败:', error);
      saved.value = false;
    }
  }, 2000);

  // 获取笔记详情
  const fetchNoteDetail = async (noteId: number) => {
    try {
      console.log(`开始获取笔记详情，ID: ${noteId}`);
      
      // 立即设置笔记ID，确保在异步操作期间也能获取到
      currentNoteId.value = noteId;
      
      // 同时保存到localStorage作为备份
      localStorage.setItem('lastNoteId', noteId.toString());
      
      // 加载笔记内容
      const noteRes = await noteService.getNoteDetail(noteId);
      console.log('笔记详情获取成功:', noteRes);
      
      // 安全地访问数据，确保即使数据格式不符合预期也不会崩溃
      const note = noteRes || {};
      
      // 判断是否是新创建的笔记
      const isNewNote = !note.content || note.content === '' || note.title === '';
      
      // 设置编辑器内容和标题
      if (isNewNote) {
        editorContent.value = '<h1 class="title-placeholder" data-placeholder="请输入标题"></h1><p></p>';
        firstUserInputDetected.value = false; // 新笔记需要检测第一次输入
      } else {
        editorContent.value = note.content || '<p></p>';
        firstUserInputDetected.value = true; // 已有内容的笔记不需要检测第一次输入
      }
      editorTitle.value = note.title || '无标题笔记';
      
      // 保存最近打开的笔记ID到localStorage
      localStorage.setItem('lastNoteId', noteId.toString());
      
      saved.value = true;
      
      return { note, hasSessionHistory: !!note.session_id, needsComplexRendering: !isNewNote };
    } catch (error: any) {
      console.error('获取笔记详情失败:', error);
      
      // 错误处理
      const isAxiosError = (err: any) => err && err.isAxiosError;
      if (isAxiosError(error) && error.response?.status === 404) {
        // 处理笔记不存在的情况
        message.error('笔记不存在');
        router.push('/');
      } else {
        message.error('获取笔记详情失败');
      }
      throw error;
    }
  };

  // 通过会话ID查找关联的笔记
  const fetchNoteBySessionId = async (sessionId: number) => {
    try {
      const noteData = await noteService.getNoteBySessionId(sessionId);
      if (noteData) {
        currentNoteId.value = noteData.id;
        console.log(`从会话ID查找到并设置笔记ID: ${noteData.id}`);
        firstUserInputDetected.value = true; // 已存在的笔记不需要检测第一行
        return noteData;
      }
    } catch (error: any) {
      console.error('根据会话ID查找笔记失败:', error);
      throw error;
    }
  };

  // 更新编辑器内容
  const updateContent = (content: string) => {
    editorContent.value = content;
    saved.value = false; // 内容变化时，标记为未保存
    
    // 调用防抖保存函数
    debouncedSave(content);
  };

  // 创建新笔记
  const createNewNote = () => {
    editorContent.value = '<h1 class="title-placeholder" data-placeholder="请输入标题"></h1><p></p>';
    editorTitle.value = '新笔记';
    currentNoteId.value = null;
    firstUserInputDetected.value = false;
    saved.value = true;
  };

  // 获取当前笔记ID的可靠方法
  const getCurrentNoteId = () => {
    // 优先使用内存中的值
    if (currentNoteId.value) {
      return currentNoteId.value;
    }
    
    // 如果内存中没有，尝试从localStorage获取
    const lastNoteId = localStorage.getItem('lastNoteId');
    if (lastNoteId) {
      const noteId = parseInt(lastNoteId);
      if (!isNaN(noteId)) {
        console.log('从localStorage恢复笔记ID:', noteId);
        currentNoteId.value = noteId;
        return noteId;
      }
    }
    
    return null;
  };

  // 更新编辑器第一行标题的函数
  const updateEditorFirstLineTitle = (newTitle: string, editorRef: any) => {
    if (!editorRef || !editorRef.editorRef) return;
    
    const editorElement = editorRef.editorRef;
    const firstH1 = editorElement.querySelector('h1');
    
    if (firstH1) {
      // 如果第一行是标题占位符，移除占位符类并设置新标题
      if (firstH1.classList.contains('title-placeholder')) {
        firstH1.classList.remove('title-placeholder');
        firstH1.removeAttribute('data-placeholder');
      }
      
      // 设置新的标题内容
      firstH1.textContent = newTitle;
      
      // 触发内容更新
      const newContent = editorElement.innerHTML;
      editorContent.value = newContent;
      
      console.log('已更新编辑器第一行标题为:', newTitle);
    } else {
      // 如果没有H1标签，在编辑器开头插入一个
      const newH1 = document.createElement('h1');
      newH1.textContent = newTitle;
      
      // 插入到编辑器开头
      if (editorElement.firstChild) {
        editorElement.insertBefore(newH1, editorElement.firstChild);
      } else {
        editorElement.appendChild(newH1);
      }
      
      // 触发内容更新
      const newContent = editorElement.innerHTML;
      editorContent.value = newContent;
      
      console.log('已在编辑器开头插入新标题:', newTitle);
    }
  };

  return {
    // 状态
    currentNoteId,
    editorTitle,
    editorContent,
    isAutoSaveEnabled,
    lastSavedContent,
    firstUserInputDetected,
    saved,
    
    // 方法
    fetchNoteDetail,
    fetchNoteBySessionId,
    updateContent,
    createNewNote,
    updateEditorFirstLineTitle,
    debouncedSave,
    getCurrentNoteId
  };
} 