<template>
  <div class="canvas-topbar">
    <div class="topbar-left">
      <!-- 返回按钮 -->
      <button class="back-btn" @click="$emit('back')" title="返回文档 (Esc)">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8.5 2.75a.75.75 0 0 0-1.06-.02L2.22 7.47a.75.75 0 0 0 0 1.06l5.22 4.74a.75.75 0 0 0 1.06-1.04L4.81 8.5h7.44a.75.75 0 0 0 0-1.5H4.81l3.69-3.73a.75.75 0 0 0 .02-1.06z"/>
        </svg>
      </button>
      
      <!-- 画板名称 -->
      <div class="canvas-title">
        <input 
          v-if="editingTitle"
          v-model="titleInput"
          class="title-input"
          @blur="handleTitleSave"
          @keydown.enter="handleTitleSave"
          @keydown.esc="handleTitleCancel"
          ref="titleInputRef"
        />
        <span 
          v-else
          class="title-text"
          @dblclick="handleTitleEdit"
        >
          {{ canvasName }}
        </span>
      </div>
    </div>
    
    <div class="topbar-center">
      <!-- 中央工具区域 -->
      <div class="center-tools">
        <!-- 撤销重做 -->
        <div class="tool-group">
          <button class="tool-btn" @click="handleUndo" :disabled="!canUndo" title="撤销 (Ctrl+Z)">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1.5 8a6.5 6.5 0 0 1 11.49-4.22.75.75 0 0 0 1.06-1.06A8 8 0 0 0 0 8a8 8 0 0 0 8 8 .75.75 0 0 0 0-1.5A6.5 6.5 0 0 1 1.5 8z"/>
              <path d="M6.44 3.44a.75.75 0 0 1 1.06 1.06L5.06 7h2.69a.75.75 0 0 1 0 1.5H5.06l2.44 2.44a.75.75 0 0 1-1.06 1.06l-3.75-3.75a.75.75 0 0 1 0-1.06l3.75-3.75z"/>
            </svg>
          </button>
          <button class="tool-btn" @click="handleRedo" :disabled="!canRedo" title="重做 (Ctrl+Y)">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M14.5 8a6.5 6.5 0 0 0-11.49-4.22.75.75 0 0 1-1.06-1.06A8 8 0 0 1 16 8a8 8 0 0 1-8 8 .75.75 0 0 1 0-1.5A6.5 6.5 0 0 0 14.5 8z"/>
              <path d="M9.56 3.44a.75.75 0 0 0-1.06 1.06L10.94 7H8.25a.75.75 0 0 0 0 1.5h2.69l-2.44 2.44a.75.75 0 0 0 1.06 1.06l3.75-3.75a.75.75 0 0 0 0-1.06l-3.75-3.75z"/>
            </svg>
          </button>
        </div>
        
        <!-- 分隔线 -->
        <div class="divider"></div>
        
        <!-- 视图控制 -->
        <div class="tool-group">
          <button class="tool-btn" @click="toggleGrid" :class="{ active: showGrid }" title="网格">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zM2.5 2a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zm7-1A1.5 1.5 0 0 1 11 2.5v3A1.5 1.5 0 0 1 9.5 7h-3A1.5 1.5 0 0 1 5 5.5v-3A1.5 1.5 0 0 1 6.5 1h3zM6.5 2a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zM1 10.5A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zM2.5 10a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zm7-1A1.5 1.5 0 0 1 11 10.5v3A1.5 1.5 0 0 1 9.5 15h-3A1.5 1.5 0 0 1 5 13.5v-3A1.5 1.5 0 0 1 6.5 9h3zM6.5 10a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3z"/>
            </svg>
          </button>
          <button class="tool-btn" @click="fitToScreen" title="适合屏幕">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M5.828 10.172a.5.5 0 0 0-.707 0l-4.096 4.096V11a.5.5 0 0 0-1 0v3.975a.5.5 0 0 0 .5.5H4.5a.5.5 0 0 0 0-1H1.732l4.096-4.096a.5.5 0 0 0 0-.707zm4.344-4.344a.5.5 0 0 0 .707 0l4.096-4.096V5a.5.5 0 1 0 1 0V1.025a.5.5 0 0 0-.5-.5H11.5a.5.5 0 0 0 0 1h3.268l-4.096 4.096a.5.5 0 0 0 0 .707z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <div class="topbar-right">
      <!-- 右侧功能按钮 -->
      <div class="action-buttons">
        <!-- 协作 -->
        <button class="action-btn" @click="$emit('share')" title="分享">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M11 2.5a2.5 2.5 0 1 1 .603 1.628l-6.718 3.12a2.499 2.499 0 0 1 0 1.504l6.718 3.12a2.5 2.5 0 1 1-.488.876l-6.718-3.12a2.5 2.5 0 1 1 0-3.256l6.718-3.12A2.5 2.5 0 0 1 11 2.5z"/>
          </svg>
          <span class="btn-text">分享</span>
        </button>
        
        <!-- 评论 -->
        <button class="action-btn" @click="handleComments" title="评论">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2.678 11.894a1 1 0 0 1 .287.801 10.97 10.97 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8.06 8.06 0 0 0 8 14c3.996 0 7-2.807 7-6 0-3.192-3.004-6-7-6S1 4.808 1 8c0 1.468.617 2.83 1.678 3.894zm-.493 3.905a21.682 21.682 0 0 1-.713.129c-.2.032-.352-.176-.273-.362a9.68 9.68 0 0 0 .244-.637l.003-.01c.248-.72.45-1.548.524-2.319C.743 11.37 0 9.76 0 8c0-3.866 3.582-7 8-7s8 3.134 8 7-3.582 7-8 7a9.06 9.06 0 0 1-2.347-.306c-.52.263-1.639.742-3.468 1.105z"/>
          </svg>
          <span class="btn-text">评论</span>
          <span v-if="commentCount > 0" class="comment-badge">{{ commentCount }}</span>
        </button>
        
        <!-- 导出 -->
        <div class="dropdown-container">
          <button 
            class="action-btn" 
            @click="toggleExportMenu" 
            :class="{ active: showExportMenu }"
            title="导出"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
              <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
            </svg>
            <span class="btn-text">导出</span>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" class="dropdown-arrow">
              <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
            </svg>
          </button>
          
          <!-- 导出菜单 -->
          <div v-if="showExportMenu" class="export-menu">
            <button class="export-option" @click="handleExport('png')">
              <span>PNG 图片</span>
            </button>
            <button class="export-option" @click="handleExport('svg')">
              <span>SVG 矢量图</span>
            </button>
            <button class="export-option" @click="handleExport('pdf')">
              <span>PDF 文档</span>
            </button>
            <button class="export-option" @click="handleExport('json')">
              <span>JSON 数据</span>
            </button>
          </div>
        </div>
        
        <!-- 保存 -->
        <button class="action-btn primary" @click="$emit('save')" title="保存 (Ctrl+S)">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H9.5a1 1 0 0 0-1 1v7.293l2.646-2.647a.5.5 0 0 1 .708.708l-3.5 3.5a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L7.5 9.293V2a2 2 0 0 1 2-2H14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h2.5a.5.5 0 0 1 0 1H2z"/>
          </svg>
          <span class="btn-text">保存</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

// Props
const props = defineProps<{
  canvasId: string
  canvasName: string
}>()

// Emits
const emit = defineEmits<{
  back: []
  save: []
  export: [format: string]
  share: []
}>()

// 状态
const editingTitle = ref(false)
const titleInput = ref('')
const titleInputRef = ref<HTMLInputElement>()
const showExportMenu = ref(false)
const showGrid = ref(true)
const canUndo = ref(false)
const canRedo = ref(false)
const commentCount = ref(0)

// 方法
const handleTitleEdit = () => {
  editingTitle.value = true
  titleInput.value = props.canvasName
  nextTick(() => {
    titleInputRef.value?.focus()
    titleInputRef.value?.select()
  })
}

const handleTitleSave = () => {
  if (titleInput.value.trim()) {
    // TODO: 保存标题
    console.log('保存标题:', titleInput.value)
  }
  editingTitle.value = false
}

const handleTitleCancel = () => {
  editingTitle.value = false
  titleInput.value = ''
}

const handleUndo = () => {
  console.log('撤销')
  // TODO: 实现撤销逻辑
}

const handleRedo = () => {
  console.log('重做')
  // TODO: 实现重做逻辑
}

const toggleGrid = () => {
  showGrid.value = !showGrid.value
  console.log('切换网格:', showGrid.value)
  // TODO: 实现网格切换
}

const fitToScreen = () => {
  console.log('适合屏幕')
  // TODO: 实现适合屏幕逻辑
}

const handleComments = () => {
  console.log('打开评论')
  // TODO: 实现评论功能
}

const toggleExportMenu = () => {
  showExportMenu.value = !showExportMenu.value
}

const handleExport = (format: string) => {
  showExportMenu.value = false
  emit('export', format)
}

// 点击外部关闭菜单
document.addEventListener('click', (e) => {
  if (!e.target?.closest('.dropdown-container')) {
    showExportMenu.value = false
  }
})
</script>

<style scoped>
.canvas-topbar {
  height: 56px;
  background-color: #ffffff;
  border-bottom: 1px solid #e1e4e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: relative;
  z-index: 100;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.back-btn:hover {
  background-color: #f6f8fa;
  color: #24292f;
}

.canvas-title {
  display: flex;
  align-items: center;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: #24292f;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

.title-text:hover {
  background-color: #f6f8fa;
}

.title-input {
  font-size: 16px;
  font-weight: 600;
  color: #24292f;
  border: 2px solid #1890ff;
  border-radius: 4px;
  padding: 4px 8px;
  background-color: #ffffff;
  outline: none;
  min-width: 200px;
}

.topbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.center-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 4px;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 4px;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 4px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tool-btn:hover:not(:disabled) {
  background-color: #ffffff;
  color: #24292f;
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tool-btn.active {
  background-color: #1890ff;
  color: #ffffff;
}

.divider {
  width: 1px;
  height: 24px;
  background-color: #d0d7de;
  margin: 0 8px;
}

.topbar-right {
  flex: 0 0 auto;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background-color: #ffffff;
  color: #24292f;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 14px;
  position: relative;
}

.action-btn:hover {
  background-color: #f6f8fa;
  border-color: #8b949e;
}

.action-btn.primary {
  background-color: #1890ff;
  border-color: #1890ff;
  color: #ffffff;
}

.action-btn.primary:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

.action-btn.active {
  background-color: #f6f8fa;
  border-color: #1890ff;
}

.btn-text {
  font-size: 14px;
  font-weight: 500;
}

.comment-badge {
  background-color: #ff4d4f;
  color: #ffffff;
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: 600;
  min-width: 18px;
  text-align: center;
}

.dropdown-container {
  position: relative;
}

.dropdown-arrow {
  margin-left: 4px;
  transition: transform 0.15s ease;
}

.action-btn.active .dropdown-arrow {
  transform: rotate(180deg);
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background-color: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 8px 0;
  min-width: 160px;
  z-index: 1000;
}

.export-option {
  width: 100%;
  height: 36px;
  padding: 0 16px;
  border: none;
  background-color: transparent;
  color: #24292f;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.15s ease;
  font-size: 14px;
}

.export-option:hover {
  background-color: #f6f8fa;
}
</style> 