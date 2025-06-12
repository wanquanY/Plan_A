<template>
  <div class="template-panel">
    <div class="panel-header">
      <h3>模板库</h3>
      <a-input-search 
        v-model:value="searchText" 
        placeholder="搜索模板..." 
        size="small"
        @search="handleSearch"
      />
    </div>
    
    <div class="template-categories">
      <a-tabs v-model:activeKey="activeCategory" size="small">
        <a-tab-pane key="flowchart" tab="流程图">
          <div class="template-grid">
            <div 
              v-for="template in flowchartTemplates"
              :key="template.id"
              class="template-item"
              @click="applyTemplate(template)"
            >
              <div class="template-preview">
                <img :src="template.preview" :alt="template.name" />
              </div>
              <div class="template-info">
                <h4>{{ template.name }}</h4>
                <p>{{ template.description }}</p>
              </div>
            </div>
          </div>
        </a-tab-pane>
        
        <a-tab-pane key="mindmap" tab="思维导图">
          <div class="template-grid">
            <div 
              v-for="template in mindmapTemplates"
              :key="template.id"
              class="template-item"
              @click="applyTemplate(template)"
            >
              <div class="template-preview">
                <img :src="template.preview" :alt="template.name" />
              </div>
              <div class="template-info">
                <h4>{{ template.name }}</h4>
                <p>{{ template.description }}</p>
              </div>
            </div>
          </div>
        </a-tab-pane>
        
        <a-tab-pane key="shapes" tab="常用形状">
          <div class="shape-grid">
            <div 
              v-for="shape in commonShapes"
              :key="shape.type"
              class="shape-item"
              @click="addShape(shape)"
              :title="shape.name"
            >
              <div class="shape-preview" :data-shape="shape.type">
                {{ shape.icon }}
              </div>
              <span>{{ shape.name }}</span>
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Tabs as ATabs, TabPane as ATabPane, Input as AInput } from 'ant-design-vue'
import { useCanvasStore } from '../stores/canvasStore'
import { ElementType } from '../types/canvas'

const AInputSearch = AInput.Search

// 状态管理
const canvasStore = useCanvasStore()

// 面板状态
const searchText = ref('')
const activeCategory = ref('flowchart')

// 模板数据
const flowchartTemplates = ref([
  {
    id: 'flowchart-basic',
    name: '基础流程图',
    description: '包含开始、处理、决策、结束等基本元素',
    preview: '/templates/flowchart-basic.png',
    elements: [
      {
        type: ElementType.RECTANGLE,
        x: 100,
        y: 50,
        width: 120,
        height: 60,
        style: { fill: '#e1f5fe', stroke: '#01579b' },
        data: { text: '开始' }
      },
      {
        type: ElementType.RECTANGLE,
        x: 100,
        y: 150,
        width: 120,
        height: 60,
        style: { fill: '#f3e5f5', stroke: '#4a148c' },
        data: { text: '处理' }
      }
    ]
  },
  {
    id: 'flowchart-decision',
    name: '决策流程图',
    description: '包含判断条件的复杂流程图模板',
    preview: '/templates/flowchart-decision.png',
    elements: []
  }
])

const mindmapTemplates = ref([
  {
    id: 'mindmap-basic',
    name: '基础思维导图',
    description: '中心主题加四个分支的思维导图',
    preview: '/templates/mindmap-basic.png',
    elements: []
  },
  {
    id: 'mindmap-project',
    name: '项目规划',
    description: '适用于项目规划的思维导图模板',
    preview: '/templates/mindmap-project.png',
    elements: []
  }
])

const commonShapes = ref([
  { type: ElementType.RECTANGLE, name: '矩形', icon: '▭' },
  { type: ElementType.CIRCLE, name: '圆形', icon: '●' },
  { type: ElementType.TRIANGLE, name: '三角形', icon: '▲' },
  { type: ElementType.LINE, name: '直线', icon: '━' },
  { type: ElementType.ARROW, name: '箭头', icon: '→' },
  { type: ElementType.TEXT, name: '文本', icon: 'T' }
])

// 方法
const handleSearch = (value: string) => {
  console.log('搜索模板:', value)
  // 实现搜索逻辑
}

const applyTemplate = (template: any) => {
  console.log('应用模板:', template.name)
  
  // 清空当前画布
  canvasStore.clearCanvas()
  
  // 添加模板元素
  template.elements.forEach((element: any) => {
    canvasStore.addElement({
      ...element,
      zIndex: 0,
      locked: false,
      visible: true,
      rotation: 0
    })
  })
}

const addShape = (shape: any) => {
  console.log('添加形状:', shape.name)
  
  // 在画布中心添加形状
  const centerX = canvasStore.canvasData.width / 2 - 60
  const centerY = canvasStore.canvasData.height / 2 - 30
  
  canvasStore.addElement({
    type: shape.type,
    x: centerX,
    y: centerY,
    width: shape.type === ElementType.TEXT ? 100 : 120,
    height: shape.type === ElementType.TEXT ? 40 : 60,
    rotation: 0,
    zIndex: canvasStore.canvasData.elements.length,
    locked: false,
    visible: true,
    style: {
      fill: '#ffffff',
      stroke: '#000000',
      strokeWidth: 2,
      opacity: 1
    },
    data: shape.type === ElementType.TEXT ? { text: '新文本' } : {}
  })
}
</script>

<style scoped>
.template-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.template-categories {
  flex: 1;
  overflow: hidden;
}

.template-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  padding: 16px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.template-item {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.template-item:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

.template-preview {
  width: 100%;
  height: 120px;
  background: #fafafa;
  border-radius: 4px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.template-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.template-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 500;
  color: #262626;
}

.template-info p {
  margin: 0;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.4;
}

.shape-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 16px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.shape-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.shape-item:hover {
  border-color: #1890ff;
  background: #f6fbff;
}

.shape-preview {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #1890ff;
  margin-bottom: 8px;
}

.shape-item span {
  font-size: 12px;
  color: #666;
  text-align: center;
}

/* 滚动条样式 */
.template-grid::-webkit-scrollbar,
.shape-grid::-webkit-scrollbar {
  width: 6px;
}

.template-grid::-webkit-scrollbar-track,
.shape-grid::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.template-grid::-webkit-scrollbar-thumb,
.shape-grid::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.template-grid::-webkit-scrollbar-thumb:hover,
.shape-grid::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style> 