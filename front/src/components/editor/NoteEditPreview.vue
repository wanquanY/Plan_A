<template>
  <div v-if="visible" class="note-edit-preview-overlay">
    <div class="preview-container">
      <div class="preview-header">
        <div class="preview-title">
          <Icon name="edit" class="icon" />
          <span>AI编辑预览</span>
          <span class="edit-type-badge">{{ getEditTypeText(editData?.editType) }}</span>
        </div>
        <button @click="handleReject" class="close-btn" title="关闭预览">
          <Icon name="close" />
        </button>
      </div>
      
      <div class="preview-content">
        <div class="content-diff">
          <div class="original-content">
            <h4>原内容</h4>
            <div class="content-box original" v-html="originalContent"></div>
          </div>
          <div class="separator">
            <Icon name="arrow-right" />
          </div>
          <div class="new-content">
            <h4>编辑后</h4>
            <div class="content-box preview" v-html="previewContent"></div>
          </div>
        </div>
        
        <div class="edit-summary" v-if="editData?.changes">
          <h4>编辑摘要</h4>
          <div class="stats">
            <span class="stat-item">
              <Icon name="text" />
              字符：{{ editData.changes.original_length }} → {{ editData.changes.new_length }}
            </span>
            <span class="stat-item">
              <Icon name="list" />
              行数：{{ editData.changes.original_lines }} → {{ editData.changes.new_lines }}
            </span>
            <span v-if="editData.changes.title_changed" class="stat-item">
              <Icon name="title" />
              标题已更新
            </span>
          </div>
        </div>
      </div>
      
      <div class="preview-actions">
        <button @click="handleReject" class="btn-reject">
          <Icon name="close" />
          拒绝编辑
        </button>
        <button @click="handleAccept" class="btn-accept">
          <Icon name="check" />
          接受编辑
        </button>
      </div>
    </div>
    
    <!-- 编辑器高亮覆盖层 -->
    <div class="editor-highlight-overlay" v-if="showEditorHighlight">
      <div class="highlight-content" v-html="previewContent"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, h } from 'vue';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  editData: {
    type: Object,
    default: null
  },
  originalContent: {
    type: String,
    default: ''
  }
});

// Events
const emit = defineEmits(['accept', 'reject', 'close']);

// State
const showEditorHighlight = ref(false);

// Computed
const previewContent = computed(() => {
  return props.editData?.content || '';
});

// Methods
const getEditTypeText = (editType: string) => {
  const typeMap = {
    'replace': '完全替换',
    'append': '追加内容',
    'prepend': '前置内容',
    'insert': '插入内容',
    'replace_lines': '替换行',
    'replace_text': '替换文本'
  };
  return typeMap[editType] || editType;
};

const handleAccept = () => {
  console.log('[NoteEditPreview] 用户接受编辑');
  emit('accept', props.editData);
};

const handleReject = () => {
  console.log('[NoteEditPreview] 用户拒绝编辑');
  emit('reject');
};

// Watch for visibility changes
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    nextTick(() => {
      showEditorHighlight.value = true;
    });
  } else {
    showEditorHighlight.value = false;
  }
});

// Icon component (简单的图标实现)
const Icon = (props) => {
  const iconMap = {
    'edit': '✏️',
    'close': '✕',
    'arrow-right': '→',
    'text': '📝',
    'list': '📋',
    'title': '🏷️',
    'check': '✓'
  };
  
  return h('span', { 
    class: `icon ${props.class || ''}`,
    style: 'display: inline-block; margin-right: 4px;'
  }, iconMap[props.name] || '●');
};
</script>

<style scoped>
.note-edit-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}

.preview-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 90vw;
  max-height: 90vh;
  width: 800px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #374151;
}

.edit-type-badge {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  color: #6b7280;
}

.close-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

.preview-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.content-diff {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.separator {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  font-size: 20px;
}

.content-box {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  background: #f9fafb;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 14px;
  line-height: 1.5;
}

.content-box.preview {
  background: #f0f9ff;
  border-color: #3b82f6;
}

.edit-summary {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.edit-summary h4 {
  margin: 0 0 8px 0;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
}

.stats {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6b7280;
  font-size: 13px;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.btn-reject,
.btn-accept {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-reject {
  background: #fee2e2;
  color: #dc2626;
}

.btn-reject:hover {
  background: #fecaca;
}

.btn-accept {
  background: #1d4ed8;
  color: white;
}

.btn-accept:hover {
  background: #1e40af;
}

.editor-highlight-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 999;
}

.highlight-content {
  background: rgba(59, 130, 246, 0.1);
  border: 2px solid #3b82f6;
  border-radius: 4px;
  animation: highlight-pulse 2s infinite;
}

@keyframes highlight-pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 0.4; }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preview-container {
    width: 95vw;
    height: 95vh;
  }
  
  .content-diff {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .separator {
    transform: rotate(90deg);
  }
  
  .stats {
    flex-direction: column;
    gap: 8px;
  }
}
</style> 