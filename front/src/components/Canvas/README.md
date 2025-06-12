# 飞书风格画板功能技术设计文档

## 1. 概述

本项目实现类似飞书文档的专业画板功能，提供独立的全屏编辑界面，支持流程图、思维导图、数据库设计图等多种专业绘图需求。用户可以通过双击画板进入专门的编辑环境，享受与飞书画板相同的专业体验。

## 2. 飞书画板特性分析

### 2.1 界面布局特点
- **独立全屏编辑**：双击进入专门的画板编辑页面，提供沉浸式编辑体验
- **左侧工具面板**：垂直布局的丰富工具栏，包含形状、素材、数据建模等分类
- **顶部功能栏**：退出、画板设置、分享、导出等全局功能
- **主画布区域**：支持无限画布、网格背景、缩放平移
- **右侧属性面板**：动态显示选中元素的属性和样式设置

### 2.2 核心功能特性
- **丰富的形状库**：基础图形、流程图符号、数据库图标、网络拓扑等
- **专业连接线**：智能路由、自动吸附、多种箭头样式
- **数据建模工具**：ER图、UML图、组织架构图等专业图表
- **协作功能**：多人实时编辑、评论、历史版本
- **智能辅助**：自动对齐、智能布局、模板推荐

### 2.3 技术栈选择

基于现有架构，升级技术选型：

- **渲染引擎**: Konva.js (主要) + Fabric.js (辅助)
- **全屏界面**: Vue 3 Router + 独立路由页面
- **UI框架**: Ant Design Vue + 自定义组件
- **状态管理**: Pinia + 实时同步
- **图形库**: 自定义SVG图标库 + 专业符号库
- **导出引擎**: html2canvas + jsPDF + SVG

## 3. 架构设计重构

### 3.1 全屏编辑界面架构

#### 3.1.1 路由设计
```typescript
// 路由配置
{
  path: '/canvas/:canvasId/edit',
  name: 'CanvasFullscreenEditor',
  component: () => import('@/components/Canvas/FullscreenEditor/index.vue'),
  meta: { 
    fullscreen: true,
    requiresAuth: true 
  }
}

// 从嵌入画板进入全屏编辑
const enterFullscreenEdit = (canvasId: string) => {
  // 保存当前编辑器状态
  await saveEditorState()
  // 跳转到全屏编辑页面
  router.push(`/canvas/${canvasId}/edit`)
}
```

#### 3.1.2 组件结构重构
```
components/Canvas/
├── EmbeddedCanvas.vue           # 嵌入式画板组件 (简化版)
├── FullscreenEditor/            # 全屏编辑器 (飞书风格)
│   ├── index.vue               # 编辑器主容器
│   ├── TopBar/                 # 顶部工具栏
│   │   ├── index.vue          # 主工具栏
│   │   ├── FileActions.vue    # 文件操作 (保存/导出/分享)
│   │   ├── ViewControls.vue   # 视图控制 (缩放/网格/全屏)
│   │   └── UndoRedoControls.vue # 撤销重做
│   ├── LeftSidebar/            # 左侧工具面板
│   │   ├── index.vue          # 侧边栏容器
│   │   ├── ToolCategories.vue # 工具分类导航
│   │   ├── ShapeLibrary/      # 形状库
│   │   │   ├── BasicShapes.vue    # 基础图形
│   │   │   ├── FlowchartShapes.vue # 流程图符号
│   │   │   ├── DatabaseShapes.vue  # 数据库图标
│   │   │   ├── NetworkShapes.vue   # 网络拓扑
│   │   │   └── CustomShapes.vue    # 自定义图形
│   │   ├── MaterialLibrary.vue # 素材库
│   │   └── TemplateLibrary.vue # 模板库
│   ├── RightPanel/             # 右侧属性面板
│   │   ├── index.vue          # 面板容器
│   │   ├── ElementProperties.vue # 元素属性
│   │   ├── StyleEditor.vue    # 样式编辑器
│   │   ├── LayerManager.vue   # 图层管理
│   │   └── HistoryPanel.vue   # 历史记录
│   ├── Canvas/                 # 画布核心
│   │   ├── CanvasContainer.vue # 画布容器
│   │   ├── CanvasRenderer.vue  # 渲染引擎
│   │   ├── GridBackground.vue  # 网格背景
│   │   ├── SelectionBox.vue    # 选择框
│   │   └── ContextMenu.vue     # 右键菜单
│   └── StatusBar/              # 底部状态栏
│       ├── index.vue          # 状态栏主组件
│       ├── ZoomControls.vue   # 缩放控制
│       ├── CoordinateDisplay.vue # 坐标显示
│       └── ElementCounter.vue  # 元素统计
├── Elements/                   # 画布元素组件
│   ├── BaseElement.vue        # 基础元素类
│   ├── Shape/                 # 形状元素
│   │   ├── Rectangle.vue      # 矩形
│   │   ├── Circle.vue         # 圆形
│   │   ├── Diamond.vue        # 菱形
│   │   ├── Database.vue       # 数据库图标
│   │   └── CustomShape.vue    # 自定义形状
│   ├── Connection/            # 连接线
│   │   ├── StraightLine.vue   # 直线
│   │   ├── CurvedLine.vue     # 曲线
│   │   ├── FlowLine.vue       # 流程线
│   │   └── DataLine.vue       # 数据流线
│   ├── Text/                  # 文本元素
│   │   ├── SimpleText.vue     # 简单文本
│   │   ├── RichText.vue       # 富文本
│   │   └── Label.vue          # 标签
│   └── Group/                 # 组合元素
│       ├── ElementGroup.vue   # 元素组
│       └── Template.vue       # 模板实例
├── Tools/                     # 工具系统
│   ├── SelectTool.vue         # 选择工具
│   ├── DrawTool.vue           # 绘制工具
│   ├── TextTool.vue           # 文本工具
│   ├── ConnectorTool.vue      # 连接工具
│   └── PanTool.vue            # 平移工具
├── Stores/                    # 状态管理
│   ├── canvasStore.ts         # 画布状态
│   ├── toolStore.ts           # 工具状态
│   ├── elementStore.ts        # 元素管理
│   ├── selectionStore.ts      # 选择状态
│   ├── historyStore.ts        # 历史记录
│   └── collaborationStore.ts  # 协作状态
├── Utils/                     # 工具函数
│   ├── geometry.ts            # 几何计算
│   ├── collision.ts           # 碰撞检测
│   ├── export.ts              # 导出功能
│   ├── import.ts              # 导入功能
│   ├── template.ts            # 模板处理
│   └── collaboration.ts       # 协作工具
├── Types/                     # 类型定义
│   ├── canvas.ts              # 画布类型
│   ├── elements.ts            # 元素类型
│   ├── tools.ts               # 工具类型
│   ├── events.ts              # 事件类型
│   └── api.ts                 # API类型
└── Assets/                    # 静态资源
    ├── icons/                 # 图标库
    ├── shapes/                # 形状定义
    ├── templates/             # 模板文件
    └── themes/                # 主题样式
```

### 3.2 核心数据模型设计

#### 3.2.1 画布数据结构
```typescript
interface CanvasDocument {
  id: string
  name: string
  description?: string
  thumbnail?: string
  
  // 画布设置
  canvas: {
  width: number
  height: number
    background: BackgroundConfig
    grid: GridConfig
  zoom: number
    viewport: ViewportConfig
  }
  
  // 元素数据
  elements: CanvasElement[]
  connections: Connection[]
  groups: ElementGroup[]
  
  // 版本信息
  version: string
  createdAt: Date
  updatedAt: Date
  createdBy: string
  lastModifiedBy: string
  
  // 协作信息
  collaborators: Collaborator[]
  permissions: PermissionConfig
  
  // 导出设置
  exportSettings: ExportConfig
}

interface CanvasElement {
  id: string
  type: ElementType
  
  // 几何属性
  geometry: {
  x: number
  y: number
  width: number
  height: number
  rotation: number
    anchor: AnchorPoint
  }
  
  // 视觉样式
  style: {
    fill: FillStyle
    stroke: StrokeStyle
    shadow: ShadowStyle
    opacity: number
    visible: boolean
  }
  
  // 元素数据
  data: any
  
  // 连接点
  connectionPoints: ConnectionPoint[]
  
  // 元数据
  metadata: {
    locked: boolean
    groupId?: string
    layerId: string
    zIndex: number
    tags: string[]
  }
}

interface Connection {
  id: string
  type: ConnectionType
  
  // 连接信息
  source: {
    elementId: string
    connectionPointId: string
  }
  target: {
    elementId: string
    connectionPointId: string
  }
  
  // 路径信息
  path: PathData
  style: ConnectionStyle
  
  // 标签
  labels: ConnectionLabel[]
  
  // 元数据
  metadata: ConnectionMetadata
}
```

### 3.3 全屏编辑器界面设计

#### 3.3.1 主界面布局 (飞书风格)
```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────┐ 画板编辑器                           🔄↩️ 💾 📤 👥 ❌    │ 
│  │ ← │ 返回文档                                                │ 顶部栏
│  └─────┘                                                      │
├─┬─────────────────────────────────────────────────────────────┤
│ │ 🔲 图形                                                     │
│ │ ─────────                                                  │
│ │ 📄 素材                                                     │
│ │ ─────────                                                  │
│ │ 🗂️ 数据建模                                                 │
│ │ ─────────                                                  │
│ │ 🔧 时序图                                                    │
│ │ ─────────                                                  │
│ │ 📚 模板                                                     │
│ │                                                            │
│ │ ┌─────────┐                                                │
│ │ │ 矩形    │    ┌─────────────────────────────┐             │
│ │ └─────────┘    │                             │             │
│ │ ┌─────────┐    │        主画布区域            │ ┌─────────┐ │
│ │ │ 圆形    │    │                             │ │属性面板  │ │
│ │ └─────────┘    │     📊 🔄 💾              │ │         │ │
│ │ ┌─────────┐    │                             │ │颜色     │ │
│ │ │ 菱形    │    │                             │ │字体     │ │
│ │ └─────────┘    │                             │ │边框     │ │
│ │ ┌─────────┐    │                             │ │阴影     │ │
│ │ │ 数据库   │    │                             │ │         │ │
│ │ └─────────┘    │                             │ │图层     │ │
│ │                │                             │ │历史     │ │
│ │                └─────────────────────────────┘ └─────────┘ │
├─┴─────────────────────────────────────────────────────────────┤
│ 🔍 100% │ 网格 │ 坐标 (0, 0) │ 选中 3 个元素 │ 自动保存    │ 状态栏
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 左侧工具面板详细设计

##### 图形工具分类
```typescript
const ShapeCategories = {
  basic: {
    name: '基础图形',
    icon: '🔲',
    shapes: [
      { type: 'rectangle', name: '矩形', icon: '▭' },
      { type: 'circle', name: '圆形', icon: '○' },
      { type: 'diamond', name: '菱形', icon: '◇' },
      { type: 'triangle', name: '三角形', icon: '△' },
      { type: 'pentagon', name: '五边形', icon: '⬟' },
      { type: 'hexagon', name: '六边形', icon: '⬡' },
      { type: 'star', name: '星形', icon: '☆' },
      { type: 'arrow', name: '箭头', icon: '→' }
    ]
  },
  
  flowchart: {
    name: '流程图',
    icon: '📊',
    shapes: [
      { type: 'process', name: '处理', icon: '▭' },
      { type: 'decision', name: '判断', icon: '◇' },
      { type: 'terminal', name: '终端', icon: '▯' },
      { type: 'document', name: '文档', icon: '📄' },
      { type: 'database', name: '数据库', icon: '🗃️' },
      { type: 'storage', name: '存储', icon: '🛢️' }
    ]
  },
  
  database: {
    name: '数据建模',
    icon: '🗂️',
    shapes: [
      { type: 'entity', name: '实体', icon: '📋' },
      { type: 'attribute', name: '属性', icon: '○' },
      { type: 'relationship', name: '关系', icon: '◇' },
      { type: 'table', name: '表', icon: '📊' },
      { type: 'view', name: '视图', icon: '👁️' },
      { type: 'index', name: '索引', icon: '🔍' }
    ]
  },
  
  network: {
    name: '网络拓扑',
    icon: '🌐',
    shapes: [
      { type: 'server', name: '服务器', icon: '🖥️' },
      { type: 'router', name: '路由器', icon: '📡' },
      { type: 'switch', name: '交换机', icon: '🔌' },
      { type: 'firewall', name: '防火墙', icon: '🛡️' },
      { type: 'cloud', name: '云服务', icon: '☁️' },
      { type: 'user', name: '用户', icon: '👤' }
    ]
  },
  
  uml: {
    name: 'UML图',
    icon: '📐',
    shapes: [
      { type: 'class', name: '类', icon: '📦' },
      { type: 'interface', name: '接口', icon: '🔌' },
      { type: 'actor', name: '角色', icon: '👤' },
      { type: 'usecase', name: '用例', icon: '○' },
      { type: 'component', name: '组件', icon: '📦' },
      { type: 'node', name: '节点', icon: '🖥️' }
    ]
  }
}
```

#### 3.3.3 顶部工具栏功能设计

```typescript
const TopBarActions = {
  navigation: {
    back: { icon: '←', title: '返回文档', shortcut: 'Esc' },
    title: { text: '画板名称', editable: true }
  },
  
  file: {
    save: { icon: '💾', title: '保存', shortcut: 'Ctrl+S' },
    export: { 
      icon: '📤', 
      title: '导出',
      options: ['PNG', 'SVG', 'PDF', 'JSON']
    },
    import: {
      icon: '📥',
      title: '导入',
      options: ['JSON', 'SVG', 'Visio', 'Draw.io']
    }
  },
  
  collaboration: {
    share: { icon: '👥', title: '分享', action: 'openShareDialog' },
    comments: { icon: '💬', title: '评论', badge: 3 },
    history: { icon: '🕐', title: '历史版本' }
  },
  
  view: {
    undo: { icon: '↩️', title: '撤销', shortcut: 'Ctrl+Z' },
    redo: { icon: '↪️', title: '重做', shortcut: 'Ctrl+Y' },
    zoom: { icon: '🔍', title: '缩放', options: ['适合窗口', '100%', '200%'] },
    fullscreen: { icon: '⛶', title: '全屏', shortcut: 'F11' }
  }
}
```

### 3.4 关键技术实现

#### 3.4.1 全屏模式切换
```typescript
// 从嵌入画板进入全屏编辑
class CanvasTransition {
  async enterFullscreen(canvasId: string) {
    // 1. 保存当前编辑器状态
    const editorState = await this.saveCurrentEditorState()
    
    // 2. 获取画布数据
    const canvasData = await this.loadCanvasData(canvasId)
    
    // 3. 设置全屏编辑状态
    this.setFullscreenMode(true)
    
    // 4. 路由跳转
    await router.push({
      name: 'CanvasFullscreenEditor',
      params: { canvasId },
      query: { 
        returnTo: router.currentRoute.value.fullPath,
        editorState: btoa(JSON.stringify(editorState))
      }
    })
  }
  
  async exitFullscreen() {
    // 1. 保存画布更改
    await this.saveCanvasChanges()
    
    // 2. 恢复编辑器状态
    const returnTo = router.currentRoute.value.query.returnTo
    const editorState = JSON.parse(atob(router.currentRoute.value.query.editorState))
    
    // 3. 返回原页面
    await router.push(returnTo)
    await this.restoreEditorState(editorState)
    
    // 4. 刷新嵌入画板
    this.refreshEmbeddedCanvas()
  }
}
```

#### 3.4.2 高性能渲染引擎
```typescript
class CanvasRenderer {
  private konvaStage: Konva.Stage
  private fabricCanvas: fabric.Canvas
  private renderMode: 'konva' | 'fabric' = 'konva'
  
  constructor(container: HTMLDivElement) {
    // 初始化Konva舞台 (主要渲染引擎)
    this.konvaStage = new Konva.Stage({
      container,
      width: container.offsetWidth,
      height: container.offsetHeight,
      draggable: true
    })
    
    // 初始化Fabric画布 (复杂图形和文本)
    this.fabricCanvas = new fabric.Canvas(null, {
      width: container.offsetWidth,
      height: container.offsetHeight,
      renderOnAddRemove: false
    })
    
    this.setupLayers()
    this.setupInteraction()
  }
  
  // 智能渲染模式选择
  selectRenderMode(element: CanvasElement) {
    if (element.type === 'text' || element.type === 'richText') {
      return 'fabric' // Fabric擅长文本处理
    }
    if (element.type === 'path' || element.type === 'freehand') {
      return 'fabric' // Fabric擅长路径绘制
    }
    return 'konva' // Konva擅长图形渲染和动画
  }
  
  // 虚拟化渲染 (大量元素优化)
  renderWithVirtualization(elements: CanvasElement[], viewport: Viewport) {
    const visibleElements = this.getVisibleElements(elements, viewport)
    const renderQueue = this.createRenderQueue(visibleElements)
    
    requestAnimationFrame(() => {
      this.batchRender(renderQueue)
    })
  }
}
```

#### 3.4.3 智能连接系统
```typescript
class SmartConnectionSystem {
  private snapDistance = 10
  private connectionPoints: Map<string, ConnectionPoint[]> = new Map()
  
  // 自动检测连接点
  detectConnectionPoints(element: CanvasElement): ConnectionPoint[] {
    const { x, y, width, height } = element.geometry
    
    // 基础连接点 (上下左右中心)
    const basicPoints = [
      { id: 'top', x: x + width/2, y, direction: 'up' },
      { id: 'right', x: x + width, y: y + height/2, direction: 'right' },
      { id: 'bottom', x: x + width/2, y: y + height, direction: 'down' },
      { id: 'left', x, y: y + height/2, direction: 'left' }
    ]
    
    // 根据元素类型添加特殊连接点
    const specialPoints = this.getSpecialConnectionPoints(element)
    
    return [...basicPoints, ...specialPoints]
  }
  
  // 智能路由算法
  calculateSmartRoute(start: Point, end: Point, obstacles: CanvasElement[]): Point[] {
    // A*算法寻找最优路径
    const pathfinder = new AStarPathfinder(obstacles)
    const waypoints = pathfinder.findPath(start, end)
    
    // 路径平滑处理
    return this.smoothPath(waypoints)
  }
  
  // 自动吸附
  snapToNearbyPoints(point: Point): Point {
    const nearbyPoints = this.findNearbyConnectionPoints(point, this.snapDistance)
    
    if (nearbyPoints.length > 0) {
      const closest = nearbyPoints.reduce((prev, current) => 
        this.distance(point, current) < this.distance(point, prev) ? current : prev
      )
      return closest
    }
    
    return point
  }
}
```

## 4. 专业功能实现

### 4.1 形状库系统

#### 4.1.1 动态形状加载
```typescript
class ShapeLibraryManager {
  private shapeCache: Map<string, ShapeDefinition> = new Map()
  private customShapes: Map<string, CustomShape> = new Map()
  
  // 延迟加载形状定义
  async loadShapeCategory(category: string): Promise<ShapeDefinition[]> {
    if (!this.shapeCache.has(category)) {
      const module = await import(`@/assets/shapes/${category}.ts`)
      this.shapeCache.set(category, module.default)
    }
    
    return this.shapeCache.get(category)!
  }
  
  // 创建形状实例
  createShape(type: string, options: ShapeOptions): CanvasElement {
    const definition = this.getShapeDefinition(type)
    
    return {
      id: generateId(),
      type,
      geometry: this.calculateGeometry(definition, options),
      style: this.applyDefaultStyle(definition),
      data: definition.defaultData || {},
      connectionPoints: this.generateConnectionPoints(definition),
      metadata: {
        locked: false,
        layerId: 'default',
        zIndex: this.getNextZIndex(),
        tags: definition.tags || []
      }
    }
  }
}
```

#### 4.1.2 自定义形状编辑器
```vue
<template>
  <div class="custom-shape-editor">
    <div class="shape-canvas">
      <svg :width="canvasSize.width" :height="canvasSize.height">
        <g v-for="path in shapePaths" :key="path.id">
          <path 
            :d="path.d" 
            :fill="path.fill" 
            :stroke="path.stroke"
            @click="selectPath(path)"
          />
        </g>
        <!-- 编辑控制点 -->
        <g v-if="selectedPath">
          <circle 
            v-for="point in editPoints" 
            :key="point.id"
            :cx="point.x" 
            :cy="point.y" 
            r="4"
            fill="#1890ff"
            @mousedown="startDragPoint(point)"
          />
        </g>
      </svg>
    </div>
    
    <div class="shape-properties">
      <ShapeStyleEditor v-model="selectedPath.style" />
      <ConnectionPointEditor v-model="connectionPoints" />
    </div>
  </div>
</template>
```

### 4.2 数据建模工具

#### 4.2.1 ER图生成器
```typescript
class ERDiagramGenerator {
  generateTable(tableData: TableDefinition): CanvasElement {
    const { name, columns, primaryKeys, foreignKeys } = tableData
    
    // 计算表格尺寸
    const headerHeight = 40
    const rowHeight = 30
    const width = Math.max(200, name.length * 10)
    const height = headerHeight + columns.length * rowHeight
    
    return {
      id: generateId(),
      type: 'database-table',
      geometry: { x: 0, y: 0, width, height, rotation: 0, anchor: 'top-left' },
      style: this.getTableStyle(),
      data: {
        name,
        columns: columns.map(col => ({
          ...col,
          isPrimaryKey: primaryKeys.includes(col.name),
          isForeignKey: foreignKeys.some(fk => fk.column === col.name)
        }))
      },
      connectionPoints: this.generateTableConnectionPoints(width, height),
      metadata: {
        locked: false,
        layerId: 'tables',
        zIndex: 1,
        tags: ['database', 'table']
      }
    }
  }
  
  generateRelationship(source: string, target: string, type: RelationType): Connection {
    return {
      id: generateId(),
      type: 'database-relationship',
      source: { elementId: source, connectionPointId: 'right' },
      target: { elementId: target, connectionPointId: 'left' },
      path: this.calculateRelationshipPath(),
      style: this.getRelationshipStyle(type),
      labels: [{ text: this.getRelationshipLabel(type), position: 0.5 }],
      metadata: { relationshipType: type }
    }
  }
}
```

#### 4.2.2 UML类图编辑器
```vue
<template>
  <div class="uml-class-editor">
    <div class="class-header">
      <input v-model="classData.name" placeholder="类名" />
      <select v-model="classData.stereotype">
        <option value="">无</option>
        <option value="abstract">抽象类</option>
        <option value="interface">接口</option>
        <option value="enum">枚举</option>
      </select>
    </div>
    
    <div class="class-attributes">
      <h4>属性</h4>
      <div v-for="(attr, index) in classData.attributes" :key="index" class="attribute-row">
        <select v-model="attr.visibility">
          <option value="public">+</option>
          <option value="private">-</option>
          <option value="protected">#</option>
        </select>
        <input v-model="attr.name" placeholder="属性名" />
        <input v-model="attr.type" placeholder="类型" />
        <button @click="removeAttribute(index)">删除</button>
      </div>
      <button @click="addAttribute">添加属性</button>
    </div>
    
    <div class="class-methods">
      <h4>方法</h4>
      <div v-for="(method, index) in classData.methods" :key="index" class="method-row">
        <select v-model="method.visibility">
          <option value="public">+</option>
          <option value="private">-</option>
          <option value="protected">#</option>
        </select>
        <input v-model="method.name" placeholder="方法名" />
        <input v-model="method.parameters" placeholder="参数" />
        <input v-model="method.returnType" placeholder="返回类型" />
        <button @click="removeMethod(index)">删除</button>
      </div>
      <button @click="addMethod">添加方法</button>
    </div>
  </div>
</template>
```

### 4.3 模板系统

#### 4.3.1 智能模板推荐
```typescript
class TemplateRecommendationEngine {
  private templates: TemplateDefinition[] = []
  private userHistory: UserAction[] = []
  
  // 基于用户行为推荐模板
  recommendTemplates(context: RecommendationContext): TemplateRecommendation[] {
    const { currentElements, userIntent, projectType } = context
    
    // 分析当前画布内容
    const contentAnalysis = this.analyzeCanvasContent(currentElements)
    
    // 匹配相似模板
    const similarTemplates = this.findSimilarTemplates(contentAnalysis)
    
    // 基于用户历史偏好
    const preferredTemplates = this.filterByUserPreferences(similarTemplates)
    
    // 计算推荐分数
    return preferredTemplates.map(template => ({
      template,
      score: this.calculateRecommendationScore(template, context),
      reason: this.generateRecommendationReason(template, context)
    })).sort((a, b) => b.score - a.score)
  }
  
  // 生成自定义模板
  generateTemplateFromSelection(elements: CanvasElement[]): TemplateDefinition {
    return {
      id: generateId(),
      name: this.suggestTemplateName(elements),
      category: this.detectTemplateCategory(elements),
      thumbnail: this.generateThumbnail(elements),
      elements: this.normalizeElements(elements),
      metadata: {
        createdAt: new Date(),
        usage: 0,
        tags: this.extractTags(elements)
      }
    }
  }
}
```

#### 4.3.2 模板市场
```vue
<template>
  <div class="template-marketplace">
    <div class="template-categories">
      <div 
        v-for="category in categories" 
        :key="category.id"
        class="category-item"
        :class="{ active: selectedCategory === category.id }"
        @click="selectCategory(category.id)"
      >
        <div class="category-icon">{{ category.icon }}</div>
        <div class="category-name">{{ category.name }}</div>
        <div class="category-count">{{ category.templateCount }}</div>
      </div>
    </div>
    
    <div class="template-grid">
      <div 
        v-for="template in filteredTemplates" 
        :key="template.id"
        class="template-card"
        @click="previewTemplate(template)"
        @dblclick="useTemplate(template)"
      >
        <div class="template-thumbnail">
          <img :src="template.thumbnail" :alt="template.name" />
        </div>
        <div class="template-info">
          <h4>{{ template.name }}</h4>
          <p>{{ template.description }}</p>
          <div class="template-meta">
            <span class="usage-count">{{ template.usage }}次使用</span>
            <span class="rating">⭐ {{ template.rating }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 模板预览 -->
    <TemplatePreviewModal 
      v-if="showPreview"
      :template="previewTemplate"
      @close="showPreview = false"
      @use="useTemplate"
    />
  </div>
</template>
```

## 5. 协作功能设计

### 5.1 实时协作编辑
```typescript
class CollaborationEngine {
  private websocket: WebSocket
  private operationalTransform: OTEngine
  private conflictResolver: ConflictResolver
  
  // 实时同步画布操作
  syncOperation(operation: CanvasOperation) {
    // 操作转换
    const transformedOp = this.operationalTransform.transform(operation)
    
    // 发送到服务器
    this.websocket.send(JSON.stringify({
      type: 'canvas-operation',
      operation: transformedOp,
      timestamp: Date.now(),
      userId: this.currentUser.id
    }))
    
    // 本地应用
    this.applyOperation(transformedOp)
  }
  
  // 处理远程操作
  handleRemoteOperation(operation: CanvasOperation) {
    // 冲突检测
    if (this.conflictResolver.hasConflict(operation)) {
      const resolution = this.conflictResolver.resolve(operation)
      this.applyResolution(resolution)
    } else {
      this.applyOperation(operation)
    }
    
    // 更新协作者光标
    this.updateCollaboratorCursor(operation.userId, operation.cursor)
  }
}
```

### 5.2 评论和批注系统
```vue
<template>
  <div class="comment-system">
    <!-- 画布上的评论标记 -->
    <div 
      v-for="comment in canvasComments" 
      :key="comment.id"
      class="comment-marker"
      :style="{ left: comment.x + 'px', top: comment.y + 'px' }"
      @click="openComment(comment)"
    >
      <div class="comment-badge">{{ comment.replies.length + 1 }}</div>
    </div>
    
    <!-- 评论面板 -->
    <div v-if="activeComment" class="comment-panel">
      <div class="comment-thread">
        <div class="comment-item" v-for="item in commentThread" :key="item.id">
          <div class="comment-author">
            <img :src="item.author.avatar" />
            <span>{{ item.author.name }}</span>
            <time>{{ formatTime(item.createdAt) }}</time>
          </div>
          <div class="comment-content">{{ item.content }}</div>
        </div>
      </div>
      
      <div class="comment-input">
        <textarea v-model="newComment" placeholder="添加评论..."></textarea>
        <button @click="addComment">发送</button>
      </div>
    </div>
  </div>
</template>
```

## 6. 开发优先级和时间规划

### Phase 1: 全屏编辑器基础架构 (2-3周)
- [x] 路由和页面架构搭建
- [x] 基础布局组件 (顶部栏、左侧栏、画布、右侧栏)
- [x] Konva.js 渲染引擎集成
- [x] 基础工具系统框架
- [x] 状态管理架构

### Phase 2: 核心绘图功能 (3-4周)
- [ ] 基础形状绘制 (矩形、圆形、线条)
- [ ] 选择和变换工具
- [ ] 文本编辑功能
- [ ] 连接线系统
- [ ] 撤销重做功能

### Phase 3: 专业图形库 (3-4周)
- [ ] 流程图形状库
- [ ] 数据库建模工具
- [ ] UML图形支持
- [ ] 网络拓扑图标
- [ ] 自定义形状编辑器

### Phase 4: 高级功能 (4-5周)
- [ ] 智能连接和自动布局
- [ ] 模板系统
- [ ] 导出功能 (PNG/SVG/PDF)
- [ ] 协作编辑基础
- [ ] 评论批注系统

### Phase 5: 优化和集成 (2-3周)
- [ ] 性能优化
- [ ] 移动端适配
- [ ] 与主编辑器集成
- [ ] 全面测试
- [ ] 文档完善

## 7. 技术挑战和解决方案

### 7.1 大规模元素渲染性能
**挑战**: 画布包含数千个元素时的渲染性能

**解决方案**:
- 虚拟化渲染：只渲染可视区域的元素
- 图层缓存：静态元素缓存为纹理
- 级联更新：只更新变化的元素
- Web Worker：大量计算移到后台线程

### 7.2 实时协作冲突解决
**挑战**: 多人同时编辑时的操作冲突

**解决方案**:
- 操作转换算法 (Operational Transformation)
- 版本向量时钟同步
- 语义冲突检测
- 用户意图保持算法

### 7.3 复杂图形精确交互
**挑战**: 复杂路径和形状的精确选择和编辑

**解决方案**:
- 碰撞检测算法优化
- 多级精度交互 (粗糙 → 精确)
- 智能捕获区域
- 上下文相关的交互提示

## 8. 总结

通过对飞书画板的深入分析，我们设计了一套完整的全屏画板编辑系统。核心特点包括：

1. **独立全屏编辑体验**: 通过路由跳转提供沉浸式编辑环境
2. **专业工具生态**: 丰富的形状库和专业绘图工具
3. **智能交互系统**: 自动吸附、智能路由、批量操作
4. **高性能渲染**: 基于Konva.js的优化渲染引擎
5. **协作编辑支持**: 实时同步和冲突解决机制

这个设计方案既保持了与现有架构的兼容性，又提供了专业级的画板编辑体验，能够满足各种复杂的绘图需求。 