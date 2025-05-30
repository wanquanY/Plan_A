import { ref } from 'vue';

export function usePreviewManager() {
  // 预览相关状态
  const pendingEditData = ref(null);
  const originalContentForPreview = ref('');
  const previewedContent = ref('');

  // 渲染markdown内容为HTML
  const renderContentAsHtml = async (content: string): Promise<string> => {
    try {
      // 动态导入agentResponseService
      const { processMarkdown } = await import('../services/agentResponseService');
      return processMarkdown(content);
    } catch (error) {
      console.error('渲染markdown内容失败:', error);
      // 如果渲染失败，至少处理换行
      return content.replace(/\n/g, '<br>');
    }
  };

  // 显示替换预览
  const showReplacePreview = async (editorElement: HTMLElement, previewData: any) => {
    // 将整个编辑器内容用删除线标记，并在下方显示新内容
    const currentContent = editorElement.innerHTML;
    
    // 渲染新内容的markdown
    const renderedContent = await renderContentAsHtml(previewData.content);
    
    editorElement.innerHTML = `
      <div class="preview-deleted-content">
        ${currentContent}
      </div>
      <div class="preview-added-content">
        ${renderedContent}
      </div>
    `;
    
    // 在内容插入后，渲染特殊组件（代码块、图表等）
    setTimeout(async () => {
      try {
        const { renderContentComponents } = await import('../services/renderService');
        renderContentComponents(true);
      } catch (error) {
        console.error('渲染特殊组件失败:', error);
      }
    }, 100);
  };

  // 显示追加预览
  const showAppendPreview = async (editorElement: HTMLElement, previewData: any) => {
    // 在编辑器末尾添加高亮的新内容
    const newContentDiv = document.createElement('div');
    newContentDiv.className = 'preview-added-content';
    
    // 渲染markdown内容
    const renderedContent = await renderContentAsHtml(previewData.content);
    newContentDiv.innerHTML = renderedContent;
    
    editorElement.appendChild(newContentDiv);
    
    // 触发重新布局以确保动画效果
    newContentDiv.offsetHeight;
    
    // 渲染特殊组件
    setTimeout(async () => {
      try {
        const { renderContentComponents } = await import('../services/renderService');
        renderContentComponents(true);
      } catch (error) {
        console.error('渲染特殊组件失败:', error);
      }
    }, 100);
  };

  // 显示前置预览
  const showPrependPreview = async (editorElement: HTMLElement, previewData: any) => {
    // 在编辑器开头添加高亮的新内容
    const newContentDiv = document.createElement('div');
    newContentDiv.className = 'preview-added-content';
    
    // 渲染markdown内容
    const renderedContent = await renderContentAsHtml(previewData.content);
    newContentDiv.innerHTML = renderedContent;
    
    // 插入到开头
    if (editorElement.firstChild) {
      editorElement.insertBefore(newContentDiv, editorElement.firstChild);
    } else {
      editorElement.appendChild(newContentDiv);
    }
    
    // 触发重新布局
    newContentDiv.offsetHeight;
    
    // 渲染特殊组件
    setTimeout(async () => {
      try {
        const { renderContentComponents } = await import('../services/renderService');
        renderContentComponents(true);
      } catch (error) {
        console.error('渲染特殊组件失败:', error);
      }
    }, 100);
  };

  // 显示插入预览
  const showInsertPreview = async (editorElement: HTMLElement, previewData: any) => {
    // 默认追加到末尾
    await showAppendPreview(editorElement, previewData);
  };

  // 清除现有的预览内容
  const clearExistingPreview = () => {
    // 清除预览内容标记
    const previewContents = document.querySelectorAll('.preview-added-content, .preview-deleted-content');
    previewContents.forEach(element => {
      if (element.parentNode) {
        // 对于内联元素，用文本内容替换
        if (element.classList.contains('inline')) {
          const textNode = document.createTextNode(element.textContent || '');
          element.parentNode.replaceChild(textNode, element);
        } else {
          element.parentNode.removeChild(element);
        }
      }
    });
  };

  // 直接在编辑器中插入高亮预览内容
  const insertPreviewContentInEditor = async (previewData: any, editorElement: HTMLElement | null, onAccept: Function, onReject: Function) => {
    console.log('[PreviewManager] 在编辑器中插入内联预览内容');
    
    if (!editorElement) {
      console.warn('[PreviewManager] 无法找到编辑器元素');
      return;
    }
    
    try {
      // 清除任何现有的预览内容
      clearExistingPreview();
      
      // 保存原始内容
      const originalContent = editorElement.innerHTML;
      
      // 根据编辑类型处理内容
      if (previewData.editType === 'replace') {
        // 替换模式：用高亮的新内容替换现有内容
        await showReplacePreview(editorElement, previewData);
      } else if (previewData.editType === 'append') {
        // 追加模式：在末尾添加高亮内容
        await showAppendPreview(editorElement, previewData);
      } else if (previewData.editType === 'prepend') {
        // 前置模式：在开头添加高亮内容
        await showPrependPreview(editorElement, previewData);
      } else {
        // 默认插入模式
        await showInsertPreview(editorElement, previewData);
      }
      
      // 等待DOM更新后，找到预览内容并添加按钮
      setTimeout(() => {
        const previewElement = editorElement.querySelector('.preview-added-content') as HTMLElement;
        if (previewElement) {
          // 确保预览元素有相对定位
          previewElement.style.position = 'relative';
          
          // 创建按钮容器
          const buttonContainer = document.createElement('div');
          buttonContainer.className = 'preview-floating-buttons';
          buttonContainer.setAttribute('data-preview-buttons', 'true');
          
          // 使用绝对定位相对于预览内容
          buttonContainer.style.cssText = `
            position: absolute;
            bottom: -35px;
            right: 0px;
            z-index: 1000;
            animation: slideInBottomRight 0.3s ease-out;
          `;
          
          // 创建按钮组
          const buttonGroup = document.createElement('div');
          buttonGroup.style.cssText = `
            display: flex;
            gap: 4px;
            background: white;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 2px;
            border: 1px solid #e1e4e8;
          `;
          
          // 创建接受按钮
          const acceptButton = document.createElement('button');
          acceptButton.innerHTML = '✓ 接受';
          acceptButton.style.cssText = `
            padding: 4px 8px;
            border: none;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            background-color: #2ea043;
            color: white;
            transition: all 0.2s ease;
          `;
          acceptButton.onclick = () => onAccept(previewData);
          
          // 创建拒绝按钮
          const rejectButton = document.createElement('button');
          rejectButton.innerHTML = '✗ 拒绝';
          rejectButton.style.cssText = `
            padding: 4px 8px;
            border: none;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            background-color: #f85149;
            color: white;
            transition: all 0.2s ease;
          `;
          rejectButton.onclick = () => onReject(originalContent);
          
          buttonGroup.appendChild(acceptButton);
          buttonGroup.appendChild(rejectButton);
          buttonContainer.appendChild(buttonGroup);
          
          // 将按钮添加到预览元素内部
          previewElement.appendChild(buttonContainer);
          
          console.log('[PreviewManager] 按钮已添加到预览内容的右下角');
          
          // 滚动到预览内容
          previewElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
          });
          
          // 添加短暂的脉冲效果
          previewElement.style.animation = 'none';
          setTimeout(() => {
            previewElement.style.animation = 'fadeInGlow 0.5s ease-in-out';
          }, 10);
        }
      }, 100);
      
      console.log('[PreviewManager] 内联预览已显示');
      
    } catch (error) {
      console.error('[PreviewManager] 显示内联预览失败:', error);
    }
  };

  // 测试预览功能的函数
  const testPreviewButtons = async () => {
    console.log('[PreviewManager] 测试预览按钮功能');
    
    const testData = {
      content: '这是测试内容',
      editType: 'append',
      noteId: 123
    };
    
    const testAccept = (data: any) => {
      console.log('[PreviewManager] 测试：用户接受了预览', data);
    };
    
    const testReject = (originalContent: string) => {
      console.log('[PreviewManager] 测试：用户拒绝了预览', originalContent);
    };
    
    // 直接调用添加按钮的函数
    await insertPreviewContentInEditor(testData, null, testAccept, testReject);
  };

  // 显示消息的辅助方法
  const showSuccessMessage = (message: string) => {
    // TODO: 实现成功消息显示，可以使用现有的通知系统
    console.log('[Success]', message);
  };

  const showErrorMessage = (message: string) => {
    // TODO: 实现错误消息显示
    console.error('[Error]', message);
  };

  const showInfoMessage = (message: string) => {
    // TODO: 实现信息消息显示
    console.log('[Info]', message);
  };

  return {
    // 状态
    pendingEditData,
    originalContentForPreview,
    previewedContent,

    // 方法
    showReplacePreview,
    showAppendPreview,
    showPrependPreview,
    showInsertPreview,
    clearExistingPreview,
    insertPreviewContentInEditor,
    showSuccessMessage,
    showErrorMessage,
    showInfoMessage,
    testPreviewButtons,
  };
} 