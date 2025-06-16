<template>
  <div class="pdf-export-container">
    <!-- PDF导出按钮 -->
    <a-button 
      type="text" 
      size="small" 
      :loading="loading" 
      class="pdf-export-btn"
      @click="handleExport"
      :title="'导出PDF - 保持原始格式和渲染效果'"
    >
      <FilePdfOutlined />
      <span v-if="!collapsed">导出PDF</span>
    </a-button>


  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue';
import { message } from 'ant-design-vue';
import { 
  FilePdfOutlined
} from '@ant-design/icons-vue';
import pdfExportService, { type PDFExportOptions } from '../services/pdfExportService';

// Props
const props = defineProps({
  content: {
    type: String,
    required: true
  },
  title: {
    type: String,
    default: '笔记'
  },
  collapsed: {
    type: Boolean,
    default: false
  }
});

// 状态
const loading = ref(false);

// 主导出功能
const handleExport = async () => {
  try {
    loading.value = true;
    
    console.log('开始导出PDF，内容:', props.content);
    console.log('导出标题:', props.title);
    
    // 检查内容是否为空
    if (!props.content || props.content.trim() === '') {
      message.error('笔记内容为空，无法导出PDF');
      return;
    }
    
    message.loading('正在生成PDF，请稍候...', 0);
    
    await pdfExportService.exportNoteAsPDF(props.content, props.title);
    
    message.destroy();
    message.success('PDF导出成功！');
  } catch (error: any) {
    console.error('PDF导出失败:', error);
    message.destroy();
    message.error(error.message || 'PDF导出失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};


</script>

<style scoped>
.pdf-export-container {
  display: inline-block;
}

.pdf-export-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6b7280;
  transition: all 0.2s ease;
}

.pdf-export-btn:hover {
  color: #3b82f6;
  background-color: #f3f4f6;
}

.pdf-export-btn:focus {
  color: #3b82f6;
}

:deep(.ant-dropdown) {
  z-index: 1050;
}

:deep(.ant-modal) {
  z-index: 1060;
}

:deep(.ant-input-number) {
  width: 100%;
}

:deep(.ant-col) {
  text-align: center;
}

:deep(.ant-col .ant-input-number) {
  text-align: center;
}
</style> 