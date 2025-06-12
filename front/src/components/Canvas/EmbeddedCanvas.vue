<template>
  <div 
    class="embedded-canvas-wrapper" 
    :data-canvas-id="canvasId" 
    contenteditable="false"
  >
    <div 
      class="canvas-board" 
      :class="{ 'canvas-selected': isSelected }"
      :data-canvas-id="canvasId"
      @click="handleClick"
      @dblclick="handleDoubleClick"
      @mouseenter="showResizeHandles = true"
      @mouseleave="showResizeHandles = false"
      ref="canvasBoard"
    >
      <div 
        class="canvas-delete-btn" 
        @click.stop="handleDelete" 
        title="删除画板"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M10.5 3.5L3.5 10.5M3.5 3.5L10.5 10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      
      <!-- 拖拽控制点 -->
      <div 
        class="canvas-resize-handles" 
        :style="{ display: (isSelected || showResizeHandles) ? 'block' : 'none' }"
      >
        <!-- 四个角的控制点 -->
        <div 
          class="canvas-resize-handle canvas-resize-nw" 
          data-direction="nw"
          @mousedown="handleResizeStart"
        ></div>
        <div 
          class="canvas-resize-handle canvas-resize-ne" 
          data-direction="ne"
          @mousedown="handleResizeStart"
        ></div>
        <div 
          class="canvas-resize-handle canvas-resize-sw" 
          data-direction="sw"
          @mousedown="handleResizeStart"
        ></div>
        <div 
          class="canvas-resize-handle canvas-resize-se" 
          data-direction="se"
          @mousedown="handleResizeStart"
        ></div>
        
        <!-- 四条边的控制点 -->
        <div 
          class="canvas-resize-handle canvas-resize-n" 
          data-direction="n"
          @mousedown="handleResizeStart"
        ></div>
        <div 
          class="canvas-resize-handle canvas-resize-s" 
          data-direction="s"
          @mousedown="handleResizeStart"
        ></div>
        <div 
          class="canvas-resize-handle canvas-resize-w" 
          data-direction="w"
          @mousedown="handleResizeStart"
        ></div>
        <div 
          class="canvas-resize-handle canvas-resize-e" 
          data-direction="e"
          @mousedown="handleResizeStart"
        ></div>
      </div>
      
      <div class="canvas-content">
        <div class="canvas-icon-area">
          <div class="canvas-decorative-element canvas-element-1"></div>
          <div class="canvas-decorative-element canvas-element-2"></div>
          <div class="canvas-decorative-element canvas-element-3"></div>
          <div class="canvas-main-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect x="8" y="8" width="32" height="32" rx="4" stroke="currentColor" stroke-width="2" fill="none"/>
              <circle cx="16" cy="16" r="2" fill="currentColor"/>
              <path d="M14 24L20 18L26 24L32 18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
        <div class="canvas-text">空白画板</div>
      </div>
    </div>
    
    <!-- 全屏画板编辑模态框 -->
    <div v-if="showFullscreen" class="canvas-fullscreen-modal" @click="handleBackdropClick">
      <div class="canvas-fullscreen-backdrop"></div>
      <div class="canvas-fullscreen-container" @click.stop>
        <div class="canvas-fullscreen-header">
          <div class="canvas-fullscreen-title">
            <div class="title-icon">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <rect x="2" y="2" width="16" height="16" rx="3" stroke="currentColor" stroke-width="2"/>
                <circle cx="6" cy="6" r="1.5" fill="currentColor"/>
                <path d="M4 12L8 8L12 12L16 8" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="title-text">
              <span>画板编辑器</span>
              <small>ID: {{ canvasId }}</small>
            </div>
          </div>
          <div class="canvas-fullscreen-actions">
            <button class="canvas-action-btn canvas-save-btn" @click="saveCanvas">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M3.5 2a.5.5 0 00-.5.5v11a.5.5 0 00.5.5h9a.5.5 0 00.5-.5v-7.293L10.293 2H3.5zM11 8V2.5L13.5 5V8H11z"/>
                <path d="M4.5 4a.5.5 0 01.5-.5h4a.5.5 0 010 1H5a.5.5 0 01-.5-.5z"/>
              </svg>
              保存画板
            </button>
            <button class="canvas-action-btn canvas-close-btn" @click="closeFullscreen">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/>
              </svg>
              退出编辑
            </button>
          </div>
        </div>
        
        <div class="canvas-fullscreen-toolbar">
          <!-- 基础工具组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">基础工具</div>
            <div class="tool-group-buttons">
              <!-- 选择工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'select' }"
                @click="setTool('select')"
                title="选择 (V)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M2 2l4 9 2-1.5L12 2 2 2z"/>
                </svg>
              </button>
              
              <!-- 手型工具（移动画布） -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'hand' }"
                @click="setTool('hand')"
                title="移动画布 (H)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M6.5 1A1.5 1.5 0 005 2.5V6H3.5a1.5 1.5 0 00-1.48 1.75l.818 4.91A2 2 0 004.82 14h6.36a2 2 0 001.98-1.75l.818-4.91A1.5 1.5 0 0012.5 6H11V2.5A1.5 1.5 0 009.5 1h-3zM10 6V2.5a.5.5 0 00-.5-.5h-3a.5.5 0 00-.5.5V6h4z"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="canvas-tool-divider"></div>
          
          <!-- 图形工具组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">图形</div>
            <div class="tool-group-buttons">
              <!-- 矩形工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'rectangle' }"
                @click="setTool('rectangle')"
                title="矩形 (R)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <rect x="2" y="3" width="12" height="10" stroke="currentColor" stroke-width="1.5" rx="1"/>
                </svg>
              </button>
              
              <!-- 圆形工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'circle' }"
                @click="setTool('circle')"
                title="圆形 (O)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </button>
              
              <!-- 菱形工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'diamond' }"
                @click="setTool('diamond')"
                title="菱形 (D)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1l5 7-5 7-5-7 5-7z" stroke="currentColor" stroke-width="1.5" fill="none"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="canvas-tool-divider"></div>
          
          <!-- 连接工具组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">连接</div>
            <div class="tool-group-buttons">
              <!-- 直线工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'line' }"
                @click="setTool('line')"
                title="直线 (L)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 14L14 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </button>
              
              <!-- 箭头工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'arrow' }"
                @click="setTool('arrow')"
                title="箭头 (A)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 8h10m0 0l-3-3m3 3l-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="canvas-tool-divider"></div>
          
          <!-- 内容工具组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">内容</div>
            <div class="tool-group-buttons">
              <!-- 文本工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'text' }"
                @click="setTool('text')"
                title="文本 (T)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M4 2.5a.5.5 0 01.5-.5h7a.5.5 0 010 1h-3v11h1a.5.5 0 010 1h-3a.5.5 0 010-1h1V3h-3a.5.5 0 01-.5-.5z"/>
                </svg>
              </button>
              
              <!-- 画笔工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'pen' }"
                @click="setTool('pen')"
                title="画笔 (P)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M13.498.795l.707-.707a1.5 1.5 0 112.122 2.122l-.707.707-2.122-2.122zm-1.414 1.414L3 11.293V14h2.707l8.084-8.084-2.707-2.707z"/>
                </svg>
              </button>
              
              <!-- 橡皮擦工具 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: currentTool === 'eraser' }"
                @click="setTool('eraser')"
                title="橡皮擦 (E)"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M6.5 1a4.5 4.5 0 00-3.182 7.682L8.5 14h3a1.5 1.5 0 001.5-1.5v-1a1.5 1.5 0 00-1.5-1.5h-.5v-.5a4.5 4.5 0 00-4.5-4.5z"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="canvas-tool-divider"></div>
          
          <!-- 视图控制组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">视图</div>
            <div class="tool-group-buttons">
              <!-- 网格控制 -->
              <button 
                class="canvas-tool-btn"
                :class="{ active: showGrid }"
                @click="toggleGrid"
                :title="showGrid ? '隐藏网格' : '显示网格'"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="4" cy="4" r="1" fill="currentColor"/>
                  <circle cx="8" cy="4" r="1" fill="currentColor"/>
                  <circle cx="12" cy="4" r="1" fill="currentColor"/>
                  <circle cx="4" cy="8" r="1" fill="currentColor"/>
                  <circle cx="8" cy="8" r="1" fill="currentColor"/>
                  <circle cx="12" cy="8" r="1" fill="currentColor"/>
                  <circle cx="4" cy="12" r="1" fill="currentColor"/>
                  <circle cx="8" cy="12" r="1" fill="currentColor"/>
                  <circle cx="12" cy="12" r="1" fill="currentColor"/>
                </svg>
              </button>
              
              <!-- 网格大小控制 -->
              <div class="grid-size-control">
                <select v-model="gridSize" class="grid-size-select" :disabled="!showGrid">
                  <option value="10">10px</option>
                  <option value="20">20px</option>
                  <option value="25">25px</option>
                  <option value="50">50px</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="canvas-tool-divider"></div>
          
          <!-- 样式控制组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">样式</div>
            <div class="tool-group-buttons">
              <div class="canvas-color-picker" @click="showColorPicker = !showColorPicker">
                <div class="canvas-current-color" :style="{ backgroundColor: currentColor }"></div>
                <span class="color-label">颜色</span>
              </div>
              
              <!-- 颜色面板 -->
              <div v-if="showColorPicker" class="canvas-color-panel">
                <div class="color-preset-grid">
                  <div 
                    v-for="color in presetColors" 
                    :key="color"
                    class="color-preset-item"
                    :style="{ backgroundColor: color }"
                    :class="{ active: currentColor === color }"
                    @click="selectColor(color)"
                  ></div>
                </div>
                <div class="color-input-group">
                  <input 
                    type="color" 
                    v-model="currentColor"
                    class="color-input"
                  />
                  <input 
                    type="text" 
                    v-model="currentColor"
                    class="color-text-input"
                    placeholder="#1890ff"
                  />
                </div>
              </div>
              
              <div class="canvas-stroke-width">
                <span class="stroke-label">粗细</span>
                <input 
                  type="range" 
                  class="canvas-stroke-slider"
                  v-model="strokeWidth"
                  min="1" 
                  max="20"
                />
                <span class="stroke-value">{{ strokeWidth }}px</span>
              </div>
            </div>
          </div>
          
          <div class="canvas-tool-divider"></div>
          
          <!-- 操作控制组 -->
          <div class="canvas-tool-group">
            <div class="tool-group-label">操作</div>
            <div class="tool-group-buttons">
              <!-- 清空按钮 -->
              <button 
                class="canvas-tool-btn canvas-danger-btn"
                @click="clearCanvas"
                title="清空画布"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                  <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <div class="canvas-fullscreen-content">
          <div class="canvas-fullscreen-workspace">
            <!-- 纯白色背景，只有在显式开启网格时才显示网格 -->
            <div 
              v-if="showGrid" 
              class="canvas-grid-bg-improved"
              :style="{ 
                backgroundSize: `${gridSize}px ${gridSize}px`,
                '--grid-size': gridSize + 'px'
              }"
            ></div>
            <canvas 
              ref="fullscreenCanvas"
              class="canvas-drawing-area"
              @mousedown="startDrawing"
              @mousemove="draw"
              @mouseup="stopDrawing"
              @mouseleave="stopDrawing"
            ></canvas>
            
            <!-- 优化的欢迎提示 -->
            <div v-if="!hasDrawing" class="canvas-welcome-hint">
              <div class="welcome-icon-container">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                  <rect x="8" y="8" width="48" height="48" rx="6" stroke="currentColor" stroke-width="2"/>
                  <circle cx="20" cy="20" r="3" fill="currentColor"/>
                  <path d="M16 32L28 20L40 32L52 20" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="44" cy="44" r="2" fill="currentColor" opacity="0.6"/>
                  <circle cx="28" cy="44" r="1.5" fill="currentColor" opacity="0.4"/>
                </svg>
              </div>
              <h3 style="margin: 20px 0 12px 0; font-size: 18px; font-weight: 600; color: #1f2937;">开始创作</h3>
              <p style="margin: 0 0 16px 0; font-size: 15px; color: #6b7280; line-height: 1.5;">选择工具并在画布上绘制内容<br>支持形状、连线、文本等多种元素</p>
              <div style="margin-top: 20px; font-size: 13px; color: #9ca3af; display: flex; align-items: center; gap: 8px; justify-content: center;">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>
                </svg>
                <span>💡 提示：点击网格按钮可显示辅助网格</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import CanvasModal from './CanvasModal.vue';

const props = defineProps({
  canvasId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['delete', 'resize', 'select', 'deselect']);

const canvasBoard = ref<HTMLElement | null>(null);
const isSelected = ref(false);
const isResizing = ref(false);
const showResizeHandles = ref(false);

// 全屏画板状态
const showFullscreen = ref(false);
const fullscreenCanvas = ref<HTMLCanvasElement | null>(null);
const currentTool = ref('pen');
const currentColor = ref('#1890ff');
const strokeWidth = ref(3);
const showColorPicker = ref(false);
const hasDrawing = ref(false);
const isDrawing = ref(false);
const lastX = ref(0);
const lastY = ref(0);

// 画板设置
const showGrid = ref(false);
const gridSize = ref(20);
const gridStyle = ref('dot'); // 'dot' | 'line'

// 拖拽状态
const resizeState = ref({
  startX: 0,
  startY: 0,
  startWidth: 0,
  startHeight: 0,
  direction: ''
});

// 处理点击事件
let clickTimer: NodeJS.Timeout | null = null;

const handleClick = (e: Event) => {
  e.preventDefault();
  e.stopPropagation();
  
  // 如果已经有点击定时器，说明是双击
  if (clickTimer) {
    clearTimeout(clickTimer);
    clickTimer = null;
    handleDoubleClick();
  } else {
    // 单击选中，设置延迟以区分双击
    clickTimer = setTimeout(() => {
      selectCanvas();
      clickTimer = null;
    }, 200);
  }
};

const handleDoubleClick = () => {
  console.log('[EmbeddedCanvas] 双击进入全屏编辑');
  
  // 保存当前滚动位置
  const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
  const currentScrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
  
  // 保存编辑器光标位置
  const editorState = saveEditorState();
  
  // 保存所有状态到 sessionStorage
  sessionStorage.setItem('canvasReturnState', JSON.stringify({
    scroll: {
      top: currentScrollTop,
      left: currentScrollLeft
    },
    editor: editorState,
    timestamp: Date.now()
  }));
  
  // 构建返回URL，包含当前完整路径和查询参数
  const currentPath = window.location.pathname + window.location.search + window.location.hash;
  const editUrl = `/canvas/${props.canvasId}/edit?returnTo=${encodeURIComponent(currentPath)}`;
  
  // 使用router跳转而不是window.location，避免页面刷新
  // 由于是动态挂载的组件，通过window对象获取Vue应用的router
  if (window.__VUE_APP_ROUTER__) {
    window.__VUE_APP_ROUTER__.push(editUrl);
  } else {
    // 降级方案：仍使用location跳转，但会保存滚动位置用于返回时恢复
    window.location.href = editUrl;
  }
};

// 保存编辑器状态
const saveEditorState = () => {
  try {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      console.log('[EmbeddedCanvas] 没有选择范围，跳过编辑器状态保存');
      return null;
    }
    
    const range = selection.getRangeAt(0);
    const container = range.startContainer;
    
    // 检查光标是否在可编辑区域内
    let editableParent = container.nodeType === Node.TEXT_NODE ? container.parentElement : container as Element;
    while (editableParent && !editableParent.matches('[contenteditable="true"], .editable-content')) {
      editableParent = editableParent.parentElement;
    }
    
    if (!editableParent) {
      console.log('[EmbeddedCanvas] 光标不在可编辑区域内，跳过状态保存');
      return null;
    }
    
    // 只保存文本节点的位置信息
    if (container.nodeType === Node.TEXT_NODE && container.parentElement) {
      // 找到最近的段落或可编辑元素
      let parentParagraph = container.parentElement;
      while (parentParagraph && !parentParagraph.matches('p, div[contenteditable], .editable-content')) {
        parentParagraph = parentParagraph.parentElement;
      }
      
      if (parentParagraph) {
        // 创建一个临时标记来唯一标识位置
        const markerId = `cursor-marker-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
        const marker = document.createElement('span');
        marker.id = markerId;
        marker.style.display = 'none';
        marker.setAttribute('data-cursor-marker', 'true');
        marker.setAttribute('data-temp-marker', 'true'); // 标记为临时元素
        
        try {
          const markerRange = range.cloneRange();
          markerRange.insertNode(marker);
          
          console.log('[EmbeddedCanvas] 保存编辑器光标位置，标记ID:', markerId);
          
          return {
            markerId: markerId,
            offset: range.startOffset,
            containerText: container.textContent?.substring(0, 50) || '', // 保存部分文本用于验证
            paragraphIndex: Array.from(document.querySelectorAll('p, div[contenteditable]')).indexOf(parentParagraph),
            // 额外保存一些上下文信息用于验证
            paragraphText: parentParagraph.textContent?.substring(0, 100) || ''
          };
        } catch (error) {
          console.warn('[EmbeddedCanvas] 插入光标标记失败:', error);
          // 清理失败的标记
          if (marker.parentNode) {
            marker.parentNode.removeChild(marker);
          }
          return null;
        }
      }
    }
    
    console.log('[EmbeddedCanvas] 无法保存编辑器状态：不是有效的文本光标位置');
    return null;
  } catch (error) {
    console.error('[EmbeddedCanvas] 保存编辑器状态失败:', error);
    return null;
  }
};

const selectCanvas = () => {
  isSelected.value = true;
  emit('select', props.canvasId);
};

const deselectCanvas = () => {
  isSelected.value = false;
  emit('deselect', props.canvasId);
};

const handleDelete = () => {
  if (confirm('确定要删除这个画板吗？')) {
    emit('delete', props.canvasId);
  }
};

// 拖拽调整大小
const handleResizeStart = (e: MouseEvent) => {
  if (!canvasBoard.value) return;
  
  e.preventDefault();
  e.stopPropagation();
  
  const direction = (e.target as HTMLElement).dataset.direction || '';
  
  isResizing.value = true;
  resizeState.value = {
    startX: e.clientX,
    startY: e.clientY,
    startWidth: canvasBoard.value.offsetWidth,
    startHeight: canvasBoard.value.offsetHeight,
    direction
  };
  
  document.body.style.cursor = getResizeCursor(direction);
  document.body.style.userSelect = 'none';
  document.body.classList.add('canvas-resizing');
  
  // 添加全局鼠标事件监听
  document.addEventListener('mousemove', handleResizeMove);
  document.addEventListener('mouseup', handleResizeEnd);
};

const handleResizeMove = (e: MouseEvent) => {
  if (!isResizing.value || !canvasBoard.value) return;
  
  const { startX, startY, startWidth, startHeight, direction } = resizeState.value;
  const deltaX = e.clientX - startX;
  const deltaY = e.clientY - startY;
  
  let newWidth = startWidth;
  let newHeight = startHeight;
  
  // 根据拖拽方向计算新尺寸
  switch (direction) {
    case 'se': // 右下角
      newWidth = startWidth + deltaX;
      newHeight = startHeight + deltaY;
      break;
    case 'sw': // 左下角
      newWidth = startWidth - deltaX;
      newHeight = startHeight + deltaY;
      break;
    case 'ne': // 右上角
      newWidth = startWidth + deltaX;
      newHeight = startHeight - deltaY;
      break;
    case 'nw': // 左上角
      newWidth = startWidth - deltaX;
      newHeight = startHeight - deltaY;
      break;
    case 'e': // 右边
      newWidth = startWidth + deltaX;
      break;
    case 'w': // 左边
      newWidth = startWidth - deltaX;
      break;
    case 's': // 下边
      newHeight = startHeight + deltaY;
      break;
    case 'n': // 上边
      newHeight = startHeight - deltaY;
      break;
  }
  
  // 设置最小尺寸限制
  newWidth = Math.max(200, newWidth);
  newHeight = Math.max(150, newHeight);
  
  // 设置最大尺寸限制（不超过父容器）
  const wrapper = canvasBoard.value.closest('.embedded-canvas-wrapper') as HTMLElement;
  if (wrapper) {
    const maxWidth = wrapper.offsetWidth - 20; // 留一些边距
    newWidth = Math.min(maxWidth, newWidth);
  }
  
  // 应用新尺寸
  canvasBoard.value.style.width = newWidth + 'px';
  canvasBoard.value.style.height = newHeight + 'px';
  
  // 通知父组件尺寸改变
  emit('resize', {
    canvasId: props.canvasId,
    width: newWidth,
    height: newHeight
  });
};

const handleResizeEnd = () => {
  if (!isResizing.value) return;
  
  isResizing.value = false;
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
  document.body.classList.remove('canvas-resizing');
  
  // 移除全局鼠标事件监听
  document.removeEventListener('mousemove', handleResizeMove);
  document.removeEventListener('mouseup', handleResizeEnd);
};

const getResizeCursor = (direction: string): string => {
  const cursors: { [key: string]: string } = {
    'nw': 'nw-resize',
    'ne': 'ne-resize',
    'sw': 'sw-resize',
    'se': 'se-resize',
    'n': 'n-resize',
    's': 's-resize',
    'e': 'e-resize',
    'w': 'w-resize'
  };
  return cursors[direction] || 'default';
};

// 处理全局点击事件，点击画板外部时取消选中
const handleGlobalClick = (e: Event) => {
  const target = e.target as HTMLElement;
  if (!target.closest(`[data-canvas-id="${props.canvasId}"]`)) {
    deselectCanvas();
  }
};

onMounted(() => {
  console.log(`[EmbeddedCanvas] 组件已挂载，canvasId: ${props.canvasId}`);
  document.addEventListener('click', handleGlobalClick);
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  document.removeEventListener('click', handleGlobalClick);
  document.removeEventListener('mousemove', handleResizeMove);
  document.removeEventListener('mouseup', handleResizeEnd);
  window.removeEventListener('resize', handleResize);
  
  // 清理定时器
  if (clickTimer) {
    clearTimeout(clickTimer);
  }
});

// 暴露方法给父组件
defineExpose({
  selectCanvas,
  deselectCanvas
});

// 初始化画布
const initializeCanvas = () => {
  if (!fullscreenCanvas.value) return;
  
  const canvas = fullscreenCanvas.value;
  const rect = canvas.parentElement?.getBoundingClientRect();
  
  if (rect) {
    canvas.width = rect.width;
    canvas.height = rect.height;
  }
  
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = currentColor.value;
    ctx.lineWidth = strokeWidth.value;
  }
};

// 绘图相关方法
const startDrawing = (e: MouseEvent) => {
  if (currentTool.value === 'pen' || currentTool.value === 'eraser') {
    isDrawing.value = true;
    const rect = fullscreenCanvas.value?.getBoundingClientRect();
    if (rect) {
      lastX.value = e.clientX - rect.left;
      lastY.value = e.clientY - rect.top;
    }
  }
};

const draw = (e: MouseEvent) => {
  if (!isDrawing.value || !fullscreenCanvas.value) return;
  
  const canvas = fullscreenCanvas.value;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  const rect = canvas.getBoundingClientRect();
  const currentX = e.clientX - rect.left;
  const currentY = e.clientY - rect.top;
  
  ctx.beginPath();
  ctx.moveTo(lastX.value, lastY.value);
  ctx.lineTo(currentX, currentY);
  
  if (currentTool.value === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.lineWidth = strokeWidth.value * 2; // 橡皮擦更大一些
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = currentColor.value;
    ctx.lineWidth = strokeWidth.value;
  }
  
  ctx.stroke();
  
  lastX.value = currentX;
  lastY.value = currentY;
  
  hasDrawing.value = true;
};

const stopDrawing = () => {
  isDrawing.value = false;
};

// 工具相关方法
const setTool = (tool: string) => {
  currentTool.value = tool;
};

const clearCanvas = () => {
  if (confirm('确定要清空画布吗？')) {
    const canvas = fullscreenCanvas.value;
    const ctx = canvas?.getContext('2d');
    if (ctx && canvas) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      hasDrawing.value = false;
    }
  }
};

const saveCanvas = () => {
  console.log('保存画板:', props.canvasId);
  // TODO: 实现保存功能，可以将画布数据保存到后端
  closeFullscreen();
};

const closeFullscreen = () => {
  showFullscreen.value = false;
};

const handleBackdropClick = () => {
  closeFullscreen();
};

// 处理窗口大小变化
const handleResize = () => {
  if (showFullscreen.value && fullscreenCanvas.value) {
    initializeCanvas();
  }
};

// 网格控制方法
const toggleGrid = () => {
  showGrid.value = !showGrid.value;
};

// 添加颜色选择功能
const presetColors = ref([
  '#1890ff', '#f5222d', '#fa541c', '#fadb14', 
  '#52c41a', '#13c2c2', '#722ed1', '#eb2f96',
  '#000000', '#262626', '#595959', '#8c8c8c',
  '#bfbfbf', '#d9d9d9', '#f0f0f0', '#ffffff'
]);

const selectColor = (color: string) => {
  currentColor.value = color;
  showColorPicker.value = false; // 选择后关闭面板
};
</script>

<style scoped>
/* 组件内的样式已经在global.css中定义 */
</style> 