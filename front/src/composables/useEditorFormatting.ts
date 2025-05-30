import { nextTick } from 'vue';

export function useEditorFormatting() {
  // 获取完整内容的辅助方法
  const getFullContent = (editorRef: HTMLElement | null) => {
    if (editorRef) {
      return editorRef.innerHTML;
    }
    return '';
  };

  // 格式化操作
  const applyFormat = ({ command, value }: { command: string; value?: string }, editorRef: HTMLElement | null, emit: Function) => {
    // 应用格式化命令
    document.execCommand(command, false, value);
    
    // 获取应用格式化后的内容
    const newContent = getFullContent(editorRef);
    
    // 发出内容更新事件
    emit('update:modelValue', newContent);
    
    // 聚焦编辑器以保持光标位置
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  // 设置标题
  const setHeading = (heading: string, editorRef: HTMLElement | null, emit: Function) => {
    // 应用格式化
    document.execCommand('formatBlock', false, heading);
    
    // 获取应用格式化后的内容
    const newContent = getFullContent(editorRef);
    
    // 发出内容更新事件
    emit('update:modelValue', newContent);
    
    // 聚焦编辑器以保持光标位置
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  // 设置字号
  const setFontSize = (size: string, editorRef: HTMLElement | null, emit: Function) => {
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
    const newContent = getFullContent(editorRef);
    
    // 发出内容更新事件
    emit('update:modelValue', newContent);
    
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  // 设置字间距
  const setLetterSpacing = (spacing: string, editorRef: HTMLElement | null, emit: Function) => {
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const span = document.createElement('span');
      span.style.letterSpacing = spacing;
      range.surroundContents(span);
      
      // 获取应用格式化后的内容
      const newContent = getFullContent(editorRef);
      
      // 发出内容更新事件
      emit('update:modelValue', newContent);
    }
    
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  // 设置行高
  const setLineHeight = (height: string, editorRef: HTMLElement | null, emit: Function) => {
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      
      // 检查选择是否包含多个段落或完整段落
      let containsElement = false;
      let startNode: Node | null = range.startContainer;
      
      // 查找最近的块级元素
      while (startNode && startNode !== editorRef) {
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
      const newContent = getFullContent(editorRef);
      
      // 发出内容更新事件
      emit('update:modelValue', newContent);
    }
    
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  // 撤销和重做操作
  const undoAction = (editorRef: HTMLElement | null) => {
    document.execCommand('undo', false);
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  const redoAction = (editorRef: HTMLElement | null) => {
    document.execCommand('redo', false);
    nextTick(() => {
      if (editorRef) {
        editorRef.focus();
      }
    });
  };

  return {
    getFullContent,
    applyFormat,
    setHeading,
    setFontSize,
    setLetterSpacing,
    setLineHeight,
    undoAction,
    redoAction,
  };
} 