<template>
  <!-- 渲染组件（隐藏） -->
  <div style="display: none;">
    <MermaidRenderer ref="mermaidRenderer" />
    <CodeBlock ref="codeBlockRenderer" :code="''" :language="'text'" />
    <MarkMap ref="markMapRenderer" :content="''" />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import MermaidRenderer from '../../rendering/MermaidRenderer.vue';
import CodeBlock from '../../rendering/CodeBlock.vue';
import MarkMap from '../../rendering/MarkMap.vue';
import { renderMermaidDynamically, renderCodeBlocks, renderMarkMaps } from '../../../services/renderService';

// 组件引用
const mermaidRenderer = ref(null);
const codeBlockRenderer = ref(null);
const markMapRenderer = ref(null);

// 渲染特殊组件（Mermaid、代码块、思维导图等）
const renderSpecialComponents = () => {
  nextTick(() => {
    try {
      // 渲染 Mermaid 图表
      renderMermaidDynamically();
      
      // 渲染代码块
      renderCodeBlocks();
      
      // 渲染思维导图
      renderMarkMaps();
      
      console.log('特殊组件渲染完成');
    } catch (error) {
      console.error('渲染特殊组件失败:', error);
    }
  });
};

// 处理笔记编辑工具结果的函数
const handleNoteEditorResult = (toolResult: any) => {
  console.log('[AgentSidebarToolStatus] 处理笔记编辑工具结果:', toolResult);
  console.log('[AgentSidebarToolStatus] 工具结果类型:', typeof toolResult);
  console.log('[AgentSidebarToolStatus] 工具结果内容:', JSON.stringify(toolResult, null, 2));
  
  try {
    let resultData = toolResult;
    
    // 如果结果是字符串，尝试解析为JSON
    if (typeof toolResult === 'string') {
      try {
        resultData = JSON.parse(toolResult);
        console.log('[AgentSidebarToolStatus] 解析JSON后的结果:', resultData);
      } catch (e) {
        console.warn('[AgentSidebarToolStatus] 无法解析工具结果为JSON:', e);
        console.warn('[AgentSidebarToolStatus] 原始字符串内容:', toolResult);
        return null;
      }
    }
    
    console.log('[AgentSidebarToolStatus] 检查编辑结果字段:', {
      success: resultData?.success,
      note_id: resultData?.note_id,
      content_exists: resultData?.content !== undefined,
      content_length: resultData?.content?.length || 0,
      is_preview: resultData?.is_preview,
      title: resultData?.title,
      edit_type: resultData?.edit_type
    });
    
    // 检查是否是成功的笔记编辑结果
    if (resultData && resultData.success && resultData.note_id && resultData.content !== undefined) {
      console.log('[AgentSidebarToolStatus] 笔记编辑成功，准备返回预览数据');
      
      const previewData = {
        noteId: resultData.note_id,
        title: resultData.title,
        content: resultData.content,
        editType: resultData.edit_type,
        isPreview: resultData.is_preview || false,
        changes: resultData.changes,
        updatedAt: resultData.updated_at,
        contentPreview: resultData.content_preview
      };
      
      console.log('[AgentSidebarToolStatus] 即将返回的预览数据:', previewData);
      return previewData;
    } else {
      console.log('[AgentSidebarToolStatus] 笔记编辑结果不符合预期格式:', {
        has_success: !!resultData?.success,
        success_value: resultData?.success,
        has_note_id: !!resultData?.note_id,
        note_id_value: resultData?.note_id,
        has_content: resultData?.content !== undefined,
        content_sample: resultData?.content?.substring(0, 100)
      });
      
      // 尝试查看是否有其他可能的字段名称
      console.log('[AgentSidebarToolStatus] 可用的字段:', Object.keys(resultData || {}));
    }
  } catch (error) {
    console.error('[AgentSidebarToolStatus] 处理笔记编辑结果时出错:', error);
  }
  
  return null;
};

// 暴露方法
defineExpose({
  renderSpecialComponents,
  handleNoteEditorResult
});
</script>

<style scoped>
/* 这个组件没有可见的UI，所以不需要样式 */
</style> 