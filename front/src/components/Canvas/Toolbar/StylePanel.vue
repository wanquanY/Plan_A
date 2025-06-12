<template>
  <div class="style-panel">
    <a-divider type="vertical" />
    
    <!-- 颜色控制 -->
    <div class="style-group">
      <a-dropdown :trigger="['click']">
        <a-button class="color-button">
          <div class="color-preview" :style="{ backgroundColor: strokeColor }"></div>
          <DownOutlined />
        </a-button>
        <template #overlay>
          <div class="color-palette">
            <div 
              v-for="color in colorPresets"
              :key="color"
              class="color-swatch"
              :style="{ backgroundColor: color }"
              @click="setStrokeColor(color)"
            ></div>
          </div>
        </template>
      </a-dropdown>
      
      <a-dropdown :trigger="['click']">
        <a-button class="color-button">
          <div class="color-preview fill" :style="{ backgroundColor: fillColor }"></div>
          <BgColorsOutlined />
        </a-button>
        <template #overlay>
          <div class="color-palette">
            <div 
              v-for="color in colorPresets"
              :key="color"
              class="color-swatch"
              :style="{ backgroundColor: color }"
              @click="setFillColor(color)"
            ></div>
          </div>
        </template>
      </a-dropdown>
    </div>

    <!-- 线条粗细 -->
    <div class="style-group">
      <a-dropdown :trigger="['click']">
        <a-button>
          <LineHeightOutlined />
          {{ strokeWidth }}px
        </a-button>
        <template #overlay>
          <div class="stroke-options">
            <div 
              v-for="width in strokeWidthPresets"
              :key="width"
              class="stroke-option"
              @click="setStrokeWidth(width)"
            >
              <div class="stroke-preview" :style="{ height: `${width}px` }"></div>
              <span>{{ width }}px</span>
            </div>
          </div>
        </template>
      </a-dropdown>
    </div>

    <!-- 透明度 -->
    <div class="style-group">
      <span class="style-label">透明度</span>
      <a-slider 
        v-model:value="opacity"
        :min="0"
        :max="100"
        :step="5"
        style="width: 80px;"
        @change="setOpacity"
      />
    </div>

    <!-- 字体控制（文本元素专用） -->
    <div v-if="isTextElement" class="style-group">
      <a-select v-model:value="fontSize" style="width: 70px;" @change="setFontSize">
        <a-select-option v-for="size in fontSizePresets" :key="size" :value="size">
          {{ size }}px
        </a-select-option>
      </a-select>
      
      <a-button 
        :type="isBold ? 'primary' : 'default'"
        @click="toggleBold"
        title="粗体"
      >
        <template #icon><BoldOutlined /></template>
      </a-button>
      
      <a-button 
        :type="isItalic ? 'primary' : 'default'"
        @click="toggleItalic"
        title="斜体"
      >
        <template #icon><ItalicOutlined /></template>
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { 
  Divider as ADivider, 
  Button as AButton, 
  Dropdown as ADropdown,
  Slider as ASlider,
  Select as ASelect,
  SelectOption as ASelectOption
} from 'ant-design-vue'
import {
  DownOutlined,
  BgColorsOutlined,
  LineHeightOutlined,
  BoldOutlined,
  ItalicOutlined
} from '@ant-design/icons-vue'
import { useCanvasStore } from '../stores/canvasStore'

const canvasStore = useCanvasStore()
const { selectedElements } = canvasStore

// 样式状态
const strokeColor = ref('#000000')
const fillColor = ref('#ffffff')
const strokeWidth = ref(1)
const opacity = ref(100)
const fontSize = ref(16)
const isBold = ref(false)
const isItalic = ref(false)

// 预设值
const colorPresets = [
  '#000000', '#ffffff', '#ff0000', '#00ff00', '#0000ff',
  '#ffff00', '#ff00ff', '#00ffff', '#ffa500', '#800080',
  '#808080', '#c0c0c0', '#800000', '#008000', '#000080'
]

const strokeWidthPresets = [1, 2, 3, 4, 5, 8, 10, 12, 16, 20]
const fontSizePresets = [12, 14, 16, 18, 20, 24, 28, 32, 36, 48]

// 计算属性
const isTextElement = computed(() => {
  return selectedElements.some(el => el.type === 'text')
})

// 监听选中元素变化，更新样式面板
watch(selectedElements, (newElements) => {
  if (newElements.length > 0) {
    const firstElement = newElements[0]
    strokeColor.value = firstElement.style?.stroke || '#000000'
    fillColor.value = firstElement.style?.fill || '#ffffff'
    strokeWidth.value = firstElement.style?.strokeWidth || 1
    opacity.value = (firstElement.style?.opacity || 1) * 100
    
    if (firstElement.type === 'text') {
      fontSize.value = firstElement.style?.fontSize || 16
      isBold.value = firstElement.style?.fontWeight === 'bold'
      isItalic.value = firstElement.style?.fontStyle === 'italic'
    }
  }
}, { immediate: true })

// 样式设置方法
const setStrokeColor = (color: string) => {
  strokeColor.value = color
  canvasStore.updateSelectedElementsStyle({ stroke: color })
}

const setFillColor = (color: string) => {
  fillColor.value = color
  canvasStore.updateSelectedElementsStyle({ fill: color })
}

const setStrokeWidth = (width: number) => {
  strokeWidth.value = width
  canvasStore.updateSelectedElementsStyle({ strokeWidth: width })
}

const setOpacity = (value: number) => {
  const opacityValue = value / 100
  canvasStore.updateSelectedElementsStyle({ opacity: opacityValue })
}

const setFontSize = (size: number) => {
  fontSize.value = size
  canvasStore.updateSelectedElementsStyle({ fontSize: size })
}

const toggleBold = () => {
  isBold.value = !isBold.value
  canvasStore.updateSelectedElementsStyle({ 
    fontWeight: isBold.value ? 'bold' : 'normal' 
  })
}

const toggleItalic = () => {
  isItalic.value = !isItalic.value
  canvasStore.updateSelectedElementsStyle({ 
    fontStyle: isItalic.value ? 'italic' : 'normal' 
  })
}
</script>

<style scoped>
.style-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 12px;
}

.style-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.style-label {
  font-size: 12px;
  color: #666;
}

.color-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
}

.color-preview {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  border: 1px solid #d9d9d9;
}

.color-preview.fill {
  border: 2px solid #666;
  border-style: dashed;
}

.color-palette {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  padding: 8px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #d9d9d9;
  transition: transform 0.2s;
}

.color-swatch:hover {
  transform: scale(1.1);
}

.stroke-options {
  padding: 8px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  min-width: 120px;
}

.stroke-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.stroke-option:hover {
  background-color: #f5f5f5;
}

.stroke-preview {
  width: 40px;
  background-color: #333;
  border-radius: 1px;
}
</style> 