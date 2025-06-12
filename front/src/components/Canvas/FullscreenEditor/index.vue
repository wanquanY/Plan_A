<template>
  <div class="canvas-fullscreen-editor">
    <!-- 顶部工具栏 -->
    <TopBar 
      :canvas-id="canvasId"
      :canvas-name="canvasName"
      @back="handleBack"
      @save="handleSave"
      @export="handleExport"
      @share="handleShare"
    />
    
    <!-- 主内容区域 -->
    <div class="editor-main-content">
      <!-- 左侧工具面板 -->
      <LeftSidebar 
        :active-tool="activeTool"
        @tool-change="handleToolChange"
        @shape-select="handleShapeSelect"
        @grid-toggle="handleGridToggle"
        @snap-toggle="handleSnapToggle"
        @zoom-in="handleZoomIn"
        @zoom-out="handleZoomOut"
        @zoom-reset="handleZoomReset"
      />
      
      <!-- 画布区域 -->
      <div class="canvas-area">
        <CanvasContainer 
          ref="canvasContainer"
          :canvas-id="canvasId"
          :active-tool="activeTool"
          :selected-elements="selectedElements"
          @element-select="handleElementSelect"
          @element-deselect="handleElementDeselect"
          @canvas-change="handleCanvasChange"
        />
      </div>
    </div>
    
    <!-- 底部状态栏 -->
    <StatusBar 
      :zoom-level="zoomLevel"
      :cursor-position="cursorPosition"
      :selected-count="selectedElements.length"
      @zoom-change="handleZoomChange"
    />
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner"></div>
        <span>正在加载画板...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from './TopBar/index.vue'
import LeftSidebar from './LeftSidebar/index.vue'
import CanvasContainer from './Canvas/CanvasContainer.vue'
import StatusBar from './StatusBar/index.vue'

// Props
const route = useRoute()
const router = useRouter()

// 画板ID
const canvasId = computed(() => route.params.canvasId as string)

// 状态数据
const loading = ref(true)
const canvasName = ref('新建画板')
const activeTool = ref('select')
const selectedElements = ref<any[]>([])
const canvasProperties = ref({
  width: 1920,
  height: 1080,
  background: '#ffffff',
  grid: false,
  snap: true
})
const zoomLevel = ref(100)
const cursorPosition = ref({ x: 0, y: 0 })

// 组件引用
const canvasContainer = ref<any>(null)

// 生命周期
onMounted(async () => {
  try {
    // 加载画板数据
    await loadCanvasData()
    
    // 设置全屏样式
    document.body.classList.add('canvas-fullscreen-mode')
    
    // 设置键盘快捷键
    setupKeyboardShortcuts()
    
    loading.value = false
  } catch (error) {
    console.error('加载画板失败:', error)
    // 可以显示错误提示
    loading.value = false
  }
})

onUnmounted(() => {
  // 清理全屏样式
  document.body.classList.remove('canvas-fullscreen-mode')
  
  // 清理键盘监听器
  cleanupKeyboardShortcuts()
  
  // 确保页面可以正常滚动
  document.body.style.overflow = ''
  document.documentElement.style.overflow = ''
})

// 方法
const loadCanvasData = async () => {
  // TODO: 从后端API加载画板数据
  console.log('加载画板数据:', canvasId.value)
  
  // 模拟加载延迟
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // 设置默认数据
  canvasName.value = `画板 ${canvasId.value}`
}

const handleBack = async () => {
  // 保存当前状态
  await handleSave()
  
  // 返回到原来的页面
  const returnTo = route.query.returnTo as string
  if (returnTo) {
    // 检查并恢复状态
    try {
      const savedState = sessionStorage.getItem('canvasReturnState')
      if (savedState) {
        const state = JSON.parse(savedState)
        // 检查时间戳，如果超过10分钟就不恢复（避免恢复过期的位置）
        if (Date.now() - state.timestamp < 10 * 60 * 1000) {
          // 将状态保存到全局变量，供页面加载时使用
          window.__CANVAS_RETURN_STATE__ = {
            scrollPosition: state.scroll ? {
              x: state.scroll.left,
              y: state.scroll.top
            } : null,
            editorState: state.editor || null
          }
          console.log('设置返回状态:', window.__CANVAS_RETURN_STATE__)
        }
        // 清理sessionStorage
        sessionStorage.removeItem('canvasReturnState')
      }
    } catch (error) {
      console.error('处理返回状态失败:', error)
    }
    
    await router.push(returnTo)
    
    // 恢复页面状态
    await nextTick()
    
    // 恢复滚动位置
    if (window.__CANVAS_RETURN_STATE__?.scrollPosition) {
      requestAnimationFrame(() => {
        window.scrollTo({
          top: window.__CANVAS_RETURN_STATE__.scrollPosition.y,
          left: window.__CANVAS_RETURN_STATE__.scrollPosition.x,
          behavior: 'instant'
        })
      })
    }
    
    // 编辑器状态恢复现在由EditorContent组件在onMounted时自动处理
    // 延迟清理状态，给编辑器足够时间完成恢复
    setTimeout(() => {
      if (window.__CANVAS_RETURN_STATE__) {
        console.log('清理画布返回状态')
        delete window.__CANVAS_RETURN_STATE__
      }
    }, 2000)
    
  } else {
    router.push('/')
  }
}

// 恢复编辑器状态
const restoreEditorState = (editorState: any) => {
  try {
    if (!editorState || !editorState.markerId) {
      console.log('[FullscreenEditor] 没有有效的编辑器状态需要恢复')
      return
    }
    
    // 查找光标标记
    const marker = document.getElementById(editorState.markerId)
    if (marker) {
      console.log('[FullscreenEditor] 找到光标标记，恢复光标位置')
      
      // 创建选择范围
      const selection = window.getSelection()
      if (selection) {
        const range = document.createRange()
        
        // 将光标设置到标记位置
        range.setStartBefore(marker)
        range.setEndBefore(marker)
        
        // 应用选择
        selection.removeAllRanges()
        selection.addRange(range)
        
        // 移除标记
        marker.parentNode?.removeChild(marker)
        
        // 确保编辑器获得焦点
        const editorElement = document.querySelector('[contenteditable="true"]')
        if (editorElement) {
          (editorElement as HTMLElement).focus()
        }
        
        console.log('[FullscreenEditor] 成功恢复编辑器光标位置')
      }
    } else {
      console.warn('[FullscreenEditor] 未找到光标标记，尝试备用方案')
      
      // 备用方案：基于段落索引恢复
      if (typeof editorState.paragraphIndex === 'number') {
        const paragraphs = document.querySelectorAll('p, div[contenteditable]')
        const targetParagraph = paragraphs[editorState.paragraphIndex]
        
        if (targetParagraph) {
          const selection = window.getSelection()
          if (selection) {
            const range = document.createRange()
            
            // 尝试找到匹配的文本节点
            const textNodes = Array.from(targetParagraph.childNodes).filter(
              node => node.nodeType === Node.TEXT_NODE && 
                     node.textContent?.startsWith(editorState.containerText)
            )
            
            if (textNodes.length > 0) {
              const textNode = textNodes[0]
              const offset = Math.min(editorState.offset, textNode.textContent?.length || 0)
              range.setStart(textNode, offset)
              range.setEnd(textNode, offset)
            } else {
              // 如果找不到匹配的文本节点，就设置到段落开始
              range.selectNodeContents(targetParagraph)
              range.collapse(true)
            }
            
            selection.removeAllRanges()
            selection.addRange(range)
            
            const editorElement = document.querySelector('[contenteditable="true"]')
            if (editorElement) {
              (editorElement as HTMLElement).focus()
            }
            
            console.log('[FullscreenEditor] 使用备用方案恢复光标位置')
          }
        }
      }
    }
    
    // 清理所有遗留的光标标记
    const allMarkers = document.querySelectorAll('[data-cursor-marker="true"]')
    allMarkers.forEach(marker => {
      marker.parentNode?.removeChild(marker)
    })
    
  } catch (error) {
    console.error('[FullscreenEditor] 恢复编辑器状态失败:', error)
  }
}

const handleSave = async () => {
  console.log('保存画板:', canvasId.value)
  // TODO: 实现保存逻辑
}

const handleExport = (format: string) => {
  console.log('导出画板:', format)
  // TODO: 实现导出逻辑
}

const handleShare = () => {
  console.log('分享画板')
  // TODO: 实现分享逻辑
}

const handleToolChange = (tool: string) => {
  activeTool.value = tool
  console.log('切换工具:', tool)
}

const handleShapeSelect = (shape: any) => {
  console.log('选择形状:', shape)
  
  // 通知画布容器添加形状
  if (canvasContainer.value) {
    canvasContainer.value.addShape(shape)
  }
}

const handleElementSelect = (elements: any[]) => {
  selectedElements.value = elements
}

const handleElementDeselect = () => {
  selectedElements.value = []
}

const handleCanvasChange = (changes: any) => {
  console.log('画布变化:', changes)
  // TODO: 处理画布变化
}

const handleZoomChange = (zoom: number) => {
  zoomLevel.value = zoom
  if (canvasContainer.value) {
    canvasContainer.value.setZoom(zoom)
  }
}

const handleGridToggle = () => {
  if (canvasContainer.value) {
    canvasContainer.value.toggleGrid()
  }
  canvasProperties.value.grid = !canvasProperties.value.grid
  console.log('网格切换:', canvasProperties.value.grid)
}

const handleSnapToggle = (snap: boolean) => {
  canvasProperties.value.snap = snap
  console.log('捕捉切换:', snap)
}

const handleZoomIn = () => {
  if (canvasContainer.value) {
    canvasContainer.value.zoomIn()
  }
}

const handleZoomOut = () => {
  if (canvasContainer.value) {
    canvasContainer.value.zoomOut()
  }
}

const handleZoomReset = () => {
  if (canvasContainer.value) {
    canvasContainer.value.zoomReset()
  }
}

const setupKeyboardShortcuts = () => {
  document.addEventListener('keydown', handleKeyDown)
}

const cleanupKeyboardShortcuts = () => {
  document.removeEventListener('keydown', handleKeyDown)
}

const handleKeyDown = (event: KeyboardEvent) => {
  // ESC - 返回
  if (event.key === 'Escape') {
    handleBack()
    return
  }
  
  // Ctrl+S - 保存
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault()
    handleSave()
    return
  }
  
  // Ctrl+Z - 撤销
  if (event.ctrlKey && event.key === 'z' && !event.shiftKey) {
    event.preventDefault()
    // TODO: 实现撤销
    return
  }
  
  // Ctrl+Y 或 Ctrl+Shift+Z - 重做
  if ((event.ctrlKey && event.key === 'y') || (event.ctrlKey && event.shiftKey && event.key === 'z')) {
    event.preventDefault()
    // TODO: 实现重做
    return
  }
}
</script>

<style scoped>
.canvas-fullscreen-editor {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
  overflow: hidden;
}

.editor-main-content {
  flex: 1;
  display: flex;
  min-height: 0;
}

.canvas-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background-color: #ffffff;
  position: relative;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-spinner span {
  color: #666;
  font-size: 14px;
}
</style>

<style>
/* 全屏模式下的全局样式 */
body.canvas-fullscreen-mode {
  overflow: hidden;
}
</style> 