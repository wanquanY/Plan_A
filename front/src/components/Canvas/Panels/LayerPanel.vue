<template>
  <div class="layer-panel">
    <div class="panel-header">
      <h3>图层</h3>
      <div class="header-actions">
        <a-button size="small" @click="addLayer" title="添加图层">
          <PlusOutlined />
        </a-button>
        <a-button size="small" @click="deleteSelectedLayers" :disabled="!hasSelection" title="删除选中图层">
          <DeleteOutlined />
        </a-button>
      </div>
    </div>
    
    <div class="layer-list">
      <div class="layer-controls">
        <a-button-group size="small">
          <a-button @click="selectAll" title="全选">全选</a-button>
          <a-button @click="clearSelection" title="清除选择">清除</a-button>
        </a-button-group>
      </div>
      
      <div class="layers-container">
        <draggable 
          v-model="sortedElements"
          @change="handleLayerReorder"
          item-key="id"
          class="layer-items"
        >
          <template #item="{ element, index }">
            <div 
              class="layer-item"
              :class="{ 
                selected: isSelected(element.id),
                locked: element.locked,
                hidden: !element.visible
              }"
              @click="handleLayerClick(element.id, $event)"
              @dblclick="handleLayerDoubleClick(element.id)"
            >
              <!-- 图层缩略图 -->
              <div class="layer-thumbnail">
                <div class="thumbnail-content" :data-type="element.type">
                  {{ getElementIcon(element.type) }}
                </div>
              </div>
              
              <!-- 图层信息 -->
              <div class="layer-info">
                <div class="layer-name" v-if="!isEditing(element.id)">
                  {{ getElementName(element) }}
                </div>
                <a-input 
                  v-else
                  v-model:value="editingName"
                  size="small"
                  @blur="handleNameEditComplete(element.id)"
                  @keyup.enter="handleNameEditComplete(element.id)"
                  @keyup.esc="cancelNameEdit"
                  ref="nameInput"
                />
                <div class="layer-type">{{ getElementTypeName(element.type) }}</div>
              </div>
              
              <!-- 图层操作按钮 -->
              <div class="layer-actions">
                <a-button 
                  size="small" 
                  type="text"
                  @click.stop="toggleVisibility(element.id)"
                  :title="element.visible ? '隐藏' : '显示'"
                >
                  <EyeOutlined v-if="element.visible" />
                  <EyeInvisibleOutlined v-else />
                </a-button>
                
                <a-button 
                  size="small" 
                  type="text"
                  @click.stop="toggleLock(element.id)"
                  :title="element.locked ? '解锁' : '锁定'"
                >
                  <UnlockOutlined v-if="!element.locked" />
                  <LockOutlined v-else />
                </a-button>
                
                <a-dropdown :trigger="['click']" @click.stop>
                  <a-button size="small" type="text">
                    <MoreOutlined />
                  </a-button>
                  <template #overlay>
                    <a-menu @click="handleContextAction($event, element.id)">
                      <a-menu-item key="duplicate">复制图层</a-menu-item>
                      <a-menu-item key="bringToFront">置于顶层</a-menu-item>
                      <a-menu-item key="sendToBack">置于底层</a-menu-item>
                      <a-menu-divider />
                      <a-menu-item key="delete" danger>删除图层</a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
            </div>
          </template>
        </draggable>
      </div>
      
      <!-- 空状态 -->
      <div v-if="elements.length === 0" class="empty-state">
        <div class="empty-icon">📄</div>
        <p>暂无图层</p>
        <a-button size="small" @click="addDefaultShape">添加形状</a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { 
  Button as AButton, 
  ButtonGroup as AButtonGroup,
  Input as AInput,
  Dropdown as ADropdown,
  Menu as AMenu,
  MenuItem as AMenuItem,
  MenuDivider as AMenuDivider
} from 'ant-design-vue'
import { 
  PlusOutlined, 
  DeleteOutlined, 
  EyeOutlined, 
  EyeInvisibleOutlined,
  LockOutlined,
  UnlockOutlined,
  MoreOutlined 
} from '@ant-design/icons-vue'
import draggable from 'vuedraggable'
import { useCanvasStore } from '../stores/canvasStore'
import { ElementType } from '../types/canvas'

// 状态管理
const canvasStore = useCanvasStore()
const { canvasData, selection, hasSelection, selectedElements } = canvasStore

// 组件状态
const editingLayerId = ref<string | null>(null)
const editingName = ref('')
const nameInput = ref<any>(null)

// 计算属性
const elements = computed(() => canvasData.elements)

const sortedElements = computed({
  get: () => [...elements.value].sort((a, b) => b.zIndex - a.zIndex),
  set: (value) => {
    // 更新元素顺序时的处理
    value.forEach((element, index) => {
      const newZIndex = value.length - index - 1
      canvasStore.updateElement(element.id, { zIndex: newZIndex })
    })
  }
})

// 方法
const isSelected = (elementId: string) => {
  return selection.selectedIds.includes(elementId)
}

const isEditing = (elementId: string) => {
  return editingLayerId.value === elementId
}

const getElementIcon = (type: ElementType) => {
  const iconMap = {
    [ElementType.RECTANGLE]: '▭',
    [ElementType.CIRCLE]: '●',
    [ElementType.ELLIPSE]: '⬭',
    [ElementType.TRIANGLE]: '▲',
    [ElementType.LINE]: '━',
    [ElementType.ARROW]: '→',
    [ElementType.TEXT]: 'T',
    [ElementType.IMAGE]: '🖼',
    [ElementType.GROUP]: '📁',
    [ElementType.PATH]: '✏️'
  }
  return iconMap[type] || '?'
}

const getElementName = (element: any) => {
  if (element.data?.name) return element.data.name
  if (element.type === ElementType.TEXT && element.data?.text) {
    return element.data.text.substring(0, 20) + (element.data.text.length > 20 ? '...' : '')
  }
  return getElementTypeName(element.type)
}

const getElementTypeName = (type: ElementType) => {
  const typeMap = {
    [ElementType.RECTANGLE]: '矩形',
    [ElementType.CIRCLE]: '圆形',
    [ElementType.ELLIPSE]: '椭圆',
    [ElementType.TRIANGLE]: '三角形',
    [ElementType.LINE]: '直线',
    [ElementType.ARROW]: '箭头',
    [ElementType.TEXT]: '文本',
    [ElementType.IMAGE]: '图片',
    [ElementType.GROUP]: '组合',
    [ElementType.PATH]: '路径'
  }
  return typeMap[type] || '未知'
}

const handleLayerClick = (elementId: string, event: MouseEvent) => {
  if (event.ctrlKey || event.metaKey) {
    if (isSelected(elementId)) {
      canvasStore.deselectElement(elementId)
    } else {
      canvasStore.selectElement(elementId, true)
    }
  } else {
    canvasStore.selectElement(elementId, false)
  }
}

const handleLayerDoubleClick = (elementId: string) => {
  startNameEdit(elementId)
}

const startNameEdit = (elementId: string) => {
  const element = elements.value.find(el => el.id === elementId)
  if (!element) return
  
  editingLayerId.value = elementId
  editingName.value = getElementName(element)
  
  nextTick(() => {
    if (nameInput.value) {
      nameInput.value.focus()
    }
  })
}

const handleNameEditComplete = (elementId: string) => {
  if (editingName.value.trim()) {
    canvasStore.updateElement(elementId, {
      data: { ...elements.value.find(el => el.id === elementId)?.data, name: editingName.value }
    })
  }
  cancelNameEdit()
}

const cancelNameEdit = () => {
  editingLayerId.value = null
  editingName.value = ''
}

const toggleVisibility = (elementId: string) => {
  const element = elements.value.find(el => el.id === elementId)
  if (element) {
    canvasStore.updateElement(elementId, { visible: !element.visible })
  }
}

const toggleLock = (elementId: string) => {
  const element = elements.value.find(el => el.id === elementId)
  if (element) {
    canvasStore.updateElement(elementId, { locked: !element.locked })
  }
}

const handleLayerReorder = () => {
  // 拖拽重排序的处理逻辑已在 sortedElements 的 setter 中处理
}

const handleContextAction = (event: any, elementId: string) => {
  const action = event.key
  
  switch (action) {
    case 'duplicate':
      canvasStore.duplicateElement(elementId)
      break
    case 'bringToFront':
      canvasStore.bringToFront(elementId)
      break
    case 'sendToBack':
      canvasStore.sendToBack(elementId)
      break
    case 'delete':
      canvasStore.removeElement(elementId)
      break
  }
}

const addLayer = () => {
  // 添加新图层（默认矩形）
  const centerX = canvasData.width / 2 - 60
  const centerY = canvasData.height / 2 - 30
  
  canvasStore.addElement({
    type: ElementType.RECTANGLE,
    x: centerX,
    y: centerY,
    width: 120,
    height: 60,
    rotation: 0,
    zIndex: elements.value.length,
    locked: false,
    visible: true,
    style: {
      fill: '#ffffff',
      stroke: '#000000',
      strokeWidth: 2,
      opacity: 1
    },
    data: { name: '新图层' }
  })
}

const addDefaultShape = () => {
  addLayer()
}

const deleteSelectedLayers = () => {
  selectedElements.forEach(element => {
    canvasStore.removeElement(element.id)
  })
}

const selectAll = () => {
  canvasStore.selectAll()
}

const clearSelection = () => {
  canvasStore.clearSelection()
}
</script>

<style scoped>
.layer-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: white;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.layer-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.layer-controls {
  padding: 12px 16px;
  background: white;
  border-bottom: 1px solid #f0f0f0;
}

.layers-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.layer-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.layer-item {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  margin: 0 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
  border: 1px solid transparent;
}

.layer-item:hover {
  background: #f6fbff;
  border-color: #e6f7ff;
}

.layer-item.selected {
  background: #e6f7ff;
  border-color: #1890ff;
}

.layer-item.locked {
  opacity: 0.6;
}

.layer-item.hidden {
  opacity: 0.4;
}

.layer-thumbnail {
  width: 32px;
  height: 32px;
  margin-right: 12px;
  flex-shrink: 0;
}

.thumbnail-content {
  width: 100%;
  height: 100%;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #1890ff;
}

.layer-info {
  flex: 1;
  min-width: 0;
}

.layer-name {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.layer-type {
  font-size: 12px;
  color: #8c8c8c;
}

.layer-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.empty-state {
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

.empty-state p {
  margin: 0 0 16px 0;
  font-size: 14px;
}

/* 拖拽样式 */
.sortable-ghost {
  opacity: 0.5;
}

.sortable-chosen {
  transform: scale(1.02);
}

.sortable-drag {
  transform: rotate(2deg);
}

/* 滚动条样式 */
.layers-container::-webkit-scrollbar {
  width: 6px;
}

.layers-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.layers-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.layers-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style> 