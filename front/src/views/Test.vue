<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import CodeBlock from '../components/rendering/CodeBlock.vue';
import MermaidDiagram from '../components/rendering/MermaidDiagram.vue';
import MarkMap from '../components/rendering/MarkMap.vue';
import CanvasCore from '../components/Canvas/CanvasCore.vue';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import Sidebar from '../components/Sidebar.vue';
import authService from '../services/auth';
import chatService from '../services/chat';

// 侧边栏相关状态
const router = useRouter();
const username = ref('用户');
const sidebarCollapsed = ref(false);
const activeTab = ref('test');
const sessions = ref([]);
const editorTitle = ref('渲染测试');
const currentSessionId = ref(null);

// 从token中解析用户名
onMounted(() => {
  const token = localStorage.getItem('access_token') || '';
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.sub) {
        username.value = payload.sub;
      }
    } catch (e) {
      console.error('解析token失败', e);
    }
  }
  
  // 获取会话列表
  fetchSessions();
});

// 获取会话列表
const fetchSessions = async () => {
  try {
    const sessionsData = await chatService.getSessions();
    if (sessionsData) {
      sessions.value = sessionsData;
    }
  } catch (error) {
    console.error('获取会话列表失败:', error);
  }
};

// 侧边栏事件处理
const handleLogout = () => {
  authService.logout();
  router.push('/login');
};

const handleTabSwitch = (tab) => {
  if (tab !== 'test') {
    router.push(tab === 'notes' || tab === 'sessions' ? '/' : `/${tab}`);
  }
};

const handleSessionClick = (sessionId) => {
  router.push('/');
};

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
};

const handleNewNote = () => {
  router.push('/');
};

// 定义示例代码块内容
const pythonCode = `def hello_world():
    print("Hello, World!")
    return True

# 调用函数
result = hello_world()
print(f"函数返回结果: {result}")`;

const javascriptCode = `function calculateSum(a, b) {
  return a + b;
}

// 使用箭头函数
const multiply = (a, b) => a * b;

// 测试函数
console.log(calculateSum(5, 3));  // 输出: 8
console.log(multiply(4, 6));      // 输出: 24`;

const htmlCode = `<!DOCTYPE html>
<html>
<head>
  <title>简单的HTML示例</title>
  <style>
    body { font-family: Arial, sans-serif; }
    .container { max-width: 800px; margin: 0 auto; }
    button { padding: 8px 16px; background: #4CAF50; color: white; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Hello World</h1>
    <p>这是一个段落</p>
    <button onclick="alert('按钮被点击了!')">点击我</button>
  </div>
</body>
</html>`;

// 定义示例mermaid图表内容
const flowchartMermaid = `graph TD
    A[开始] --> B{是否已登录?}
    B -->|是| C[显示用户面板]
    B -->|否| D[显示登录表单]
    C --> E[用户操作]
    D --> F[登录处理]
    F -->|成功| C
    F -->|失败| G[显示错误信息]
    G --> D`;

const sequenceMermaid = `sequenceDiagram
    participant U as 用户
    participant C as 客户端
    participant S as 服务器
    participant DB as 数据库
    U->>C: 输入用户名密码
    C->>S: 发送登录请求
    S->>DB: 验证用户凭据
    DB-->>S: 返回验证结果
    S-->>C: 返回登录结果
    C-->>U: 显示登录状态`;

const classDiagramMermaid = `classDiagram
    class Animal {
        +String name
        +int age
        +makeSound() void
    }
    class Dog {
        +String breed
        +wagTail() void
    }
    class Cat {
        +String color
        +purr() void
    }
    Animal <|-- Dog
    Animal <|-- Cat`;

// 定义示例思维导图内容
const markdownMapSimple = `# FreeWrite应用
## 前端功能
### 编辑器
- 富文本编辑
- Markdown支持
- 代码高亮
### AI助手
- 智能对话
- 内容生成
- 上下文理解
### 数据管理
- 笔记保存
- 会话记录
- 导入导出

## 后端功能
### 用户认证
- 登录注册
- JWT认证
- 权限控制
### 数据存储
- PostgreSQL
- 文件存储
- 缓存机制
### API服务
- RESTful API
- 流式响应
- 安全防护`;

const markdownMapComplex = `# 人工智能技术概览
## 机器学习
### 监督学习
- 分类算法
  - 决策树
  - 随机森林
  - 支持向量机
- 回归算法
  - 线性回归
  - 逻辑回归
  - 多项式回归
### 无监督学习
- 聚类
  - K-means
  - DBSCAN
  - 层次聚类
- 降维
  - PCA
  - t-SNE
  - 自编码器
### 强化学习
- 策略梯度
- Q-learning
- 深度强化学习

## 深度学习
### 神经网络
- 前馈神经网络
- 卷积神经网络(CNN)
- 循环神经网络(RNN)
### 自然语言处理
- 词嵌入
  - Word2Vec
  - GloVe
  - BERT
- 语言模型
  - GPT系列
  - T5
  - LLaMA
### 计算机视觉
- 图像分类
- 目标检测
- 图像生成
  - GANs
  - Diffusion Models
  - VAEs

## 应用领域
### 医疗健康
- 疾病诊断
- 药物研发
- 医学影像分析
### 金融科技
- 风险评估
- 欺诈检测
- 算法交易
### 智能制造
- 质量控制
- 预测性维护
- 供应链优化`;

// 转换后的HTML
const renderedContent = ref('');

// 生成带有代码块和mermaid图表的示例内容
onMounted(() => {
  // 使用marked转换含有代码块和mermaid的markdown
  const markdown = `
# 代码块和图表渲染测试

## 代码块示例

### Python 代码
\`\`\`python
${pythonCode}
\`\`\`

### JavaScript 代码
\`\`\`javascript
${javascriptCode}
\`\`\`

### HTML 代码
\`\`\`html
${htmlCode}
\`\`\`

## Mermaid图表示例

### 流程图
\`\`\`mermaid
${flowchartMermaid}
\`\`\`

### 序列图
\`\`\`mermaid
${sequenceMermaid}
\`\`\`

### 类图
\`\`\`mermaid
${classDiagramMermaid}
\`\`\`

## 思维导图示例

### FreeWrite应用思维导图
\`\`\`markdown
${markdownMapSimple}
\`\`\`

### AI技术概览思维导图
\`\`\`markdown
${markdownMapComplex}
\`\`\`
`;

  // 使用marked将markdown转换为HTML
  const html = marked(markdown);
  
  // 安全处理
  renderedContent.value = DOMPurify.sanitize(html, {
    ADD_ATTR: ['class', 'data-language', 'id'],
    ADD_TAGS: ['code', 'pre', 'div']
  });
});

// 在组件挂载后渲染mermaid图表
const renderMermaidDiagrams = () => {
  try {
    // 这里不需要实现具体逻辑，因为我们将会使用MermaidDiagram组件
    console.log('渲染mermaid图表');
  } catch (error) {
    console.error('渲染mermaid图表失败:', error);
  }
};

// 处理导航到其他页面
const handleNavigation = (path) => {
  router.push(path);
};
</script>

<template>
  <div class="notebook-layout">
    <!-- 使用侧边栏组件，与Home页面保持一致 -->
    <Sidebar 
      :username="username"
      :editor-title="editorTitle"
      :sessions="sessions"
      :active-tab="activeTab"
      :current-session-id="currentSessionId"
      :collapsed="sidebarCollapsed"
      @logout="handleLogout"
      @switch-tab="handleTabSwitch"
      @session-click="handleSessionClick"
      @toggle-sidebar="toggleSidebar"
      @new-note="handleNewNote"
      @nav-to="handleNavigation"
    />
    
    <!-- 主内容区 -->
    <div class="main-content">
      <div class="test-container">
        <h1>渲染测试页面</h1>
        
        <div class="test-sections">
          <div class="section">
            <h2>代码块组件测试</h2>
            
            <h3>Python 代码</h3>
            <CodeBlock language="python" :code="pythonCode" />
            
            <h3>JavaScript 代码</h3>
            <CodeBlock language="javascript" :code="javascriptCode" />
            
            <h3>HTML 代码</h3>
            <CodeBlock language="html" :code="htmlCode" />
          </div>
          
          <div class="section">
            <h2>Mermaid图表组件测试</h2>
            
            <h3>流程图</h3>
            <MermaidDiagram :chart="flowchartMermaid" chart-type="flowchart" />
            
            <h3>序列图</h3>
            <MermaidDiagram :chart="sequenceMermaid" chart-type="sequence" />
            
            <h3>类图</h3>
            <MermaidDiagram :chart="classDiagramMermaid" chart-type="class" />
          </div>
          
          <div class="section">
            <h2>思维导图组件测试</h2>
            
            <h3>简单思维导图</h3>
            <MarkMap :content="markdownMapSimple" height="400px" />
            
            <h3>复杂思维导图</h3>
            <MarkMap :content="markdownMapComplex" height="600px" />
          </div>
          
          <div class="section">
            <h2>画板组件测试</h2>
            <p>这是画板组件测试，您可以绘制各种图形元素，选中元素时会显示浮动工具栏。</p>
            <div class="canvas-test-container">
              <CanvasCore 
                canvas-id="test-canvas"
                :width="800"
                :height="400"
              />
            </div>
            <div class="canvas-instructions">
              <h4>使用说明：</h4>
              <ul>
                <li>点击画布创建矩形</li>
                <li>选中元素后会显示浮动工具栏</li>
                <li>可以更改元素类型、填充色、边框等</li>
                <li>点击三个点图标打开详细属性面板</li>
              </ul>
            </div>
          </div>

          <div class="section">
            <h2>Markdown渲染测试</h2>
            <div class="markdown-content" v-html="renderedContent"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 共享Home页面的布局样式 */
.notebook-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  background-color: #f9f9f9;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: auto;
  background-color: white;
  position: relative;
  transition: margin-left 0.3s ease;
  margin-left: 0;
}

/* 测试页面的特定样式 */
.test-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  overflow-y: auto;
  height: 100%;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.test-sections {
  display: flex;
  flex-direction: column;
  gap: 40px;
  padding-bottom: 40px;
}

.section {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-top: 0;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
  color: #1677ff;
}

h3 {
  margin-top: 20px;
  margin-bottom: 10px;
  color: #333;
}

.markdown-content {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  border: 1px solid #eee;
}

/* 画板测试容器样式 */
.canvas-test-container {
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.canvas-instructions {
  background-color: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 6px;
  padding: 16px;
  margin-top: 16px;
}

.canvas-instructions h4 {
  margin: 0 0 12px 0;
  color: #24292e;
  font-size: 14px;
  font-weight: 600;
}

.canvas-instructions ul {
  margin: 0;
  padding-left: 20px;
}

.canvas-instructions li {
  margin-bottom: 6px;
  color: #586069;
  font-size: 13px;
  line-height: 1.5;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .test-container {
    padding: 15px;
  }
  
  .canvas-test-container {
    padding: 12px;
  }
}
</style> 