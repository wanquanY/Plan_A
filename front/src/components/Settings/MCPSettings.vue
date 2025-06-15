<template>
  <div class="mcp-settings">
    <!-- 页面头部 -->
    <div class="settings-header">
      <div class="header-content">
        <div class="header-info">
          <h2>
            <ApiOutlined class="header-icon" />
            MCP服务管理
          </h2>
          <p class="settings-description">管理您的MCP（Model Context Protocol）服务器，扩展AI助手的能力</p>
        </div>
      </div>
    </div>

    <!-- MCP状态卡片 -->
    <div class="mcp-status-card">
      <div class="status-header">
        <h3>
          <div class="status-icon">
            <ApiOutlined />
          </div>
          服务状态
        </h3>
        <Button 
          type="primary"
          ghost
          size="small" 
          @click="refreshMCPStatus"
          :loading="statusLoading"
          class="refresh-btn"
        >
          <ReloadOutlined />
          刷新状态
        </Button>
      </div>
      
      <div v-if="statusLoading" class="status-loading">
        <LoadingOutlined />
        <span>检查服务状态中...</span>
      </div>
      
      <div v-else class="status-content">
        <div class="status-grid">
          <div class="status-item">
            <div class="status-value">
              <Tag :color="mcpStatus.enabled ? 'success' : 'error'" size="large">
                {{ mcpStatus.enabled ? '已启用' : '未启用' }}
              </Tag>
            </div>
            <div class="status-label">服务状态</div>
          </div>
          <div class="status-item">
            <div class="status-value">{{ mcpStatus.connected_count || 0 }}</div>
            <div class="status-label">活跃服务器</div>
          </div>
          <div class="status-item">
            <div class="status-value">{{ mcpStatus.server_count || 0 }}</div>
            <div class="status-label">总服务器</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 标签页 -->
    <div class="mcp-tabs-container">
      <Tabs v-model:activeKey="activeTab" class="mcp-tabs" size="large">
        <!-- 公开服务器 -->
        <TabPane key="public">
          <template #tab>
            <span class="tab-title">
              <GlobalOutlined />
              公开服务器
            </span>
          </template>
          
          <div class="tab-content">
            <div class="section-header">
              <div class="section-info">
                <h3>浏览公开的MCP服务器</h3>
                <p>发现社区分享的MCP服务器，一键添加到您的配置中</p>
              </div>
            </div>
            
            <div class="content-toolbar">
              <Input.Search
                v-model:value="publicSearchKeyword"
                placeholder="搜索公开服务器..."
                class="search-input"
                @search="searchPublicServers"
              />
              <Button 
                @click="loadPublicServers" 
                :loading="publicLoading"
                class="toolbar-btn"
              >
                <ReloadOutlined />
                刷新
              </Button>
            </div>

            <div v-if="publicLoading" class="loading-container">
              <LoadingOutlined />
              <span>加载公开服务器中...</span>
            </div>

            <div v-else class="servers-grid">
              <Card 
                v-for="server in filteredPublicServers" 
                :key="server.id"
                class="server-card public-server-card"
                hoverable
              >
                <div class="server-content">
                  <div class="server-header">
                    <div class="server-title">
                      <h4>{{ server.name }}</h4>
                      <div class="server-status-badge">
                        <div 
                          class="status-dot" 
                          :class="getServerStatusClass(server)"
                        ></div>
                        <span class="status-text">{{ getServerStatusText(server) }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div class="server-tags" v-if="server.tags?.length">
                    <Tag v-for="tag in server.tags" :key="tag" size="small" color="blue">
                      {{ tag }}
                    </Tag>
                  </div>
                  
                  <p class="server-description">{{ server.description }}</p>
                  
                  <div class="server-meta">
                    <div class="meta-item">
                      <span class="meta-label">传输类型</span>
                      <Tag :color="server.transport_type === 'stdio' ? 'blue' : 'green'" size="small">
                        {{ server.transport_type }}
                      </Tag>
                    </div>
                    <div class="meta-item">
                      <span class="meta-label">创建时间</span>
                      <span class="meta-value">{{ formatDate(server.created_at) }}</span>
                    </div>
                    <div class="meta-item" v-if="server.tools_count !== undefined">
                      <span class="meta-label">可用工具</span>
                      <span class="meta-value">{{ server.tools_count || 0 }} 个</span>
                    </div>
                  </div>
                  
                  <div class="server-actions">
                    <Button 
                      type="primary" 
                      size="small"
                      @click="addPublicServer(server)"
                      :loading="addingServers.has(server.id)"
                      class="action-btn primary"
                    >
                      <PlusOutlined />
                      添加到我的配置
                    </Button>
                    <Button 
                      size="small"
                      @click="viewServerDetails(server)"
                      class="action-btn"
                    >
                      查看详情
                    </Button>
                  </div>
                </div>
              </Card>
            </div>

            <div v-if="!publicLoading && filteredPublicServers.length === 0" class="empty-state">
              <Empty description="暂无公开服务器" />
            </div>
          </div>
        </TabPane>

        <!-- 我的服务器 -->
        <TabPane key="my">
          <template #tab>
            <span class="tab-title">
              <SettingOutlined />
              我的服务器
            </span>
          </template>
          
          <div class="tab-content">
            <div class="section-header">
              <div class="section-info">
                <h3>我的MCP服务器</h3>
                <p>管理您添加的MCP服务器配置</p>
              </div>
            </div>
            
            <div class="content-toolbar">
              <Input.Search
                v-model:value="mySearchKeyword"
                placeholder="搜索我的服务器..."
                class="search-input"
                @search="searchMyServers"
              />
              <div class="toolbar-actions">
                <Button 
                  @click="loadMyServers" 
                  :loading="myLoading"
                  class="toolbar-btn"
                >
                  <ReloadOutlined />
                  刷新
                </Button>
                <Button 
                  type="primary" 
                  @click="showCreateModal"
                  class="toolbar-btn primary"
                >
                  <PlusOutlined />
                  添加服务器
                </Button>
              </div>
            </div>

            <div v-if="myLoading" class="loading-container">
              <LoadingOutlined />
              <span>加载我的服务器中...</span>
            </div>

            <div v-else class="servers-grid">
              <Card 
                v-for="server in filteredMyServers" 
                :key="server.id"
                class="server-card my-server-card"
              >
                <div class="server-content">
                  <div class="server-header">
                    <div class="server-title">
                      <h4>{{ server.name }}</h4>
                      <div class="server-status-badge">
                        <div 
                          class="status-dot" 
                          :class="getServerStatusClass(server)"
                        ></div>
                        <span class="status-text">{{ getServerStatusText(server) }}</span>
                      </div>
                    </div>
                    <div class="server-switch">
                      <Switch 
                        :checked="server.enabled"
                        @change="toggleServer(server)"
                        :loading="togglingServers.has(server.id)"
                        size="small"
                      />
                    </div>
                  </div>
                  
                  <p class="server-description">{{ server.description }}</p>
                  
                  <div class="server-meta">
                    <div class="meta-row">
                      <Tag :color="server.transport_type === 'stdio' ? 'blue' : 'green'" size="small">
                        {{ server.transport_type }}
                      </Tag>
                      <Tag :color="server.connected ? 'success' : 'error'" size="small" v-if="server.connected !== undefined">
                        {{ server.connected ? '已连接' : '未连接' }}
                      </Tag>
                    </div>
                    <div class="meta-info">
                      <span class="tools-count">
                        <ToolOutlined />
                        {{ server.tools_count || 0 }} 个工具
                      </span>
                      <span class="add-time">{{ formatDate(server.created_at) }}</span>
                    </div>
                  </div>

                  <!-- 工具列表折叠面板 -->
                  <Collapse 
                    v-if="server.tools_count > 0" 
                    class="tools-collapse"
                    ghost
                    size="small"
                    @change="(activeKeys) => onCollapseChange(activeKeys, server)"
                  >
                    <Collapse.Panel key="tools" header="查看可用工具">
                      <div class="tools-loading" v-if="loadingTools.has(server.id)">
                        <LoadingOutlined />
                        <span>加载工具列表...</span>
                      </div>
                      <div v-else-if="serverTools[server.id]?.length" class="tools-list">
                        <div 
                          v-for="tool in serverTools[server.id]" 
                          :key="tool.name"
                          class="tool-item"
                        >
                          <div class="tool-header">
                            <span class="tool-name">{{ tool.name }}</span>
                            <Tag size="small" color="blue">工具</Tag>
                          </div>
                          <p class="tool-description">{{ tool.description }}</p>
                        </div>
                      </div>
                      <div v-else class="no-tools">
                        <span>暂无工具信息</span>
                        <Button 
                          type="link" 
                          size="small"
                          @click="loadServerTools(server)"
                        >
                          重新加载
                        </Button>
                      </div>
                    </Collapse.Panel>
                  </Collapse>
                  
                  <div class="server-actions">
                    <Button 
                      size="small"
                      @click="checkServerStatus(server)"
                      :loading="checkingStatus.has(server.id)"
                      class="action-btn"
                    >
                      <EyeOutlined />
                      检查状态
                    </Button>
                    <Button 
                      size="small"
                      @click="editServer(server)"
                      class="action-btn"
                    >
                      <EditOutlined />
                      编辑
                    </Button>
                    <Button 
                      size="small"
                      danger
                      @click="confirmDeleteServer(server)"
                      class="action-btn danger"
                    >
                      <DeleteOutlined />
                      删除
                    </Button>
                  </div>
                </div>
              </Card>
            </div>

            <div v-if="!myLoading && filteredMyServers.length === 0" class="empty-state">
              <Empty description="您还没有添加任何MCP服务器">
                <Button type="primary" @click="showCreateModal" class="empty-action-btn">
                  <PlusOutlined />
                  立即添加
                </Button>
              </Empty>
            </div>
          </div>
        </TabPane>
      </Tabs>
    </div>

    <!-- 创建/编辑服务器模态框 -->
    <Modal
      v-model:open="createModalVisible"
      :title="editingServer ? '编辑MCP服务器' : '添加MCP服务器'"
      width="600px"
      @ok="submitServer"
      @cancel="cancelEdit"
      :confirmLoading="submitLoading"
      class="server-modal"
    >
      <Form
        ref="serverFormRef"
        :model="serverForm"
        :rules="serverRules"
        layout="vertical"
        class="server-form"
      >
        <Form.Item label="服务器名称" name="name">
          <Input v-model:value="serverForm.name" placeholder="请输入服务器名称" />
        </Form.Item>
        
        <Form.Item label="描述" name="description">
          <Input.TextArea 
            v-model:value="serverForm.description" 
            placeholder="请输入服务器描述"
            :rows="3"
          />
        </Form.Item>
        
        <Form.Item label="传输类型" name="transport_type">
          <Select v-model:value="serverForm.transport_type">
            <Select.Option value="stdio">STDIO</Select.Option>
            <Select.Option value="sse">SSE</Select.Option>
          </Select>
        </Form.Item>
        
        <div v-if="serverForm.transport_type === 'stdio'">
          <Form.Item label="命令" name="command">
            <Input v-model:value="serverForm.command" placeholder="例如: python" />
          </Form.Item>
          
          <Form.Item label="参数">
            <div class="args-input">
              <Input
                v-for="(arg, index) in serverForm.args"
                :key="index"
                v-model:value="serverForm.args[index]"
                placeholder="参数"
                style="margin-bottom: 8px"
              >
                <template #suffix>
                  <Button 
                    type="text" 
                    size="small" 
                    danger
                    @click="removeArg(index)"
                  >
                    <DeleteOutlined />
                  </Button>
                </template>
              </Input>
              <Button type="dashed" @click="addArg" block>
                <PlusOutlined />
                添加参数
              </Button>
            </div>
          </Form.Item>
        </div>
        
        <div v-if="serverForm.transport_type === 'sse'">
          <Form.Item label="URL" name="url">
            <Input v-model:value="serverForm.url" placeholder="https://example.com/mcp" />
          </Form.Item>
        </div>
        
        <Form.Item label="标签">
          <div class="tags-input">
            <Tag
              v-for="tag in serverForm.tags"
              :key="tag"
              closable
              @close="removeTag(tag)"
            >
              {{ tag }}
            </Tag>
            <Input
              v-if="tagInputVisible"
              ref="tagInputRef"
              v-model:value="tagInputValue"
              size="small"
              style="width: 100px"
              @blur="handleTagInputConfirm"
              @keyup.enter="handleTagInputConfirm"
            />
            <Tag v-else @click="showTagInput" style="background: #fff; border-style: dashed;">
              <PlusOutlined />
              添加标签
            </Tag>
          </div>
        </Form.Item>
      </Form>
    </Modal>

    <!-- 服务器详情模态框 -->
    <Modal
      v-model:open="detailModalVisible"
      title="服务器详情"
      width="700px"
      :footer="null"
      class="detail-modal"
    >
      <div v-if="selectedServer" class="server-details">
        <Descriptions :column="2" bordered>
          <Descriptions.Item label="名称">{{ selectedServer.name }}</Descriptions.Item>
          <Descriptions.Item label="传输类型">
            <Tag :color="selectedServer.transport_type === 'stdio' ? 'blue' : 'green'">
              {{ selectedServer.transport_type }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="描述" :span="2">{{ selectedServer.description }}</Descriptions.Item>
          <Descriptions.Item label="命令" v-if="selectedServer.command">
            {{ selectedServer.command }}
          </Descriptions.Item>
          <Descriptions.Item label="参数" v-if="selectedServer.args?.length">
            <Tag v-for="arg in selectedServer.args" :key="arg">{{ arg }}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="URL" v-if="selectedServer.url">
            {{ selectedServer.url }}
          </Descriptions.Item>
          <Descriptions.Item label="标签" v-if="selectedServer.tags?.length">
            <Tag v-for="tag in selectedServer.tags" :key="tag">{{ tag }}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{{ formatDate(selectedServer.created_at) }}</Descriptions.Item>
        </Descriptions>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick } from 'vue';
import { 
  Card, Button, Input, Tabs, TabPane, Tag, Switch, Modal, Form, 
  Select, Empty, message, Descriptions, Collapse 
} from 'ant-design-vue';
import { 
  ApiOutlined, LoadingOutlined, ReloadOutlined, PlusOutlined, 
  DeleteOutlined, GlobalOutlined, SettingOutlined, ToolOutlined, EyeOutlined, EditOutlined 
} from '@ant-design/icons-vue';
import mcpService from '@/services/mcp';
import type { MCPServer, MCPServerCreate } from '@/services/mcp';

// 状态管理
const activeTab = ref('public');
const statusLoading = ref(false);
const publicLoading = ref(false);
const myLoading = ref(false);
const submitLoading = ref(false);

// 搜索关键词
const publicSearchKeyword = ref('');
const mySearchKeyword = ref('');

// 服务器数据
const publicServers = ref<MCPServer[]>([]);
const myServers = ref<MCPServer[]>([]);
const mcpStatus = ref<any>({});

// 操作状态
const addingServers = ref(new Set<string>());
const togglingServers = ref(new Set<string>());
const checkingStatus = ref(new Set<string>());
const loadingTools = ref(new Set<string>());

// 工具数据
const serverTools = ref<Record<string, any[]>>({});

// 模态框状态
const createModalVisible = ref(false);
const detailModalVisible = ref(false);
const editingServer = ref<MCPServer | null>(null);
const selectedServer = ref<MCPServer | null>(null);

// 表单相关
const serverFormRef = ref();
const serverForm = reactive<MCPServerCreate>({
  name: '',
  description: '',
  transport_type: 'stdio',
  command: '',
  args: [],
  url: '',
  tags: []
});

const serverRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入服务器描述', trigger: 'blur' }
  ],
  transport_type: [
    { required: true, message: '请选择传输类型', trigger: 'change' }
  ]
};

// 标签输入
const tagInputVisible = ref(false);
const tagInputValue = ref('');
const tagInputRef = ref();

// 添加防抖标志
const isLoadingMyServers = ref(false);

// 计算属性
const filteredPublicServers = computed(() => {
  if (!publicSearchKeyword.value) return publicServers.value;
  const keyword = publicSearchKeyword.value.toLowerCase();
  return publicServers.value.filter(server => 
    server.name.toLowerCase().includes(keyword) ||
    server.description.toLowerCase().includes(keyword) ||
    server.tags?.some(tag => tag.toLowerCase().includes(keyword))
  );
});

const filteredMyServers = computed(() => {
  if (!mySearchKeyword.value) return myServers.value;
  const keyword = mySearchKeyword.value.toLowerCase();
  return myServers.value.filter(server => 
    server.name.toLowerCase().includes(keyword) ||
    server.description.toLowerCase().includes(keyword) ||
    server.tags?.some(tag => tag.toLowerCase().includes(keyword))
  );
});

// 方法实现
const refreshMCPStatus = async () => {
  try {
    statusLoading.value = true;
    mcpStatus.value = await mcpService.getMCPStatus();
  } catch (error) {
    console.error('获取MCP状态失败:', error);
    message.error('获取MCP状态失败');
  } finally {
    statusLoading.value = false;
  }
};

const loadPublicServers = async () => {
  try {
    publicLoading.value = true;
    const response = await mcpService.getPublicServers();
    publicServers.value = response.servers;
  } catch (error) {
    console.error('加载公开服务器失败:', error);
    message.error('加载公开服务器失败');
  } finally {
    publicLoading.value = false;
  }
};

const loadMyServers = async () => {
  // 防止重复调用
  if (isLoadingMyServers.value) {
    console.log('loadMyServers 已在执行中，跳过此次调用');
    return;
  }
  
  try {
    isLoadingMyServers.value = true;
    myLoading.value = true;
    const response = await mcpService.getUserServers();
    myServers.value = response.servers;
  } catch (error) {
    console.error('加载我的服务器失败:', error);
    message.error('加载我的服务器失败');
  } finally {
    myLoading.value = false;
    isLoadingMyServers.value = false;
  }
};

const searchPublicServers = () => {
  // 搜索逻辑已在计算属性中实现
};

const searchMyServers = () => {
  // 搜索逻辑已在计算属性中实现
};

const addPublicServer = async (server: MCPServer) => {
  try {
    addingServers.value.add(server.id);
    
    const serverData: MCPServerCreate = {
      name: server.name,
      description: server.description,
      transport_type: server.transport_type,
      command: server.command,
      args: server.args,
      url: server.url,
      tags: server.tags
    };
    
    await mcpService.createServer(serverData);
    message.success('服务器添加成功');
    await loadMyServers();
  } catch (error) {
    console.error('添加服务器失败:', error);
    message.error('添加服务器失败');
  } finally {
    addingServers.value.delete(server.id);
  }
};

const viewServerDetails = (server: MCPServer) => {
  selectedServer.value = server;
  detailModalVisible.value = true;
};

const toggleServer = async (server: MCPServer) => {
  try {
    togglingServers.value.add(server.id);
    await mcpService.toggleServer(server.id);
    message.success(`服务器已${server.enabled ? '禁用' : '启用'}`);
    // 重新加载服务器列表以获取最新状态
    await loadMyServers();
  } catch (error) {
    console.error('切换服务器状态失败:', error);
    message.error('切换服务器状态失败');
  } finally {
    togglingServers.value.delete(server.id);
  }
};

const checkServerStatus = async (server: MCPServer) => {
  try {
    checkingStatus.value.add(server.id);
    const status = await mcpService.getServerStatus(server.id);
    
    Modal.info({
      title: `${server.name} 状态`,
      content: `
        连接状态: ${status.connected ? '已连接' : '未连接'}
        初始化状态: ${status.initialized ? '已初始化' : '未初始化'}
        可用工具: ${status.tools.length} 个
        ${status.error ? `错误: ${status.error}` : ''}
      `,
      width: 500
    });
  } catch (error) {
    console.error('检查服务器状态失败:', error);
    message.error('检查服务器状态失败');
  } finally {
    checkingStatus.value.delete(server.id);
  }
};

const loadServerTools = async (server: MCPServer) => {
  try {
    loadingTools.value.add(server.id);
    
    // 现在工具信息已经包含在服务器数据中，直接使用
    if (server.tools && server.tools.length > 0) {
      serverTools.value[server.id] = server.tools;
    } else {
      // 如果没有工具信息，设置为空数组
      serverTools.value[server.id] = [];
    }
  } catch (error) {
    console.error('加载服务器工具失败:', error);
    message.error('加载服务器工具失败');
    serverTools.value[server.id] = [];
  } finally {
    loadingTools.value.delete(server.id);
  }
};

const onCollapseChange = async (activeKeys: string | string[], server: MCPServer) => {
  const keys = Array.isArray(activeKeys) ? activeKeys : [activeKeys];
  
  // 如果展开了工具面板且还没有加载过工具
  if (keys.includes('tools') && !serverTools.value[server.id]) {
    // 如果服务器数据中已经有工具信息，直接使用
    if (server.tools && server.tools.length > 0) {
      serverTools.value[server.id] = server.tools;
    } else {
      // 否则调用loadServerTools来处理（不再调用loadMyServers）
      serverTools.value[server.id] = [];
    }
  }
};

const showCreateModal = () => {
  editingServer.value = null;
  resetServerForm();
  createModalVisible.value = true;
};

const editServer = (server: MCPServer) => {
  editingServer.value = server;
  Object.assign(serverForm, {
    name: server.name,
    description: server.description,
    transport_type: server.transport_type,
    command: server.command || '',
    args: server.args || [],
    url: server.url || '',
    tags: server.tags || []
  });
  createModalVisible.value = true;
};

const resetServerForm = () => {
  Object.assign(serverForm, {
    name: '',
    description: '',
    transport_type: 'stdio',
    command: '',
    args: [],
    url: '',
    tags: []
  });
};

const submitServer = async () => {
  try {
    await serverFormRef.value.validate();
    submitLoading.value = true;
    
    if (editingServer.value) {
      await mcpService.updateServer(editingServer.value.id, serverForm);
      message.success('服务器更新成功');
    } else {
      await mcpService.createServer(serverForm);
      message.success('服务器创建成功');
    }
    
    createModalVisible.value = false;
    await loadMyServers();
  } catch (error) {
    console.error('保存服务器失败:', error);
    message.error('保存服务器失败');
  } finally {
    submitLoading.value = false;
  }
};

const cancelEdit = () => {
  createModalVisible.value = false;
  editingServer.value = null;
  resetServerForm();
};

const confirmDeleteServer = (server: MCPServer) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除服务器 "${server.name}" 吗？此操作不可恢复。`,
    onOk: () => deleteServer(server)
  });
};

const deleteServer = async (server: MCPServer) => {
  try {
    await mcpService.deleteServer(server.id);
    message.success('服务器删除成功');
    await loadMyServers();
  } catch (error) {
    console.error('删除服务器失败:', error);
    message.error('删除服务器失败');
  }
};

const addArg = () => {
  serverForm.args.push('');
};

const removeArg = (index: number) => {
  serverForm.args.splice(index, 1);
};

const showTagInput = () => {
  tagInputVisible.value = true;
  nextTick(() => {
    tagInputRef.value?.focus();
  });
};

const handleTagInputConfirm = () => {
  const value = tagInputValue.value.trim();
  if (value && !serverForm.tags.includes(value)) {
    serverForm.tags.push(value);
  }
  tagInputVisible.value = false;
  tagInputValue.value = '';
};

const removeTag = (tag: string) => {
  const index = serverForm.tags.indexOf(tag);
  if (index > -1) {
    serverForm.tags.splice(index, 1);
  }
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('zh-CN');
};

// 获取服务器状态样式类
const getServerStatusClass = (server: MCPServer) => {
  if (server.connected === true) {
    return 'status-connected';
  } else if (server.connected === false) {
    return 'status-disconnected';
  } else {
    return 'status-unknown';
  }
};

// 获取服务器状态文本
const getServerStatusText = (server: MCPServer) => {
  if (server.connected === true) {
    return '已连接';
  } else if (server.connected === false) {
    return '未连接';
  } else {
    return '状态未知';
  }
};

// 生命周期
onMounted(async () => {
  await Promise.all([
    refreshMCPStatus(),
    loadPublicServers(),
    loadMyServers()
  ]);
});
</script>

<style scoped>
.mcp-settings {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.settings-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  color: white;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
}

.header-content {
  display: flex;
  align-items: center;
}

.header-icon {
  font-size: 28px;
  margin-right: 12px;
  color: rgba(255, 255, 255, 0.9);
}

.header-info h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: white;
  display: flex;
  align-items: center;
}

.settings-description {
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  line-height: 1.5;
}

.mcp-status-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e8e8e8;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.status-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #1890ff, #40a9ff);
  border-radius: 6px;
  color: white;
  font-size: 12px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.refresh-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.status-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: #666;
}

.status-content {
  padding: 16px 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 24px;
}

.status-item {
  text-align: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.status-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.status-label {
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mcp-tabs-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e8e8e8;
}

.mcp-tabs {
  padding: 0;
}

.mcp-tabs :deep(.ant-tabs-nav) {
  background: #fafafa;
  margin: 0;
  padding: 0 24px;
  border-bottom: 1px solid #e8e8e8;
}

.mcp-tabs :deep(.ant-tabs-tab) {
  padding: 16px 24px;
  margin: 0;
  border-radius: 0;
  transition: all 0.3s ease;
}

.mcp-tabs :deep(.ant-tabs-tab-active) {
  background: white;
  border-bottom: 2px solid #1890ff;
}

.tab-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.tab-content {
  padding: 32px;
}

.section-header {
  margin-bottom: 24px;
}

.section-info h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.section-info p {
  margin: 0;
  color: #666;
  font-size: 14px;
  line-height: 1.5;
}

.content-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.search-input {
  width: 300px;
}

.search-input :deep(.ant-input) {
  border-radius: 6px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.toolbar-btn {
  border-radius: 6px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.toolbar-btn.primary {
  background: linear-gradient(135deg, #1890ff, #40a9ff);
  border: none;
  color: white;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 64px;
  color: #666;
}

.servers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.server-card {
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  border: 1px solid #e8e8e8;
}

.server-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.public-server-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border: 1px solid #e6f0ff;
}

.my-server-card {
  background: white;
}

.server-content {
  padding: 20px;
}

.server-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.server-title h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.server-status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  border: 1px solid #e8e8e8;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.connected {
  background: #52c41a;
  box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.2);
}

.status-dot.disconnected {
  background: #ff4d4f;
  box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.2);
}

.status-dot.unknown {
  background: #d9d9d9;
}

.status-text {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.server-switch {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.server-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.server-description {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.server-meta {
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 6px 0;
}

.meta-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-value {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.meta-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.meta-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #666;
}

.tools-count {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  color: #1890ff;
}

.add-time {
  color: #999;
}

.tools-collapse {
  margin-bottom: 16px;
}

.tools-collapse :deep(.ant-collapse-header) {
  padding: 8px 12px !important;
  font-size: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.tools-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  color: #666;
  justify-content: center;
}

.tools-list {
  max-height: 200px;
  overflow-y: auto;
}

.tool-item {
  padding: 8px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  margin-bottom: 8px;
  background: #fafafa;
}

.tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.tool-name {
  font-weight: 500;
  color: #333;
  font-size: 13px;
}

.tool-description {
  font-size: 12px;
  color: #666;
  margin: 0;
  line-height: 1.4;
}

.no-tools {
  text-align: center;
  padding: 16px;
  color: #999;
  font-size: 12px;
}

.server-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 80px;
  border-radius: 6px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
}

.action-btn:hover {
  transform: translateY(-1px);
}

.action-btn.primary {
  background: linear-gradient(135deg, #1890ff, #40a9ff);
  border: none;
  color: white;
}

.action-btn.danger:hover {
  background: #ff4d4f;
  border-color: #ff4d4f;
  color: white;
}

.empty-state {
  text-align: center;
  padding: 64px 32px;
}

.empty-action-btn {
  margin-top: 16px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.server-modal :deep(.ant-modal-content) {
  border-radius: 12px;
  overflow: hidden;
}

.server-modal :deep(.ant-modal-header) {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border-bottom: 1px solid #e6f0ff;
}

.server-form {
  padding: 0;
}

.args-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tags-input {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.detail-modal :deep(.ant-modal-content) {
  border-radius: 12px;
}

.server-details {
  padding: 16px 0;
}

@media (max-width: 1200px) {
  .servers-grid {
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  }
}

@media (max-width: 768px) {
  .mcp-settings {
    padding: 16px;
  }
  
  .settings-header {
    padding: 24px;
  }
  
  .tab-content {
    padding: 20px;
  }
  
  .content-toolbar {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .search-input {
    width: 100%;
  }
  
  .servers-grid {
    grid-template-columns: 1fr;
  }
  
  .server-actions {
    flex-direction: column;
  }
  
  .action-btn {
    min-width: auto;
  }
}

@media (max-width: 480px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .server-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .meta-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style> 