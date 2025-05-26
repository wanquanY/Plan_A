import { ref } from 'vue';

export function useSidebarManager() {
  // 侧边栏状态
  const showSidebar = ref(false);

  // 初始化编辑器交互模式
  const initializeEditorMode = (editorRef: any) => {
    // 默认使用弹窗模式
    if (editorRef.value && editorRef.value.setInteractionMode) {
      editorRef.value.setInteractionMode('modal');
      console.log('编辑器初始化为弹窗模式');
    }
  };

  // 处理切换侧边栏模式
  const handleToggleSidebarMode = (data: any, editorRef: any, sidebarConversationHistory: any) => {
    console.log('接收到切换侧边栏模式事件:', data);
    
    // 如果是直接切换界面显示（按钮点击）
    if (data.showInterface) {
      // 设置编辑器的交互模式
      if (editorRef.value && editorRef.value.setInteractionMode) {
        editorRef.value.setInteractionMode(data.newMode);
      }
      
      if (data.newMode === 'sidebar') {
        // 切换到侧边栏模式 - 获取当前Editor中的数据并关闭弹窗
        let currentData = null;
        if (editorRef.value && editorRef.value.getCurrentAgentData) {
          currentData = editorRef.value.getCurrentAgentData();
          console.log('获取当前弹窗数据:', currentData);
        }
        
        // 关闭弹窗（通过设置Editor的状态）
        if (editorRef.value && editorRef.value.closeModal) {
          editorRef.value.closeModal();
        }
        
        // 显示侧边栏
        showSidebar.value = true;
        
        // 如果有当前的响应数据，显示在侧边栏中
        if (currentData && (currentData.agentResponse || data.agentResponse !== undefined)) {
          // 同步会话历史记录
          if (currentData.conversationHistory && currentData.conversationHistory.length > 0) {
            sidebarConversationHistory.value = [...currentData.conversationHistory];
            console.log('同步会话历史记录到侧边栏，条数:', sidebarConversationHistory.value.length);
          }
          
          return {
            agentResponse: currentData.agentResponse || data.agentResponse || '',
            isAgentResponding: currentData.isAgentResponding || data.isAgentResponding || false,
            historyIndex: currentData.historyIndex !== undefined ? currentData.historyIndex : (data.historyIndex || -1),
            historyLength: currentData.historyLength || data.historyLength || 0
          };
        } else if (data.agentResponse !== undefined) {
          return {
            agentResponse: data.agentResponse,
            isAgentResponding: data.isAgentResponding,
            historyIndex: data.historyIndex,
            historyLength: data.historyLength
          };
        }
        
        console.log('切换到侧边栏模式并显示侧边栏');
      } else {
        // 切换到弹窗模式 - 隐藏侧边栏
        showSidebar.value = false;
        
        // 保存当前侧边栏的内容，用于在弹窗中显示
        const hasExistingContent = data.agentResponse && data.agentResponse.trim() !== '';
        const savedResponse = data.agentResponse || '';
        const savedIsResponding = data.isAgentResponding || false;
        const savedHistoryIndex = data.historyIndex || -1;
        const savedHistoryLength = data.historyLength || 0;
        const savedHistory = [...sidebarConversationHistory.value];
        
        // 等待侧边栏隐藏动画完成后显示弹窗
        setTimeout(() => {
          if (editorRef.value) {
            if (hasExistingContent || savedHistory.length > 0) {
              // 如果有现有内容或历史记录，在弹窗中显示
              if (editorRef.value.showModalWithContent) {
                editorRef.value.showModalWithContent({
                  response: savedResponse,
                  isResponding: savedIsResponding,
                  historyIndex: savedHistoryIndex,
                  historyLength: savedHistoryLength,
                  conversationHistory: savedHistory
                });
              }
            }
            // 移除自动显示演示弹窗的逻辑，让用户主动触发
          }
        }, 350); // 等待侧边栏动画完成
        
        console.log('切换到弹窗模式并隐藏侧边栏');
      }
      
      return null;
    }
    
    // 如果是纯粹的模式切换（不包含showSidebar和showInterface标记）
    if (!data.showSidebar && !data.showInterface) {
      // 设置编辑器的交互模式
      if (editorRef.value && editorRef.value.setInteractionMode) {
        editorRef.value.setInteractionMode(data.newMode);
      }
      
      console.log(`交互模式已切换为: ${data.newMode}`);
      
      // 如果切换到弹窗模式，关闭侧边栏
      if (data.newMode === 'modal') {
        showSidebar.value = false;
      }
      
      return null;
    }
    
    // 如果包含showSidebar标记，表示要显示侧边栏（用户触发了@交互）
    if (data.showSidebar) {
      showSidebar.value = true;
      
      // 确保编辑器模式为侧边栏模式
      if (editorRef.value && editorRef.value.setInteractionMode) {
        editorRef.value.setInteractionMode('sidebar');
      }
      
      // 如果有当前的响应数据，显示在侧边栏中
      if (data.agentResponse !== undefined) {
        return {
          agentResponse: data.agentResponse,
          isAgentResponding: data.isAgentResponding,
          historyIndex: data.historyIndex,
          historyLength: data.historyLength
        };
      }
      
      console.log('侧边栏模式：显示侧边栏');
    }
    
    return null;
  };

  // 处理侧边栏插入文本
  const handleSidebarInsert = (text: string, editorRef: any, editorContent: any) => {
    console.log('接收到侧边栏插入文本事件:', text);
    
    // 调用Editor组件的精确插入方法，而不是简单追加到末尾
    if (text && text.trim() && editorRef.value) {
      try {
        // 直接调用Editor组件暴露的handleInsertResponse方法
        // 这样可以确保内容插入到正确的光标位置
        if (typeof editorRef.value.handleInsertResponse === 'function') {
          editorRef.value.handleInsertResponse(text);
          console.log('通过Editor组件的方法插入文本到光标位置');
        } else {
          // 备用方案：如果Editor组件没有暴露该方法，直接操作内容
          console.warn('Editor组件未暴露handleInsertResponse方法，使用备用方案');
          
          // 将文本转换为HTML段落格式
          const paragraphs = text.split('\n\n').filter(p => p.trim());
          const htmlContent = paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
          
          // 如果当前内容只是一个空段落，替换它
          if (editorContent.value === '<p></p>' || editorContent.value === '<p>开始写作...</p>' || editorContent.value === '<p>请输入内容...</p>') {
            editorContent.value = htmlContent;
          } else {
            // 否则在末尾添加
            editorContent.value += htmlContent;
          }
          
          console.log('使用备用方案插入文本到编辑器末尾');
        }
      } catch (error) {
        console.error('插入文本时出错:', error);
        
        // 错误情况下的备用方案
        const paragraphs = text.split('\n\n').filter(p => p.trim());
        const htmlContent = paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
        
        if (editorContent.value === '<p></p>' || editorContent.value === '<p>开始写作...</p>' || editorContent.value === '<p>请输入内容...</p>') {
          editorContent.value = htmlContent;
        } else {
          editorContent.value += htmlContent;
        }
        
        console.log('错误情况下使用备用方案插入文本');
      }
    }
  };

  // 关闭侧边栏
  const closeSidebar = (editorRef: any) => {
    console.log('关闭侧边栏');
    showSidebar.value = false;
    
    // 设置编辑器为弹窗模式
    if (editorRef.value && editorRef.value.setInteractionMode) {
      editorRef.value.setInteractionMode('modal');
    }
    
    return {
      agentResponse: '',
      isAgentResponding: false,
      historyIndex: -1,
      historyLength: 0
    };
  };

  return {
    // 状态
    showSidebar,
    
    // 方法
    initializeEditorMode,
    handleToggleSidebarMode,
    handleSidebarInsert,
    closeSidebar
  };
} 