<template>
  <div class="properties-panel">
    <div class="panel-header">
      <h3>属性</h3>
    </div>
    
    <!-- 没有选中元素的状态 -->
    <div v-if="!hasSelection" class="no-selection">
      <div class="empty-icon">🎨</div>
      <p>选择一个元素来编辑属性</p>
    </div>
    
    <!-- 选中了元素的属性编辑 -->
    <div v-else class="properties-content">
      <!-- 多选时的提示 -->
      <div v-if="isMultiSelection" class="multi-selection-info">
        <InfoCircleOutlined />
        <span>已选中 {{ selectedElements.length }} 个元素</span>
      </div>
      
      <!-- 基本信息 -->
      <div class="property-section">
        <h4>基本信息</h4>
        <div class="property-grid">
          <div class="property-item">
            <label>位置 X</label>
            <a-input-number 
              v-model:value="position.x" 
              size="small"
              @change="updatePosition"
              :disabled="isLocked"
            />
          </div>
          <div class="property-item">
            <label>位置 Y</label>
            <a-input-number 
              v-model:value="position.y" 
              size="small"
              @change="updatePosition"
              :disabled="isLocked"
            />
          </div>
          <div class="property-item">
            <label>宽度</label>
            <a-input-number 
              v-model:value="size.width" 
              size="small"
              :min="1"
              @change="updateSize"
              :disabled="isLocked"
            />
          </div>
          <div class="property-item">
            <label>高度</label>
            <a-input-number 
              v-model:value="size.height" 
              size="small"
              :min="1"
              @change="updateSize"
              :disabled="isLocked"
            />
          </div>
          <div class="property-item full-width">
            <label>旋转角度</label>
            <a-slider 
              v-model:value="rotation" 
              :min="-180" 
              :max="180"
              :marks="{ 0: '0°', 90: '90°', 180: '180°', '-90': '-90°' }"
              @change="updateRotation"
              :disabled="isLocked"
            />
          </div>
        </div>
      </div>
      
      <!-- 样式属性 -->
      <div class="property-section">
        <h4>样式</h4>
        <div class="style-controls">
          <!-- 填充颜色 -->
          <div class="property-item">
            <label>填充颜色</label>
            <div class="color-input">
              <div 
                class="color-preview" 
                :style="{ backgroundColor: style.fill }"
                @click="showFillColorPicker = true"
              ></div>
              <a-input 
                v-model:value="style.fill" 
                size="small"
                @change="updateStyle"
                :disabled="isLocked"
              />
            </div>
          </div>
          
          <!-- 边框颜色 -->
          <div class="property-item">
            <label>边框颜色</label>
            <div class="color-input">
              <div 
                class="color-preview" 
                :style="{ backgroundColor: style.stroke }"
                @click="showStrokeColorPicker = true"
              ></div>
              <a-input 
                v-model:value="style.stroke" 
                size="small"
                @change="updateStyle"
                :disabled="isLocked"
              />
            </div>
          </div>
          
          <!-- 边框宽度 -->
          <div class="property-item">
            <label>边框宽度</label>
            <a-input-number 
              v-model:value="style.strokeWidth" 
              size="small"
              :min="0"
              :max="20"
              @change="updateStyle"
              :disabled="isLocked"
            />
          </div>
          
          <!-- 透明度 -->
          <div class="property-item full-width">
            <label>透明度 ({{ Math.round((style.opacity || 1) * 100) }}%)</label>
            <a-slider 
              v-model:value="opacityValue" 
              :min="0" 
              :max="100"
              @change="updateOpacity"
              :disabled="isLocked"
            />
          </div>
        </div>
      </div>
      
      <!-- 文本属性 (仅文本元素) -->
      <div v-if="isTextElement" class="property-section">
        <h4>文本</h4>
        <div class="text-controls">
          <div class="property-item full-width">
            <label>文本内容</label>
            <a-textarea 
              v-model:value="textContent" 
              size="small"
              :rows="3"
              @change="updateTextContent"
              :disabled="isLocked"
            />
          </div>
          
          <div class="property-item">
            <label>字体大小</label>
            <a-input-number 
              v-model:value="style.fontSize" 
              size="small"
              :min="8"
              :max="100"
              @change="updateStyle"
              :disabled="isLocked"
            />
          </div>
          
          <div class="property-item">
            <label>字体</label>
            <a-select 
              v-model:value="style.fontFamily" 
              size="small"
              @change="updateStyle"
              :disabled="isLocked"
            >
              <a-select-option value="Arial">Arial</a-select-option>
              <a-select-option value="SimHei">黑体</a-select-option>
              <a-select-option value="SimSun">宋体</a-select-option>
              <a-select-option value="Microsoft YaHei">微软雅黑</a-select-option>
            </a-select>
          </div>
          
          <div class="property-item full-width">
            <label>对齐方式</label>
            <a-radio-group 
              v-model:value="style.textAlign" 
              size="small"
              @change="updateStyle"
              :disabled="isLocked"
            >
              <a-radio-button value="left">左对齐</a-radio-button>
              <a-radio-button value="center">居中</a-radio-button>
              <a-radio-button value="right">右对齐</a-radio-button>
            </a-radio-group>
          </div>
        </div>
      </div>
      
      <!-- 图层操作 -->
      <div class="property-section">
        <h4>图层操作</h4>
        <div class="layer-actions">
          <a-button-group size="small">
            <a-button @click="bringToFront" :disabled="isLocked">置于顶层</a-button>
            <a-button @click="sendToBack" :disabled="isLocked">置于底层</a-button>
          </a-button-group>
          
          <a-button-group size="small" style="margin-top: 8px;">
            <a-button @click="duplicateSelected">复制</a-button>
            <a-button @click="deleteSelected" danger>删除</a-button>
          </a-button-group>
          
          <div class="property-item" style="margin-top: 12px;">
            <a-checkbox 
              v-model:checked="visibility" 
              @change="updateVisibility"
            >
              显示图层
            </a-checkbox>
          </div>
          
          <div class="property-item">
            <a-checkbox 
              v-model:checked="locked" 
              @change="updateLocked"
            >
              锁定图层
            </a-checkbox>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 颜色选择器 -->
    <a-modal 
      v-model:open="showFillColorPicker" 
      title="选择填充颜色" 
      :footer="null"
      width="300px"
    >
      <div class="color-picker">
        <div class="color-presets">
          <div 
            v-for="color in colorPresets"
            :key="color"
            class="color-swatch"
            :style="{ backgroundColor: color }"
            @click="selectFillColor(color)"
          ></div>
        </div>
      </div>
    </a-modal>
    
    <a-modal 
      v-model:open="showStrokeColorPicker" 
      title="选择边框颜色" 
      :footer="null"
      width="300px"
    >
      <div class="color-picker">
        <div class="color-presets">
          <div 
            v-for="color in colorPresets"
            :key="color"
            class="color-swatch"
            :style="{ backgroundColor: color }"
            @click="selectStrokeColor(color)"
          ></div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { 
  InputNumber as AInputNumber,
  Input as AInput,
  Textarea as ATextarea,
  Slider as ASlider,
  Select as ASelect,
  SelectOption as ASelectOption,
  RadioGroup as ARadioGroup,
  RadioButton as ARadioButton,
  Button as AButton,
  ButtonGroup as AButtonGroup,
  Checkbox as ACheckbox,
  Modal as AModal
} from 'ant-design-vue'
import { InfoCircleOutlined } from '@ant-design/icons-vue'
import { useCanvasStore } from '../stores/canvasStore'
import { ElementType } from '../types/canvas'

// 状态管理
const canvasStore = useCanvasStore()
const { hasSelection, isMultiSelection, selectedElements } = canvasStore

// 组件状态
const showFillColorPicker = ref(false)
const showStrokeColorPicker = ref(false)

// 颜色预设
const colorPresets = [
  '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
  '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080',
  '#008000', '#FFC0CB', '#A52A2A', '#808080', '#000080',
  '#8B4513', '#FF1493', '#1E90FF', '#32CD32', '#FFD700'
]

// 响应式属性
const position = ref({ x: 0, y: 0 })
const size = ref({ width: 0, height: 0 })
const rotation = ref(0)
const style = ref({
  fill: '#ffffff',
  stroke: '#000000',
  strokeWidth: 1,
  opacity: 1,
  fontSize: 16,
  fontFamily: 'Arial',
  textAlign: 'left' as 'left' | 'center' | 'right'
})
const textContent = ref('')
const visibility = ref(true)
const locked = ref(false)

// 计算属性
const opacityValue = computed({
  get: () => Math.round((style.value.opacity || 1) * 100),
  set: (value) => {
    style.value.opacity = value / 100
  }
})

const isTextElement = computed(() => {
  if (!hasSelection || selectedElements.length !== 1) return false
  return selectedElements[0].type === ElementType.TEXT
})

const isLocked = computed(() => {
  return selectedElements.some(element => element.locked)
})

// 监听选中元素变化，更新属性值
watch(selectedElements, (elements) => {
  if (elements.length === 0) return
  
  if (elements.length === 1) {
    const element = elements[0]
    position.value = { x: element.x, y: element.y }
    size.value = { width: element.width, height: element.height }
    rotation.value = element.rotation || 0
    style.value = {
      fill: element.style.fill || '#ffffff',
      stroke: element.style.stroke || '#000000',
      strokeWidth: element.style.strokeWidth || 1,
      opacity: element.style.opacity || 1,
      fontSize: element.style.fontSize || 16,
      fontFamily: element.style.fontFamily || 'Arial',
      textAlign: element.style.textAlign || 'left'
    }
    textContent.value = element.data?.text || ''
    visibility.value = element.visible
    locked.value = element.locked
  } else {
    // 多选时显示公共属性
    const firstElement = elements[0]
    visibility.value = elements.every(el => el.visible)
    locked.value = elements.every(el => el.locked)
  }
}, { immediate: true, deep: true })

// 更新方法
const updatePosition = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.updateElement(element.id, {
        x: position.value.x,
        y: position.value.y
      })
    }
  })
}

const updateSize = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.updateElement(element.id, {
        width: size.value.width,
        height: size.value.height
      })
    }
  })
}

const updateRotation = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.updateElement(element.id, {
        rotation: rotation.value
      })
    }
  })
}

const updateStyle = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.updateElement(element.id, {
        style: { ...element.style, ...style.value }
      })
    }
  })
}

const updateOpacity = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.updateElement(element.id, {
        style: { ...element.style, opacity: style.value.opacity }
      })
    }
  })
}

const updateTextContent = () => {
  selectedElements.forEach(element => {
    if (!element.locked && element.type === ElementType.TEXT) {
      canvasStore.updateElement(element.id, {
        data: { ...element.data, text: textContent.value }
      })
    }
  })
}

const updateVisibility = () => {
  selectedElements.forEach(element => {
    canvasStore.updateElement(element.id, {
      visible: visibility.value
    })
  })
}

const updateLocked = () => {
  selectedElements.forEach(element => {
    canvasStore.updateElement(element.id, {
      locked: locked.value
    })
  })
}

// 图层操作
const bringToFront = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.bringToFront(element.id)
    }
  })
}

const sendToBack = () => {
  selectedElements.forEach(element => {
    if (!element.locked) {
      canvasStore.sendToBack(element.id)
    }
  })
}

const duplicateSelected = () => {
  selectedElements.forEach(element => {
    canvasStore.duplicateElement(element.id)
  })
}

const deleteSelected = () => {
  selectedElements.forEach(element => {
    canvasStore.removeElement(element.id)
  })
}

// 颜色选择
const selectFillColor = (color: string) => {
  style.value.fill = color
  updateStyle()
  showFillColorPicker.value = false
}

const selectStrokeColor = (color: string) => {
  style.value.stroke = color
  updateStyle()
  showStrokeColorPicker.value = false
}
</script>

<style scoped>
.properties-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #8c8c8c;
  height: 200px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.no-selection p {
  margin: 0;
  font-size: 14px;
}

.properties-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.multi-selection-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f6ffed;
  border-bottom: 1px solid #f0f0f0;
  color: #52c41a;
  font-size: 12px;
}

.property-section {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px;
}

.property-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}

.property-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.property-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.property-item.full-width {
  grid-column: 1 / -1;
}

.property-item label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.style-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.color-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-preview {
  width: 24px;
  height: 24px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
}

.text-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.layer-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.color-picker {
  padding: 16px;
}

.color-presets {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.color-swatch {
  width: 32px;
  height: 32px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s;
}

.color-swatch:hover {
  transform: scale(1.1);
}

/* 滚动条样式 */
.properties-content::-webkit-scrollbar {
  width: 6px;
}

.properties-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.properties-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.properties-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style> 