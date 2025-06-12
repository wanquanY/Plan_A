<template>
  <div class="left-sidebar">
    <!-- 顶部搜索框 -->
    <div class="search-box">
      <div class="search-input-wrapper">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
        </svg>
        <input 
          type="text" 
          placeholder="搜索" 
          v-model="searchQuery"
          class="search-input"
        />
      </div>
    </div>

    <!-- 工具分类 -->
    <div class="tool-categories">
      <!-- 基础分类 -->
      <div class="category-section">
        <div 
          class="category-item"
          :class="{ active: isCategoryExpanded('basic') }"
          @click="setActiveCategory('basic')"
        >
          <svg class="category-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3 2a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H3z"/>
          </svg>
          <span class="category-label">基础</span>
          <svg class="expand-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M4.5 3L7.5 6L4.5 9"/>
          </svg>
        </div>
        
        <!-- 基础图形展开内容 -->
        <div v-if="isCategoryExpanded('basic')" class="shapes-container">
          <div class="shapes-grid">
            <!-- 第一行 -->
            <div class="shape-item" @click="handleShapeSelect({ type: 'rectangle', name: '矩形' })" title="矩形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="12" rx="2"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'circle', name: '圆形' })" title="圆形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="9"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'diamond', name: '菱形' })" title="菱形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L22 12L12 22L2 12L12 2Z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'square', name: '正方形' })" title="正方形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'ellipse', name: '椭圆' })" title="椭圆">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <ellipse cx="12" cy="12" rx="9" ry="6"/>
              </svg>
            </div>
            
            <!-- 第二行 -->
            <div class="shape-item" @click="handleShapeSelect({ type: 'cylinder', name: '圆柱' })" title="圆柱">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <ellipse cx="12" cy="5" rx="9" ry="3"/>
                <path d="M21 12v7a9 3 0 0 1-18 0v-7"/>
                <path d="M3 5v7a9 3 0 0 0 18 0V5"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'arrow-right', name: '右箭头' })" title="右箭头">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 12h18m-9-9l9 9-9 9"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'folder', name: '文件夹' })" title="文件夹">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'parallelogram', name: '平行四边形' })" title="平行四边形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M6 4h12l4 8-4 8H6l-4-8 4-8z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'trapezoid', name: '梯形' })" title="梯形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M7 4h10l3 16H4l3-16z"/>
              </svg>
            </div>
            
            <!-- 第三行 -->
            <div class="shape-item" @click="handleShapeSelect({ type: 'comment', name: '对话框' })" title="对话框">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'comment-bubble', name: '消息气泡' })" title="消息气泡">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M8 9h8M8 13h6M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'right-triangle', name: '直角三角形' })" title="直角三角形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 21L3 3L21 21L3 21Z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'triangle', name: '三角形' })" title="三角形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L22 20H2L12 2Z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'star', name: '星形' })" title="星形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polygon points="12,2 15,8.5 22,9.3 17,14.1 18.5,21 12,17.8 5.5,21 7,14.1 2,9.3 9,8.5"/>
              </svg>
    </div>
    
            <!-- 第四行 -->
            <div class="shape-item" @click="handleShapeSelect({ type: 'hexagon', name: '六边形' })" title="六边形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 16V8a2 2 0 0 0-1-1.73L14 2a2 2 0 0 0-2 0L6 6.27A2 2 0 0 0 5 8v8a2 2 0 0 0 1 1.73L12 22a2 2 0 0 0 2 0l6-4.27A2 2 0 0 0 21 16z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'pentagon', name: '五边形' })" title="五边形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L22 9L18 22H6L2 9L12 2Z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'octagon', name: '八边形' })" title="八边形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M7.86 2h8.28l5.86 5.86v8.28L16.14 22H7.86L2 16.14V7.86L7.86 2z"/>
              </svg>
        </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'arrow-left', name: '左箭头' })" title="左箭头">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 12H3m9 9l-9-9 9-9"/>
              </svg>
        </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'arrow-right2', name: '箭头' })" title="箭头">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M7 7L17 12L7 17V7Z"/>
              </svg>
      </div>
      
            <!-- 第五行 -->
            <div class="shape-item" @click="handleShapeSelect({ type: 'double-arrow', name: '双向箭头' })" title="双向箭头">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 12h18M8 7l-5 5 5 5M16 7l5 5-5 5"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'cloud', name: '云形' })" title="云形">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'refresh', name: '刷新' })" title="刷新">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 2v6h-6M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                <path d="M3 22v-6h6M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'undo', name: '撤销' })" title="撤销">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 7v6h6M21 17a9 9 0 1 1-9-9 9.75 9.75 0 0 1 6.74 2.74L21 13"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'cube', name: '立方体' })" title="立方体">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="7.5,4.21 12,6.81 16.5,4.21"/>
                <polyline points="7.5,19.79 7.5,14.6 3,12"/>
                <polyline points="21,12 16.5,14.6 16.5,19.79"/>
              </svg>
            </div>
        </div>
        </div>
      </div>
      
      <!-- 直线分类 -->
      <div class="category-section">
        <div 
          class="category-item"
          :class="{ active: isCategoryExpanded('lines') }"
          @click="setActiveCategory('lines')"
        >
          <svg class="category-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 8a.5.5 0 0 1 .5-.5h11a.5.5 0 0 1 0 1h-11A.5.5 0 0 1 2 8z"/>
          </svg>
          <span class="category-label">直线</span>
          <svg class="expand-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M4.5 3L7.5 6L4.5 9"/>
          </svg>
        </div>
        
        <!-- 直线展开内容 -->
        <div v-if="isCategoryExpanded('lines')" class="shapes-container">
          <div class="shapes-grid">
            <div class="shape-item" @click="handleShapeSelect({ type: 'line', name: '直线' })" title="直线">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 12h16"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'dashed-line', name: '虚线' })" title="虚线">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="5,5">
                <path d="M4 12h16"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'arrow-line', name: '箭头线' })" title="箭头线">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 12h16m-4-4l4 4-4 4"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'bezier', name: '贝塞尔曲线' })" title="贝塞尔曲线">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 20C4 20 8 12 12 12C16 12 20 4 20 4"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 泳道分类 -->
      <div class="category-section">
        <div 
          class="category-item"
          :class="{ active: isCategoryExpanded('swimlanes') }"
          @click="setActiveCategory('swimlanes')"
        >
          <svg class="category-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V3zm0 5a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V8zm0 5a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-2z"/>
          </svg>
          <span class="category-label">泳道</span>
          <svg class="expand-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M4.5 3L7.5 6L4.5 9"/>
          </svg>
        </div>
        
        <!-- 泳道展开内容 -->
        <div v-if="isCategoryExpanded('swimlanes')" class="shapes-container">
          <div class="shapes-grid">
            <div class="shape-item" @click="handleShapeSelect({ type: 'horizontal-lane', name: '水平泳道' })" title="水平泳道">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="6" width="20" height="4"/>
                <rect x="2" y="10" width="20" height="4"/>
                <rect x="2" y="14" width="20" height="4"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'vertical-lane', name: '垂直泳道' })" title="垂直泳道">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="6" y="2" width="4" height="20"/>
                <rect x="10" y="2" width="4" height="20"/>
                <rect x="14" y="2" width="4" height="20"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'grid-layout', name: '网格布局' })" title="网格布局">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 流程图分类 -->
      <div class="category-section">
        <div 
          class="category-item"
          :class="{ active: isCategoryExpanded('flowchart') }"
          @click="setActiveCategory('flowchart')"
        >
          <svg class="category-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5 0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8h-5v-.5A.5.5 0 0 1 3 7h5.5V6A1.5 1.5 0 0 1 7 4.5v-1z"/>
          </svg>
          <span class="category-label">流程图</span>
          <svg class="expand-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M4.5 3L7.5 6L4.5 9"/>
          </svg>
        </div>
        
        <!-- 流程图展开内容 -->
        <div v-if="isCategoryExpanded('flowchart')" class="shapes-container">
          <div class="shapes-grid">
            <div class="shape-item" @click="handleShapeSelect({ type: 'process', name: '流程' })" title="流程">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="8" width="18" height="8" rx="2"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'decision', name: '判断' })" title="判断">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L22 12L12 22L2 12L12 2Z"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'start-end', name: '开始/结束' })" title="开始/结束">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="8" width="18" height="8" rx="8"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'document', name: '文档' })" title="文档">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'data', name: '数据' })" title="数据">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M6 4h12l4 8-4 8H6l-4-8 4-8z"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 类图分类 -->
      <div class="category-section">
        <div 
          class="category-item"
          :class="{ active: isCategoryExpanded('class') }"
          @click="setActiveCategory('class')"
        >
          <svg class="category-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 4a4 4 0 1 1 4.5 3.969V13.5a.5.5 0 0 1-1 0V7.97A4 4 0 0 1 4 4zm2.5-.5a2.5 2.5 0 1 0 3 0 2.5 2.5 0 0 0-3 0z"/>
          </svg>
          <span class="category-label">类图</span>
          <svg class="expand-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M4.5 3L7.5 6L4.5 9"/>
          </svg>
        </div>
        
        <!-- 类图展开内容 -->
        <div v-if="isCategoryExpanded('class')" class="shapes-container">
          <div class="shapes-grid">
            <div class="shape-item" @click="handleShapeSelect({ type: 'class', name: '类' })" title="类">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'interface', name: '接口' })" title="接口">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="9" cy="9" r="2"/>
                <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'abstract', name: '抽象类' })" title="抽象类">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
                <text x="12" y="7" text-anchor="middle" font-style="italic" font-size="8">A</text>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'enum', name: '枚举' })" title="枚举">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="7" y1="8" x2="17" y2="8"/>
                <line x1="7" y1="12" x2="17" y2="12"/>
                <line x1="7" y1="16" x2="17" y2="16"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'package', name: '包' })" title="包">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 时序图分类 -->
      <div class="category-section">
        <div 
          class="category-item"
          :class="{ active: isCategoryExpanded('sequence') }"
          @click="setActiveCategory('sequence')"
        >
          <svg class="category-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/>
            <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/>
          </svg>
          <span class="category-label">时序图</span>
          <svg class="expand-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M4.5 3L7.5 6L4.5 9"/>
          </svg>
        </div>
        
        <!-- 时序图展开内容 -->
        <div v-if="isCategoryExpanded('sequence')" class="shapes-container">
          <div class="shapes-grid">
            <div class="shape-item" @click="handleShapeSelect({ type: 'actor', name: '参与者' })" title="参与者">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'lifeline', name: '生命线' })" title="生命线">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <line x1="12" y1="3" x2="12" y2="21"/>
                <rect x="8" y="2" width="8" height="4" rx="1"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'message', name: '消息' })" title="消息">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 12h18m-9-9l9 9-9 9"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'activation', name: '激活框' })" title="激活框">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="10" y="6" width="4" height="12" rx="1"/>
              </svg>
            </div>
            <div class="shape-item" @click="handleShapeSelect({ type: 'note', name: '注释' })" title="注释">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// Props
defineProps<{
  activeTool: string
}>()

// Emits
const emit = defineEmits<{
  toolChange: [tool: string]
  shapeSelect: [shape: any]
  gridToggle: []
  snapToggle: []
  zoomIn: []
  zoomOut: []
  zoomReset: []
}>()

// 状态
const expandedCategories = ref(['basic', 'lines', 'swimlanes', 'flowchart', 'class', 'sequence'])
const searchQuery = ref('')

// 方法
const setActiveCategory = (categoryId: string) => {
  const index = expandedCategories.value.indexOf(categoryId)
  if (index !== -1) {
    expandedCategories.value.splice(index, 1)
  } else {
    expandedCategories.value.push(categoryId)
  }
}

const isCategoryExpanded = (categoryId: string) => {
  return expandedCategories.value.includes(categoryId)
}

const handleShapeSelect = (shape: any) => {
  console.log('选择形状:', shape)
  emit('shapeSelect', shape)
  emit('toolChange', 'shape-' + shape.type)
}
</script>

<style scoped>
.left-sidebar {
  width: 300px;
  background-color: #f8f9fa;
  border-right: 1px solid #e1e4e8;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.search-box {
  padding: 16px;
  border-bottom: 1px solid #e1e4e8;
  background-color: #ffffff;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #656d76;
  z-index: 1;
}

.search-input {
  width: 100%;
  height: 36px;
  padding: 0 12px 0 36px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font-size: 14px;
  background-color: #f6f8fa;
  color: #24292f;
  transition: all 0.15s ease;
}

.search-input:focus {
  outline: none;
  border-color: #1890ff;
  background-color: #ffffff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.search-input::placeholder {
  color: #656d76;
}

.tool-categories {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.category-section {
  margin-bottom: 4px;
}

.category-item {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: #24292f;
  position: relative;
}

.category-item:hover {
  background-color: #f6f8fa;
}

.category-item.active {
  background-color: #f6f8fa;
}

.category-icon {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  color: inherit;
}

.category-label {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
}

.expand-icon {
  width: 12px;
  height: 12px;
  transition: transform 0.15s ease;
  color: #656d76;
}

.category-item.active .expand-icon {
  transform: rotate(90deg);
}

.shapes-container {
  background-color: #ffffff;
  border-top: 1px solid #f1f3f4;
  padding: 16px;
}

.shapes-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.shape-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid #e1e4e8;
  border-radius: 6px;
  background-color: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
  color: #656d76;
}

.shape-item:hover {
  border-color: #1890ff;
  background-color: #f6f8fa;
  color: #1890ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.shape-item:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

/* 滚动条样式 */
.tool-categories::-webkit-scrollbar {
  width: 6px;
}

.tool-categories::-webkit-scrollbar-track {
  background: transparent;
}

.tool-categories::-webkit-scrollbar-thumb {
  background: #d0d7de;
  border-radius: 3px;
}

.tool-categories::-webkit-scrollbar-thumb:hover {
  background: #8b949e;
}
</style> 