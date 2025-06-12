# 飞书风格画板功能后端目录结构

## 1. 整体目录结构

```
backend/
├── models/
│   ├── canvas/                     # 画板相关数据模型
│   │   ├── __init__.py
│   │   ├── canvas_document.py      # 画板文档模型
│   │   ├── canvas_element.py       # 画布元素模型
│   │   ├── canvas_connection.py    # 连接线模型
│   │   ├── canvas_layer.py         # 图层模型
│   │   ├── canvas_version.py       # 版本历史模型
│   │   ├── canvas_collaborator.py  # 协作者模型
│   │   ├── canvas_comment.py       # 评论模型
│   │   ├── canvas_template.py      # 模板模型
│   │   └── canvas_asset.py         # 素材资源模型
│   └── ...
│
├── schemas/
│   ├── canvas/                     # 画板相关数据模式
│   │   ├── __init__.py
│   │   ├── canvas_base.py          # 基础数据模式
│   │   ├── canvas_request.py       # 请求数据模式
│   │   ├── canvas_response.py      # 响应数据模式
│   │   ├── element_schemas.py      # 元素相关模式
│   │   ├── collaboration_schemas.py # 协作相关模式
│   │   ├── version_schemas.py      # 版本相关模式
│   │   └── export_schemas.py       # 导出相关模式
│   └── ...
│
├── crud/
│   ├── canvas/                     # 画板CRUD操作
│   │   ├── __init__.py
│   │   ├── canvas_crud.py          # 画板基础CRUD
│   │   ├── element_crud.py         # 元素CRUD
│   │   ├── collaboration_crud.py   # 协作CRUD
│   │   ├── version_crud.py         # 版本CRUD
│   │   └── template_crud.py        # 模板CRUD
│   └── ...
│
├── services/
│   ├── canvas/                     # 画板业务服务
│   │   ├── __init__.py
│   │   ├── canvas_service.py       # 画板核心服务
│   │   ├── collaboration_service.py # 实时协作服务
│   │   ├── version_service.py      # 版本控制服务
│   │   ├── export_service.py       # 导出服务
│   │   ├── template_service.py     # 模板服务
│   │   └── websocket_manager.py    # WebSocket管理器
│   └── ...
│
├── api/
│   └── v1/
│       └── endpoints/
│           ├── canvas/             # 画板API端点
│           │   ├── __init__.py
│           │   ├── canvas_api.py   # 画板主接口
│           │   ├── elements_api.py # 元素操作接口
│           │   ├── collaboration_api.py # 协作接口
│           │   ├── versions_api.py # 版本接口
│           │   ├── export_api.py   # 导出接口
│           │   ├── templates_api.py # 模板接口
│           │   └── websocket_api.py # WebSocket接口
│           └── ...
│
├── utils/
│   ├── canvas/                     # 画板工具函数
│   │   ├── __init__.py
│   │   ├── geometry_utils.py       # 几何计算工具
│   │   ├── export_utils.py         # 导出工具
│   │   ├── conflict_resolution.py  # 冲突解决算法
│   │   ├── canvas_renderer.py      # 画布渲染工具
│   │   └── file_utils.py           # 文件处理工具
│   └── ...
│
├── migrations/
│   ├── canvas/                     # 画板相关数据库迁移
│   │   ├── 001_create_canvas_tables.py
│   │   ├── 002_add_collaboration_tables.py
│   │   ├── 003_add_version_control.py
│   │   └── 004_add_templates_assets.py
│   └── ...
│
└── config/
    ├── canvas_config.py            # 画板相关配置
    └── ...
```

## 2. 核心模块详细说明

### 2.1 数据模型层 (models/canvas/)

#### canvas_document.py - 画板文档模型
```python
"""
画板文档的核心数据模型
- 画板基础信息（标题、描述、配置）
- 画布设置（尺寸、背景、网格）
- 访问控制（可见性、分享、协作）
- 导出设置和版本信息
"""
```

#### canvas_element.py - 画布元素模型
```python
"""
画布上所有元素的数据模型
- 支持多种元素类型（图形、文本、组合）
- 几何属性（位置、尺寸、旋转）
- 样式属性（填充、边框、阴影）
- 连接点和元数据管理
"""
```

#### canvas_connection.py - 连接线模型
```python
"""
元素间连接线的数据模型
- 连接关系（源元素、目标元素、连接点）
- 路径数据（直线、曲线、流程线）
- 样式设置（颜色、粗细、箭头、虚线）
- 标签和元数据
"""
```

### 2.2 数据模式层 (schemas/canvas/)

#### canvas_request.py - 请求数据模式
```python
"""
API请求的数据验证模式
- CanvasCreateRequest: 创建画板请求
- CanvasUpdateRequest: 更新画板请求
- ElementCreateRequest: 创建元素请求
- ElementBatchRequest: 批量操作请求
- CollaboratorInviteRequest: 协作邀请请求
"""
```

#### canvas_response.py - 响应数据模式
```python
"""
API响应的数据模式
- CanvasListResponse: 画板列表响应
- CanvasDetailResponse: 画板详情响应
- ElementResponse: 元素操作响应
- CollaboratorResponse: 协作者信息响应
- VersionResponse: 版本信息响应
"""
```

### 2.3 CRUD操作层 (crud/canvas/)

#### canvas_crud.py - 画板基础CRUD
```python
"""
画板文档的数据库操作
- create_canvas(): 创建新画板
- get_canvas_by_id(): 根据ID获取画板
- get_user_canvases(): 获取用户画板列表
- update_canvas(): 更新画板信息
- delete_canvas(): 删除画板（软删除）
- search_canvases(): 搜索画板
"""
```

#### element_crud.py - 元素CRUD
```python
"""
画板元素的数据库操作
- create_element(): 创建画板元素
- get_canvas_elements(): 获取画板所有元素
- update_element(): 更新元素属性
- delete_element(): 删除元素
- batch_update_elements(): 批量操作元素
- get_elements_in_region(): 获取指定区域内的元素
"""
```

### 2.4 业务服务层 (services/canvas/)

#### canvas_service.py - 画板核心服务
```python
"""
画板核心业务逻辑
- 画板创建、更新、删除逻辑
- 权限验证和访问控制
- 画板数据完整性检查
- 缓存管理和性能优化
"""
```

#### collaboration_service.py - 实时协作服务
```python
"""
多人实时协作功能
- WebSocket连接管理
- 用户在线状态跟踪
- 实时数据同步
- 冲突检测和解决
- 操作转换算法（OT）
"""
```

#### export_service.py - 导出服务
```python
"""
画板导出功能
- PNG/JPG图片导出
- SVG矢量图导出
- PDF文档导出
- JSON数据导出
- 异步任务处理
"""
```

### 2.5 API接口层 (api/v1/endpoints/canvas/)

#### canvas_api.py - 画板主接口
```python
"""
画板管理相关API
- GET /canvas/ - 获取画板列表
- POST /canvas/ - 创建新画板
- GET /canvas/{id} - 获取画板详情
- PUT /canvas/{id} - 更新画板
- DELETE /canvas/{id} - 删除画板
"""
```

#### elements_api.py - 元素操作接口
```python
"""
画板元素操作API
- POST /canvas/{id}/elements - 创建元素
- PUT /canvas/{id}/elements/{element_id} - 更新元素
- DELETE /canvas/{id}/elements/{element_id} - 删除元素
- POST /canvas/{id}/elements/batch - 批量操作
"""
```

#### websocket_api.py - WebSocket接口
```python
"""
实时协作WebSocket接口
- /canvas/{id}/ws - WebSocket连接端点
- 消息类型处理（元素更新、光标移动、用户加入/离开）
- 权限验证和连接管理
"""
```

### 2.6 工具函数层 (utils/canvas/)

#### geometry_utils.py - 几何计算工具
```python
"""
画板几何计算相关工具
- 碰撞检测算法
- 元素位置变换
- 区域重叠计算
- 连接点计算
- 路径优化算法
"""
```

#### export_utils.py - 导出工具
```python
"""
画板导出相关工具
- 图像渲染引擎
- SVG生成器
- PDF生成器
- 文件格式转换
- 压缩和优化
"""
```

## 3. 数据库迁移文件

### 001_create_canvas_tables.py
```python
"""
创建画板核心表
- canvas_documents: 画板文档表
- canvas_elements: 画板元素表
- canvas_connections: 连接线表
- canvas_layers: 图层表
"""
```

### 002_add_collaboration_tables.py
```python
"""
添加协作相关表
- canvas_collaborators: 协作者表
- canvas_comments: 评论表
- canvas_permissions: 权限表
"""
```

### 003_add_version_control.py
```python
"""
添加版本控制表
- canvas_versions: 版本历史表
- canvas_snapshots: 快照数据表
"""
```

### 004_add_templates_assets.py
```python
"""
添加模板和素材表
- canvas_templates: 模板表
- canvas_assets: 素材资源表
- canvas_categories: 分类表
"""
```

## 4. 配置文件

### canvas_config.py
```python
"""
画板功能相关配置
- 画板尺寸限制
- 元素数量限制
- 协作者数量限制
- 导出设置
- WebSocket配置
- 缓存配置
"""
```

## 5. 开发阶段建议

### Phase 1: 基础功能 (Week 1-2)
1. 创建核心数据模型
2. 实现基础CRUD操作
3. 开发画板管理API
4. 实现基础元素操作

### Phase 2: 协作功能 (Week 3-4)
1. 实现WebSocket连接管理
2. 开发实时数据同步
3. 实现权限控制
4. 添加评论功能

### Phase 3: 高级功能 (Week 5-6)
1. 实现版本控制系统
2. 开发导出功能
3. 添加模板和素材管理
4. 性能优化和缓存

### Phase 4: 部署优化 (Week 7-8)
1. 数据库优化和索引
2. 监控和日志系统
3. 安全加固
4. 负载测试和优化

---

*创建时间: 2024-12-24*
*文档版本: v1.0* 