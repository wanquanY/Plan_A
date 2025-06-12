<template>
  <div class="right-panel">
    <!-- 面板标签切换 -->
    <div class="panel-tabs">
      <button 
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="setActiveTab(tab.id)"
        :title="tab.name"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-name">{{ tab.name }}</span>
      </button>
    </div>
    
    <!-- 面板内容 -->
    <div class="panel-content">
      <!-- 属性面板 -->
      <div v-if="activeTab === 'properties'" class="property-panel">
        <div v-if="selectedElements.length === 0" class="empty-state">
          <div class="empty-icon">🎯</div>
          <p>请选择要编辑的元素</p>
        </div>
        
        <div v-else class="property-sections">
          <!-- 基本属性 -->
          <div class="property-section">
            <h4 class="section-title">基本属性</h4>
            <div class="property-item">
              <label>位置</label>
              <div class="input-group">
                <input 
                  type="number" 
                  v-model="elementProperties.x" 
                  placeholder="X"
                  @input="updateProperty('x', $event.target.value)"
                />
                <input 
                  type="number" 
                  v-model="elementProperties.y" 
                  placeholder="Y"
                  @input="updateProperty('y', $event.target.value)"
                />
              </div>
            </div>
            
            <div class="property-item">
              <label>尺寸</label>
              <div class="input-group">
                <input 
                  type="number" 
                  v-model="elementProperties.width" 
                  placeholder="宽度"
                  @input="updateProperty('width', $event.target.value)"
                />
                <input 
                  type="number" 
                  v-model="elementProperties.height" 
                  placeholder="高度"
                  @input="updateProperty('height', $event.target.value)"
                />
              </div>
            </div>
            
            <div class="property-item">
              <label>旋转角度</label>
              <input 
                type="number" 
                v-model="elementProperties.rotation" 
                placeholder="0"
                @input="updateProperty('rotation', $event.target.value)"
              />
            </div>
          </div>
          
          <!-- 样式属性 -->
          <div class="property-section">
            <h4 class="section-title">样式</h4>
            <div class="property-item">
              <label>填充色</label>
              <div class="color-input">
                <input 
                  type="color" 
                  v-model="elementProperties.fill" 
                  @input="updateProperty('fill', $event.target.value)"
                />
                <input 
                  type="text" 
                  v-model="elementProperties.fill" 
                  @input="updateProperty('fill', $event.target.value)"
                />
              </div>
            </div>
            
            <div class="property-item">
              <label>边框色</label>
              <div class="color-input">
                <input 
                  type="color" 
                  v-model="elementProperties.stroke" 
                  @input="updateProperty('stroke', $event.target.value)"
                />
                <input 
                  type="text" 
                  v-model="elementProperties.stroke" 
                  @input="updateProperty('stroke', $event.target.value)"
                />
              </div>
            </div>
            
            <div class="property-item">
              <label>边框宽度</label>
              <input 
                type="number" 
                v-model="elementProperties.strokeWidth" 
                min="0"
                @input="updateProperty('strokeWidth', $event.target.value)"
              />
            </div>
            
            <div class="property-item">
              <label>透明度</label>
              <input 
                type="range" 
                v-model="elementProperties.opacity" 
                min="0" 
                max="1" 
                step="0.1"
                @input="updateProperty('opacity', $event.target.value)"
              />
              <span class="opacity-value">{{ Math.round(elementProperties.opacity * 100) }}%</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 图层面板 -->
      <div v-else-if="activeTab === 'layers'" class="layer-panel">
        <div class="layer-header">
          <h4>图层</h4>
          <div class="layer-actions">
            <button class="layer-btn" @click="addLayer" title="添加图层">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <path d="M7 1v12M1 7h12"/>
              </svg>
            </button>
            <button class="layer-btn" @click="deleteLayer" title="删除图层">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <path d="M2 2l10 10M12 2L2 12"/>
              </svg>
            </button>
          </div>
        </div>
        
        <div class="layer-list">
          <div 
            v-for="layer in layers"
            :key="layer.id"
            class="layer-item"
            :class="{ active: layer.active }"
            @click="selectLayer(layer.id)"
          >
            <div class="layer-visibility">
              <button 
                class="visibility-btn"
                :class="{ hidden: !layer.visible }"
                @click.stop="toggleLayerVisibility(layer.id)"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                  <path v-if="layer.visible" d="M7 2C4 2 1.5 4.5 1 7c.5 2.5 3 5 6 5s5.5-2.5 6-5c-.5-2.5-3-5-6-5zm0 8a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm0-2a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/>
                  <path v-else d="M1 1l12 12M7 2C4 2 1.5 4.5 1 7l1.5 1.5"/>
                </svg>
              </button>
            </div>
            <div class="layer-info">
              <span class="layer-name">{{ layer.name }}</span>
              <span class="layer-count">{{ layer.elementCount }} 个元素</span>
            </div>
            <div class="layer-lock">
              <button 
                class="lock-btn"
                :class="{ locked: layer.locked }"
                @click.stop="toggleLayerLock(layer.id)"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                  <path v-if="layer.locked" d="M3 5V3.5C3 1.57 4.57 0 6 0s3 1.57 3 3.5V5h1v7H2V5h1zm1.5-1.5C4.5 2.67 5.17 2 6 2s1.5.67 1.5 1.5V5h-3V3.5z"/>
                  <path v-else d="M2 5h8v7H2V5zm2-1.5C4 2.67 4.67 2 5.5 2S7 2.67 7 3.5V4H4v-.5z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 历史面板 -->
      <div v-else-if="activeTab === 'history'" class="history-panel">
        <div class="history-header">
          <h4>历史记录</h4>
          <button class="clear-btn" @click="clearHistory" title="清空历史">清空</button>
        </div>
        
        <div class="history-list">
          <div 
            v-for="(action, index) in historyActions"
            :key="index"
            class="history-item"
            :class="{ active: index === currentHistoryIndex }"
            @click="jumpToHistory(index)"
          >
            <div class="action-icon">{{ getActionIcon(action.type) }}</div>
            <div class="action-info">
              <span class="action-name">{{ action.name }}</span>
              <span class="action-time">{{ formatTime(action.time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

// Props
const props = defineProps<{
  selectedElements: any[]
  canvasProperties: any
}>()

// Emits
const emit = defineEmits<{
  propertyChange: [properties: any]
  layerChange: [layerData: any]
}>()

// 状态
const activeTab = ref('properties')

// 标签数据
const tabs = [
  { id: 'properties', name: '属性', icon: '⚙️' },
  { id: 'layers', name: '图层', icon: '📚' },
  { id: 'history', name: '历史', icon: '🕐' }
]

// 元素属性
const elementProperties = ref({
  x: 0,
  y: 0,
  width: 100,
  height: 60,
  rotation: 0,
  fill: '#87CEEB',
  stroke: '#000000',
  strokeWidth: 1,
  opacity: 1
})

// 图层数据
const layers = ref([
  {
    id: 'layer-1',
    name: '图层 1',
    visible: true,
    locked: false,
    active: true,
    elementCount: 0
  }
])

// 历史记录
const historyActions = ref([
  { type: 'create', name: '创建画板', time: new Date() },
  { type: 'add', name: '添加矩形', time: new Date(Date.now() - 30000) },
  { type: 'move', name: '移动元素', time: new Date(Date.now() - 60000) }
])

const currentHistoryIndex = ref(0)

// 监听选中元素变化
watch(() => props.selectedElements, (newElements) => {
  if (newElements.length > 0) {
    // 更新属性面板显示
    const element = newElements[0]
    updateElementProperties(element)
  }
})

// 方法
const setActiveTab = (tabId: string) => {
  activeTab.value = tabId
}

const updateElementProperties = (element: any) => {
  // 这里应该从Konva元素中提取属性
  // 暂时使用模拟数据
  elementProperties.value = {
    x: element.x || 0,
    y: element.y || 0,
    width: element.width || 100,
    height: element.height || 60,
    rotation: element.rotation || 0,
    fill: element.fill || '#87CEEB',
    stroke: element.stroke || '#000000',
    strokeWidth: element.strokeWidth || 1,
    opacity: element.opacity || 1
  }
}

const updateProperty = (property: string, value: any) => {
  const numericProperties = ['x', 'y', 'width', 'height', 'rotation', 'strokeWidth', 'opacity']
  const finalValue = numericProperties.includes(property) ? Number(value) : value
  
  emit('propertyChange', {
    property,
    value: finalValue,
    elements: props.selectedElements
  })
}

const addLayer = () => {
  const newLayer = {
    id: `layer-${Date.now()}`,
    name: `图层 ${layers.value.length + 1}`,
    visible: true,
    locked: false,
    active: false,
    elementCount: 0
  }
  
  layers.value.forEach(layer => layer.active = false)
  newLayer.active = true
  layers.value.push(newLayer)
  
  emit('layerChange', { type: 'add', layer: newLayer })
}

const deleteLayer = () => {
  const activeLayerIndex = layers.value.findIndex(layer => layer.active)
  if (activeLayerIndex > -1 && layers.value.length > 1) {
    layers.value.splice(activeLayerIndex, 1)
    
    // 激活第一个图层
    if (layers.value.length > 0) {
      layers.value[0].active = true
    }
    
    emit('layerChange', { type: 'delete', index: activeLayerIndex })
  }
}

const selectLayer = (layerId: string) => {
  layers.value.forEach(layer => {
    layer.active = layer.id === layerId
  })
  
  emit('layerChange', { type: 'select', layerId })
}

const toggleLayerVisibility = (layerId: string) => {
  const layer = layers.value.find(l => l.id === layerId)
  if (layer) {
    layer.visible = !layer.visible
    emit('layerChange', { type: 'visibility', layerId, visible: layer.visible })
  }
}

const toggleLayerLock = (layerId: string) => {
  const layer = layers.value.find(l => l.id === layerId)
  if (layer) {
    layer.locked = !layer.locked
    emit('layerChange', { type: 'lock', layerId, locked: layer.locked })
  }
}

const clearHistory = () => {
  historyActions.value = []
  currentHistoryIndex.value = -1
}

const jumpToHistory = (index: number) => {
  currentHistoryIndex.value = index
  console.log('跳转到历史记录:', index)
  // TODO: 实现历史跳转逻辑
}

const getActionIcon = (type: string) => {
  const icons = {
    create: '📄',
    add: '➕',
    move: '↔️',
    delete: '🗑️',
    edit: '✏️'
  }
  return icons[type as keyof typeof icons] || '📝'
}

const formatTime = (time: Date) => {
  return time.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}
</script>

<style scoped>
.right-panel {
  width: 280px;
  background-color: #fafbfc;
  border-left: 1px solid #e1e4e8;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid #e1e4e8;
  background-color: #ffffff;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 44px;
  border: none;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
  border-bottom: 2px solid transparent;
}

.tab-btn:hover {
  background-color: #f6f8fa;
  color: #24292f;
}

.tab-btn.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
  background-color: #ffffff;
}

.tab-icon {
  font-size: 14px;
}

.tab-name {
  font-size: 12px;
  font-weight: 500;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #656d76;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.property-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.property-section {
  border: 1px solid #e1e4e8;
  border-radius: 6px;
  padding: 16px;
  background-color: #ffffff;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #24292f;
  margin: 0 0 12px 0;
}

.property-item {
  margin-bottom: 12px;
}

.property-item:last-child {
  margin-bottom: 0;
}

.property-item label {
  display: block;
  font-size: 12px;
  color: #656d76;
  margin-bottom: 4px;
}

.property-item input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  font-size: 13px;
  background-color: #ffffff;
}

.property-item input:focus {
  outline: none;
  border-color: #1890ff;
}

.input-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.color-input {
  display: flex;
  gap: 8px;
}

.color-input input[type="color"] {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  cursor: pointer;
}

.color-input input[type="text"] {
  flex: 1;
}

.opacity-value {
  font-size: 12px;
  color: #656d76;
  margin-left: 8px;
}

.layer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.layer-header h4 {
  font-size: 14px;
  font-weight: 600;
  color: #24292f;
  margin: 0;
}

.layer-actions {
  display: flex;
  gap: 4px;
}

.layer-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.layer-btn:hover {
  background-color: #e1e4e8;
  color: #24292f;
}

.layer-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.layer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.layer-item:hover {
  background-color: #f6f8fa;
}

.layer-item.active {
  background-color: #e6f3ff;
  border: 1px solid #1890ff;
}

.layer-visibility,
.layer-lock {
  flex-shrink: 0;
}

.visibility-btn,
.lock-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 3px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.visibility-btn:hover,
.lock-btn:hover {
  background-color: #e1e4e8;
}

.visibility-btn.hidden,
.lock-btn.locked {
  color: #ff4d4f;
}

.layer-info {
  flex: 1;
  min-width: 0;
}

.layer-name {
  display: block;
  font-size: 13px;
  color: #24292f;
  font-weight: 500;
}

.layer-count {
  display: block;
  font-size: 11px;
  color: #656d76;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.history-header h4 {
  font-size: 14px;
  font-weight: 600;
  color: #24292f;
  margin: 0;
}

.clear-btn {
  font-size: 12px;
  color: #656d76;
  border: none;
  background: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.clear-btn:hover {
  background-color: #f6f8fa;
  color: #24292f;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.history-item:hover {
  background-color: #f6f8fa;
}

.history-item.active {
  background-color: #e6f3ff;
  border: 1px solid #1890ff;
}

.action-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.action-info {
  flex: 1;
  min-width: 0;
}

.action-name {
  display: block;
  font-size: 13px;
  color: #24292f;
  font-weight: 500;
}

.action-time {
  display: block;
  font-size: 11px;
  color: #656d76;
}

/* 滚动条样式 */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: transparent;
}

.panel-content::-webkit-scrollbar-thumb {
  background: #d0d7de;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: #8b949e;
}
</style>