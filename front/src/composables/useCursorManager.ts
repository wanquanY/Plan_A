import { nextTick } from 'vue';

export function useCursorManager() {
  // 检查光标是否在包含@提及的同一行
  const isCursorInSameLineWithMention = (selection: Selection | null, mention: HTMLElement) => {
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
    let cursorParagraph: Node | null = cursorNode;
    while (cursorParagraph && cursorParagraph.nodeType !== Node.ELEMENT_NODE) {
      cursorParagraph = cursorParagraph.parentNode;
    }
    
    // 获取提及元素所在的段落
    let mentionParagraph: HTMLElement | null = mention;
    while (mentionParagraph && mentionParagraph.nodeName !== 'P' && mentionParagraph.nodeName !== 'DIV') {
      mentionParagraph = mentionParagraph.parentNode as HTMLElement;
    }
    
    // 判断光标和提及是否在同一个段落中
    return cursorParagraph === mentionParagraph;
  };

  // 在光标位置插入内容
  const insertContentAtCursor = async (responseText: string, editorRef: HTMLElement | null, currentCursorRange: Range | null) => {
    console.log('[CursorManager] Request to insert:', responseText);
    console.log('[CursorManager] Current cursor range exists:', !!currentCursorRange);
    
    if (!editorRef || !responseText) {
      console.warn('[CursorManager] Editor instance or responseText not available for insert.');
      return;
    }

    try {
      // 聚焦编辑器
      editorRef.focus();

      // 获取当前选择
      const selection = window.getSelection();
      let range = null;

      // 首先检查是否有保存的光标位置
      if (currentCursorRange) {
        try {
          // 检查保存的范围是否仍然有效
          const container = currentCursorRange.startContainer;
          const offset = currentCursorRange.startOffset;
          
          console.log('[CursorManager] 检查保存的光标位置，容器:', container.nodeName, '偏移:', offset);
          
          // 验证保存的范围是否仍在文档中
          if (document.contains(container)) {
            // 验证偏移值是否在有效范围内
            const maxOffset = container.nodeType === Node.TEXT_NODE 
              ? container.textContent?.length || 0
              : container.childNodes.length;
            
            const validOffset = Math.min(offset, maxOffset);
            
            // 创建新的范围
            range = document.createRange();
            range.setStart(container, validOffset);
            range.setEnd(container, validOffset);
            
            // 设置选择
            selection?.removeAllRanges();
            selection?.addRange(range);
            console.log('[CursorManager] 成功恢复保存的光标位置，偏移:', validOffset);
          } else {
            console.warn('[CursorManager] 保存的光标位置已失效，容器不在文档中');
          }
        } catch (e) {
          console.warn('[CursorManager] 保存的光标范围检查失败:', e);
        }
      }

      // 如果没有有效的保存范围，尝试使用当前选择
      if (!range && selection && selection.rangeCount > 0) {
        range = selection.getRangeAt(0);
        console.log('[CursorManager] 使用当前选择位置');
      }

      // 如果仍然没有有效范围，寻找合适的插入位置
      if (!range) {
        console.log('[CursorManager] 寻找合适的插入位置');
        range = document.createRange();
        
        // 寻找合适的插入位置
        const editableContent = editorRef.querySelector('.editable-content') || editorRef;
        
        // 先尝试找到调试标记的位置
        const debugMarker = document.getElementById('debug-cursor-position');
        if (debugMarker) {
          console.log('[CursorManager] 找到调试标记，在其位置插入');
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
              range.setStart(lastParagraph.lastChild, lastParagraph.lastChild.textContent?.length || 0);
              range.setEnd(lastParagraph.lastChild, lastParagraph.lastChild.textContent?.length || 0);
            } else {
              range.selectNodeContents(lastParagraph);
              range.collapse(false); // 移动到末尾
            }
            console.log('[CursorManager] 插入位置设置到最后一个段落末尾');
          } else {
            // 如果没有段落，在可编辑区域开始处创建
            range.selectNodeContents(editableContent);
            range.collapse(true);
            console.log('[CursorManager] 插入位置设置到可编辑区域开始');
          }
        }
        
        selection?.removeAllRanges();
        selection?.addRange(range);
      }

      console.log('[CursorManager] 最终插入位置 - 容器:', range.startContainer.nodeName, '偏移:', range.startOffset);

      // 检查内容是否包含markdown语法，如果是则先转换为HTML
      let processedContent = responseText.trim();
      let isMarkdownContent = false;
      
      // 检查是否包含markdown语法
      const hasMarkdownSyntax = responseText.includes('```') || 
                               responseText.includes('# ') || 
                               responseText.includes('## ') || 
                               responseText.includes('**') || 
                               responseText.includes('*') ||
                               responseText.includes('`') ||
                               (responseText.includes('[') && responseText.includes(']('));
      
      if (hasMarkdownSyntax) {
        try {
          console.log('[CursorManager] 检测到markdown语法，转换为HTML');
          // 动态导入markdown服务
          const markdownModule = await import('../services/markdownService');
          processedContent = markdownModule.markdownToHtml(responseText);
          isMarkdownContent = true;
          console.log('[CursorManager] Markdown转换完成，HTML长度:', processedContent.length);
        } catch (error) {
          console.error('[CursorManager] Markdown转换失败:', error);
          // 转换失败时使用原始文本
          processedContent = responseText.trim();
          isMarkdownContent = false;
        }
      }
      
      // 删除选择的内容（如果有）
      if (!range.collapsed) {
        range.deleteContents();
        console.log('[CursorManager] 删除选中内容');
      }

      // 处理插入逻辑
      const fragment = document.createDocumentFragment();
      
      if (isMarkdownContent) {
        // HTML内容处理
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = processedContent;
        
        // 将所有HTML元素添加到fragment中
        while (tempDiv.firstChild) {
          fragment.appendChild(tempDiv.firstChild);
        }
        console.log('[CursorManager] 创建HTML内容片段');
      } else {
        // 纯文本处理 - 将响应文本按段落分割
        const paragraphs = processedContent.split(/\n\s*\n/).filter(p => p.trim());
        
        if (paragraphs.length === 0) {
          // 如果没有段落，插入一个空段落
          const emptyP = document.createElement('p');
          emptyP.innerHTML = '<br>';
          fragment.appendChild(emptyP);
          console.log('[CursorManager] 插入空段落');
        } else {
          console.log('[CursorManager] 创建', paragraphs.length, '个段落');
          paragraphs.forEach((paragraph) => {
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
      }

      // 插入内容
      range.insertNode(fragment);
      console.log('[CursorManager] 内容已插入到DOM');

      // 将光标移动到插入内容的末尾
      range.collapse(false);

      selection?.removeAllRanges();
      selection?.addRange(range);
      console.log('[CursorManager] 光标已移动到插入内容末尾');

      // 触发输入事件以更新modelValue
      const inputEvent = new Event('input', { bubbles: true });
      editorRef.dispatchEvent(inputEvent);

      console.log('[CursorManager] Content inserted successfully at cursor position');
      
      // 插入内容后，触发渲染
      nextTick(async () => {
        try {
          console.log('插入内容后触发markdown渲染');
          // 动态导入渲染服务
          const renderModule = await import('../services/renderService');
          renderModule.renderContentComponents(true);
        } catch (error) {
          console.error('处理插入的markdown内容失败:', error);
        }
      });

    } catch (error) {
      console.error('[CursorManager] Error inserting content:', error);
    }
  };

  return {
    isCursorInSameLineWithMention,
    insertContentAtCursor,
  };
} 