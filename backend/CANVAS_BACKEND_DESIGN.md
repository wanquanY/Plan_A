# 飞书风格画板功能后端架构设计文档

## 1. 概述

本文档描述了实现飞书风格画板功能的后端架构设计，基于现有的FastAPI + SQLAlchemy架构，提供专业的画板编辑、协作、版本管理和导出功能。

## 2. 技术栈

### 2.1 核心技术
- **Web框架**: FastAPI 0.100+
- **数据库**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0
- **缓存**: Redis 7.0
- **文件存储**: 本地存储 + CDN（可选）
- **实时通信**: WebSocket + Socket.IO
- **任务队列**: Celery + Redis
- **版本控制**: Git-like 差异算法

### 2.2 依赖包
```toml
[dependencies]
fastapi = ">=0.100.0"
sqlalchemy = ">=2.0.0"
alembic = ">=1.11.0"
redis = ">=4.5.0"
celery = ">=5.3.0"
websockets = ">=11.0"
pillow = ">=10.0.0"
reportlab = ">=4.0.0"
svglib = ">=1.5.0"
pydantic = ">=2.0.0"
```

## 3. 数据库设计

### 3.1 画板核心表结构

#### Canvas（画板文档表）
```sql
CREATE TABLE canvas_documents (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,  -- 对外暴露的ID
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL DEFAULT '未命名画板',
    description TEXT,
    thumbnail_url VARCHAR(500),  -- 缩略图URL
    
    -- 画布配置
    canvas_config JSONB NOT NULL DEFAULT '{
        "width": 1920,
        "height": 1080,
        "background": {
            "type": "solid",
            "color": "#ffffff",
            "image": null
        },
        "grid": {
            "enabled": true,
            "size": 20,
            "color": "#e5e5e5",
            "style": "dot"
        },
        "viewport": {
            "x": 0,
            "y": 0,
            "zoom": 1.0
        }
    }'::jsonb,
    
    -- 访问控制
    visibility VARCHAR(20) DEFAULT 'private',  -- private, shared, public
    share_token VARCHAR(64) UNIQUE,  -- 分享token
    password_hash VARCHAR(128),  -- 访问密码（可选）
    
    -- 协作设置
    collaboration_enabled BOOLEAN DEFAULT true,
    max_collaborators INTEGER DEFAULT 10,
    comment_enabled BOOLEAN DEFAULT true,
    
    -- 导出设置
    export_settings JSONB DEFAULT '{
        "formats": ["png", "svg", "pdf"],
        "quality": "high",
        "dpi": 300
    }'::jsonb,
    
    -- 版本信息
    current_version INTEGER DEFAULT 1,
    
    -- 元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_canvas_documents_user_id ON canvas_documents(user_id);
CREATE INDEX idx_canvas_documents_uuid ON canvas_documents(uuid);
CREATE INDEX idx_canvas_documents_share_token ON canvas_documents(share_token);
CREATE INDEX idx_canvas_documents_updated_at ON canvas_documents(updated_at);
```

#### CanvasElement（画布元素表）
```sql
CREATE TABLE canvas_elements (
    id SERIAL PRIMARY KEY,
    canvas_id INTEGER NOT NULL REFERENCES canvas_documents(id) ON DELETE CASCADE,
    element_uuid VARCHAR(36) NOT NULL,  -- 元素唯一ID
    
    -- 元素类型和数据
    element_type VARCHAR(50) NOT NULL,  -- rectangle, circle, diamond, text, connection, group等
    element_data JSONB NOT NULL,  -- 完整的元素数据
    
    -- 几何属性（用于快速查询和空间索引）
    geometry JSONB NOT NULL DEFAULT '{
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 60,
        "rotation": 0
    }'::jsonb,
    
    -- 样式属性
    style JSONB NOT NULL DEFAULT '{
        "fill": {"color": "#87CEEB", "type": "solid"},
        "stroke": {"color": "#000000", "width": 1},
        "shadow": {"enabled": false},
        "opacity": 1.0
    }'::jsonb,
    
    -- 连接点信息
    connection_points JSONB DEFAULT '[]'::jsonb,
    
    -- 元数据
    metadata JSONB DEFAULT '{
        "locked": false,
        "visible": true,
        "zIndex": 0,
        "layerId": "default",
        "groupId": null,
        "tags": []
    }'::jsonb,
    
    -- 版本控制
    version INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);

-- 索引
CREATE INDEX idx_canvas_elements_canvas_id ON canvas_elements(canvas_id);
CREATE INDEX idx_canvas_elements_uuid ON canvas_elements(element_uuid);
CREATE INDEX idx_canvas_elements_type ON canvas_elements(element_type);
CREATE INDEX idx_canvas_elements_updated_at ON canvas_elements(updated_at);

-- 空间索引（用于快速查找指定区域的元素）
CREATE INDEX idx_canvas_elements_geometry_gin ON canvas_elements USING GIN (geometry);
```

#### CanvasConnection（连接线表）
```sql
CREATE TABLE canvas_connections (
    id SERIAL PRIMARY KEY,
    canvas_id INTEGER NOT NULL REFERENCES canvas_documents(id) ON DELETE CASCADE,
    connection_uuid VARCHAR(36) NOT NULL,
    
    -- 连接信息
    connection_type VARCHAR(50) DEFAULT 'straight',  -- straight, curved, flowline
    source_element_id VARCHAR(36) NOT NULL,
    target_element_id VARCHAR(36) NOT NULL,
    source_point VARCHAR(50),  -- 连接点标识
    target_point VARCHAR(50),
    
    -- 路径数据
    path_data JSONB NOT NULL,  -- 完整的路径信息
    
    -- 样式
    style JSONB DEFAULT '{
        "stroke": {"color": "#000000", "width": 2},
        "arrow": {"start": false, "end": true, "style": "triangle"},
        "dash": {"enabled": false, "pattern": [5, 5]}
    }'::jsonb,
    
    -- 标签
    labels JSONB DEFAULT '[]'::jsonb,
    
    -- 元数据
    metadata JSONB DEFAULT '{
        "locked": false,
        "visible": true,
        "zIndex": 0,
        "layerId": "default"
    }'::jsonb,
    
    version INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);

CREATE INDEX idx_canvas_connections_canvas_id ON canvas_connections(canvas_id);
CREATE INDEX idx_canvas_connections_source ON canvas_connections(source_element_id);
CREATE INDEX idx_canvas_connections_target ON canvas_connections(target_element_id);
```

#### CanvasLayer（图层表）
```sql
CREATE TABLE canvas_layers (
    id SERIAL PRIMARY KEY,
    canvas_id INTEGER NOT NULL REFERENCES canvas_documents(id) ON DELETE CASCADE,
    layer_uuid VARCHAR(36) NOT NULL,
    
    name VARCHAR(100) NOT NULL DEFAULT '图层',
    description TEXT,
    
    -- 图层属性
    visible BOOLEAN DEFAULT true,
    locked BOOLEAN DEFAULT false,
    opacity REAL DEFAULT 1.0,
    blend_mode VARCHAR(20) DEFAULT 'normal',
    
    -- 排序
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);
```

#### CanvasVersion（版本历史表）
```sql
CREATE TABLE canvas_versions (
    id SERIAL PRIMARY KEY,
    canvas_id INTEGER NOT NULL REFERENCES canvas_documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    
    -- 版本信息
    title VARCHAR(255),
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    
    -- 快照数据
    snapshot_data JSONB NOT NULL,  -- 完整的画板快照
    
    -- 变更信息
    changes JSONB,  -- 增量变更记录
    parent_version INTEGER,  -- 父版本号
    
    -- 统计信息
    elements_count INTEGER DEFAULT 0,
    connections_count INTEGER DEFAULT 0,
    file_size BIGINT,  -- 数据大小（字节）
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);

CREATE INDEX idx_canvas_versions_canvas_id ON canvas_versions(canvas_id);
CREATE INDEX idx_canvas_versions_number ON canvas_versions(canvas_id, version_number);
```

### 3.2 协作相关表结构

#### CanvasCollaborator（协作者表）
```sql
CREATE TABLE canvas_collaborators (
    id SERIAL PRIMARY KEY,
    canvas_id INTEGER NOT NULL REFERENCES canvas_documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- 权限级别
    permission_level VARCHAR(20) DEFAULT 'editor',  -- owner, editor, commenter, viewer
    
    -- 协作状态
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive, pending
    last_active_at TIMESTAMP WITH TIME ZONE,
    
    -- 邀请信息
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false,
    
    UNIQUE(canvas_id, user_id)
);
```

#### CanvasComment（评论表）
```sql
CREATE TABLE canvas_comments (
    id SERIAL PRIMARY KEY,
    canvas_id INTEGER NOT NULL REFERENCES canvas_documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- 评论内容
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',  -- text, markdown
    
    -- 位置信息
    position JSONB,  -- 评论在画布上的位置
    target_element_id VARCHAR(36),  -- 关联的元素ID（可选）
    
    -- 回复关系
    parent_comment_id INTEGER REFERENCES canvas_comments(id),
    reply_to_user_id INTEGER REFERENCES users(id),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'open',  -- open, resolved, closed
    resolved_by INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);
```

### 3.3 模板和素材表

#### CanvasTemplate（模板表）
```sql
CREATE TABLE canvas_templates (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- 模板信息
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),  -- flowchart, database, network, uml等
    tags JSONB DEFAULT '[]'::jsonb,
    
    -- 模板数据
    template_data JSONB NOT NULL,  -- 模板的完整画板数据
    preview_image VARCHAR(500),  -- 预览图URL
    
    -- 使用统计
    usage_count INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.0,
    
    -- 可见性
    visibility VARCHAR(20) DEFAULT 'public',  -- public, private, premium
    
    -- 创建者
    created_by INTEGER REFERENCES users(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);
```

#### CanvasAsset（素材资源表）
```sql
CREATE TABLE canvas_assets (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- 资源信息
    name VARCHAR(255) NOT NULL,
    description TEXT,
    asset_type VARCHAR(50),  -- icon, image, shape, symbol
    category VARCHAR(50),
    
    -- 文件信息
    file_url VARCHAR(500),
    file_size BIGINT,
    mime_type VARCHAR(100),
    dimensions JSONB,  -- {"width": 100, "height": 100}
    
    -- SVG数据（对于矢量图标）
    svg_data TEXT,
    
    -- 使用统计
    usage_count INTEGER DEFAULT 0,
    
    -- 可见性
    visibility VARCHAR(20) DEFAULT 'public',
    
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Shanghai', now()),
    is_deleted BOOLEAN DEFAULT false
);
```

## 4. API接口设计

### 4.1 画板管理接口

#### 4.1.1 画板CRUD
```python
# GET /api/v1/canvas/
# 获取用户的画板列表
@router.get("/", response_model=List[CanvasListResponse])
async def get_canvas_list(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取画板列表，支持搜索、分类、排序"""
    pass

# POST /api/v1/canvas/
# 创建新画板
@router.post("/", response_model=CanvasResponse)
async def create_canvas(
    canvas_data: CanvasCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新画板"""
    pass

# GET /api/v1/canvas/{canvas_id}
# 获取画板详情
@router.get("/{canvas_id}", response_model=CanvasDetailResponse)
async def get_canvas(
    canvas_id: str,
    version: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取画板详情，可指定版本"""
    pass

# PUT /api/v1/canvas/{canvas_id}
# 更新画板
@router.put("/{canvas_id}", response_model=CanvasResponse)
async def update_canvas(
    canvas_id: str,
    canvas_data: CanvasUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新画板信息"""
    pass
```

#### 4.1.2 元素操作接口
```python
# POST /api/v1/canvas/{canvas_id}/elements
# 创建元素
@router.post("/{canvas_id}/elements", response_model=ElementResponse)
async def create_element(
    canvas_id: str,
    element_data: ElementCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """在画板中创建新元素"""
    pass

# PUT /api/v1/canvas/{canvas_id}/elements/{element_id}
# 更新元素
@router.put("/{canvas_id}/elements/{element_id}", response_model=ElementResponse)
async def update_element(
    canvas_id: str,
    element_id: str,
    element_data: ElementUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新元素属性"""
    pass

# DELETE /api/v1/canvas/{canvas_id}/elements/{element_id}
# 删除元素
@router.delete("/{canvas_id}/elements/{element_id}")
async def delete_element(
    canvas_id: str,
    element_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除画板元素"""
    pass

# POST /api/v1/canvas/{canvas_id}/elements/batch
# 批量操作元素
@router.post("/{canvas_id}/elements/batch")
async def batch_update_elements(
    canvas_id: str,
    batch_data: ElementBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量创建、更新、删除元素"""
    pass
```

### 4.2 实时协作接口

#### 4.2.1 WebSocket连接
```python
# WebSocket /api/v1/canvas/{canvas_id}/ws
@router.websocket("/{canvas_id}/ws")
async def canvas_websocket(
    websocket: WebSocket,
    canvas_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """画板实时协作WebSocket连接"""
    
    # 1. 验证用户token
    user = await verify_websocket_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # 2. 验证画板访问权限
    canvas = await get_canvas_with_permission(canvas_id, user.id, db)
    if not canvas:
        await websocket.close(code=1008, reason="Canvas not found or no permission")
        return
    
    # 3. 建立连接并加入房间
    await websocket.accept()
    await canvas_manager.join_canvas(canvas_id, user.id, websocket)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            await handle_canvas_message(canvas_id, user.id, data, db)
            
    except WebSocketDisconnect:
        await canvas_manager.leave_canvas(canvas_id, user.id)
```

#### 4.2.2 协作管理
```python
# POST /api/v1/canvas/{canvas_id}/collaborators
# 邀请协作者
@router.post("/{canvas_id}/collaborators")
async def invite_collaborator(
    canvas_id: str,
    invitation: CollaboratorInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """邀请用户成为画板协作者"""
    pass

# GET /api/v1/canvas/{canvas_id}/collaborators
# 获取协作者列表
@router.get("/{canvas_id}/collaborators", response_model=List[CollaboratorResponse])
async def get_collaborators(
    canvas_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取画板协作者列表"""
    pass

# PUT /api/v1/canvas/{canvas_id}/collaborators/{user_id}
# 更新协作者权限
@router.put("/{canvas_id}/collaborators/{user_id}")
async def update_collaborator_permission(
    canvas_id: str,
    user_id: int,
    permission_data: CollaboratorPermissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新协作者权限"""
    pass
```

### 4.3 版本控制接口

```python
# GET /api/v1/canvas/{canvas_id}/versions
# 获取版本历史
@router.get("/{canvas_id}/versions", response_model=List[VersionResponse])
async def get_canvas_versions(
    canvas_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取画板版本历史"""
    pass

# POST /api/v1/canvas/{canvas_id}/versions
# 创建版本快照
@router.post("/{canvas_id}/versions", response_model=VersionResponse)
async def create_version_snapshot(
    canvas_id: str,
    version_data: VersionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建版本快照"""
    pass

# POST /api/v1/canvas/{canvas_id}/versions/{version_id}/restore
# 恢复到指定版本
@router.post("/{canvas_id}/versions/{version_id}/restore")
async def restore_to_version(
    canvas_id: str,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """恢复画板到指定版本"""
    pass
```

### 4.4 导出和分享接口

```python
# POST /api/v1/canvas/{canvas_id}/export
# 导出画板
@router.post("/{canvas_id}/export")
async def export_canvas(
    canvas_id: str,
    export_config: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出画板为指定格式"""
    
    # 异步处理导出任务
    task_id = await create_export_task(canvas_id, export_config, current_user.id)
    background_tasks.add_task(process_export_task, task_id)
    
    return {"task_id": task_id, "status": "processing"}

# GET /api/v1/canvas/{canvas_id}/export/{task_id}
# 获取导出状态
@router.get("/{canvas_id}/export/{task_id}")
async def get_export_status(
    canvas_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取导出任务状态"""
    pass

# POST /api/v1/canvas/{canvas_id}/share
# 生成分享链接
@router.post("/{canvas_id}/share")
async def create_share_link(
    canvas_id: str,
    share_config: ShareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """生成画板分享链接"""
    pass
```

## 5. 核心服务实现

### 5.1 画板服务
```python
# backend/services/canvas_service.py
class CanvasService:
    def __init__(self, db: Session, redis_client: Redis):
        self.db = db
        self.redis = redis_client
    
    async def create_canvas(self, user_id: int, canvas_data: CanvasCreateRequest) -> CanvasDocument:
        """创建新画板"""
        # 1. 创建画板文档
        canvas = CanvasDocument(
            uuid=str(uuid4()),
            user_id=user_id,
            title=canvas_data.title,
            description=canvas_data.description,
            canvas_config=canvas_data.config.dict() if canvas_data.config else None
        )
        
        # 2. 创建默认图层
        default_layer = CanvasLayer(
            canvas_id=canvas.id,
            layer_uuid=str(uuid4()),
            name="默认图层",
            sort_order=0
        )
        
        # 3. 保存到数据库
        self.db.add(canvas)
        self.db.add(default_layer)
        self.db.commit()
        
        # 4. 创建初始版本
        await self.create_version_snapshot(canvas.id, "初始版本", user_id)
        
        return canvas
    
    async def update_elements_batch(
        self, 
        canvas_id: str, 
        operations: List[ElementOperation], 
        user_id: int
    ) -> List[CanvasElement]:
        """批量更新元素"""
        
        # 1. 验证权限
        canvas = await self.get_canvas_with_permission(canvas_id, user_id, "editor")
        
        # 2. 执行批量操作
        updated_elements = []
        for op in operations:
            if op.operation == "create":
                element = await self.create_element(canvas.id, op.data, user_id)
                updated_elements.append(element)
            elif op.operation == "update":
                element = await self.update_element(op.element_id, op.data, user_id)
                updated_elements.append(element)
            elif op.operation == "delete":
                await self.delete_element(op.element_id, user_id)
        
        # 3. 广播变更给所有协作者
        await self.broadcast_canvas_changes(canvas_id, operations, user_id)
        
        # 4. 缓存更新
        await self.update_canvas_cache(canvas_id)
        
        return updated_elements
    
    async def create_version_snapshot(
        self, 
        canvas_id: int, 
        description: str, 
        user_id: int
    ) -> CanvasVersion:
        """创建版本快照"""
        
        # 1. 获取当前画板完整数据
        snapshot_data = await self.get_canvas_full_data(canvas_id)
        
        # 2. 计算与上一版本的差异
        changes = await self.calculate_version_changes(canvas_id, snapshot_data)
        
        # 3. 创建版本记录
        version = CanvasVersion(
            canvas_id=canvas_id,
            version_number=await self.get_next_version_number(canvas_id),
            description=description,
            created_by=user_id,
            snapshot_data=snapshot_data,
            changes=changes,
            elements_count=len(snapshot_data.get("elements", [])),
            connections_count=len(snapshot_data.get("connections", [])),
            file_size=len(json.dumps(snapshot_data).encode())
        )
        
        self.db.add(version)
        self.db.commit()
        
        return version
```

### 5.2 实时协作服务
```python
# backend/services/collaboration_service.py
class CollaborationManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.active_connections: Dict[str, Dict[int, WebSocket]] = {}
        self.user_cursors: Dict[str, Dict[int, CursorPosition]] = {}
    
    async def join_canvas(self, canvas_id: str, user_id: int, websocket: WebSocket):
        """用户加入画板协作"""
        
        # 1. 记录连接
        if canvas_id not in self.active_connections:
            self.active_connections[canvas_id] = {}
        self.active_connections[canvas_id][user_id] = websocket
        
        # 2. 通知其他用户
        await self.broadcast_to_canvas(canvas_id, {
            "type": "user_joined",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }, exclude_user=user_id)
        
        # 3. 发送当前在线用户列表
        online_users = list(self.active_connections[canvas_id].keys())
        await self.send_to_user(canvas_id, user_id, {
            "type": "online_users",
            "users": online_users
        })
    
    async def broadcast_canvas_changes(
        self, 
        canvas_id: str, 
        changes: List[ElementOperation], 
        author_id: int
    ):
        """广播画板变更给所有协作者"""
        
        message = {
            "type": "canvas_changes",
            "changes": [change.dict() for change in changes],
            "author_id": author_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast_to_canvas(canvas_id, message, exclude_user=author_id)
    
    async def update_user_cursor(
        self, 
        canvas_id: str, 
        user_id: int, 
        cursor_data: CursorPosition
    ):
        """更新用户光标位置"""
        
        # 1. 更新本地缓存
        if canvas_id not in self.user_cursors:
            self.user_cursors[canvas_id] = {}
        self.user_cursors[canvas_id][user_id] = cursor_data
        
        # 2. 广播给其他用户
        await self.broadcast_to_canvas(canvas_id, {
            "type": "cursor_update",
            "user_id": user_id,
            "position": cursor_data.dict()
        }, exclude_user=user_id)
    
    async def handle_conflict_resolution(
        self, 
        canvas_id: str, 
        operations: List[ElementOperation]
    ) -> List[ElementOperation]:
        """处理操作冲突解决"""
        
        # 实现操作转换算法（Operational Transformation）
        # 处理并发编辑冲突
        resolved_operations = []
        
        for op in operations:
            # 检查是否与其他用户的操作冲突
            conflicts = await self.detect_conflicts(canvas_id, op)
            
            if conflicts:
                # 应用冲突解决策略
                resolved_op = await self.resolve_conflict(op, conflicts)
                resolved_operations.append(resolved_op)
            else:
                resolved_operations.append(op)
        
        return resolved_operations
```

### 5.3 导出服务
```python
# backend/services/export_service.py
class ExportService:
    def __init__(self):
        self.supported_formats = ["png", "svg", "pdf", "json"]
    
    async def export_canvas_to_png(
        self, 
        canvas_data: Dict, 
        config: ExportConfig
    ) -> bytes:
        """导出画板为PNG格式"""
        
        # 1. 创建高分辨率画布
        width = int(canvas_data["canvas"]["width"] * config.scale)
        height = int(canvas_data["canvas"]["height"] * config.scale)
        
        # 2. 使用PIL创建图像
        from PIL import Image, ImageDraw, ImageFont
        
        image = Image.new("RGB", (width, height), color=config.background_color)
        draw = ImageDraw.Draw(image)
        
        # 3. 渲染所有元素
        for element in canvas_data["elements"]:
            await self.render_element_to_image(draw, element, config.scale)
        
        # 4. 渲染连接线
        for connection in canvas_data["connections"]:
            await self.render_connection_to_image(draw, connection, config.scale)
        
        # 5. 转换为字节流
        import io
        output = io.BytesIO()
        image.save(output, format="PNG", dpi=(config.dpi, config.dpi))
        return output.getvalue()
    
    async def export_canvas_to_svg(
        self, 
        canvas_data: Dict, 
        config: ExportConfig
    ) -> str:
        """导出画板为SVG格式"""
        
        import xml.etree.ElementTree as ET
        
        # 1. 创建SVG根元素
        svg = ET.Element("svg")
        svg.set("width", str(canvas_data["canvas"]["width"]))
        svg.set("height", str(canvas_data["canvas"]["height"]))
        svg.set("xmlns", "http://www.w3.org/2000/svg")
        
        # 2. 添加背景
        if config.include_background:
            background = ET.SubElement(svg, "rect")
            background.set("width", "100%")
            background.set("height", "100%")
            background.set("fill", config.background_color)
        
        # 3. 渲染元素
        for element in canvas_data["elements"]:
            element_svg = await self.render_element_to_svg(element)
            svg.append(element_svg)
        
        # 4. 渲染连接线
        for connection in canvas_data["connections"]:
            connection_svg = await self.render_connection_to_svg(connection)
            svg.append(connection_svg)
        
        return ET.tostring(svg, encoding="unicode")
    
    async def export_canvas_to_pdf(
        self, 
        canvas_data: Dict, 
        config: ExportConfig
    ) -> bytes:
        """导出画板为PDF格式"""
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # 1. 创建PDF画布
        output = io.BytesIO()
        pdf_canvas = canvas.Canvas(output, pagesize=letter)
        
        # 2. 计算缩放比例
        pdf_width, pdf_height = letter
        canvas_width = canvas_data["canvas"]["width"]
        canvas_height = canvas_data["canvas"]["height"]
        
        scale_x = pdf_width / canvas_width
        scale_y = pdf_height / canvas_height
        scale = min(scale_x, scale_y)
        
        # 3. 渲染元素到PDF
        for element in canvas_data["elements"]:
            await self.render_element_to_pdf(pdf_canvas, element, scale)
        
        # 4. 保存PDF
        pdf_canvas.save()
        return output.getvalue()
```

## 6. 部署和监控

### 6.1 Docker配置
```dockerfile
# backend/Dockerfile.canvas
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/uploads /app/exports /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 环境配置
```bash
# backend/.env.canvas
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/canvas_db

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 文件存储配置
UPLOAD_PATH=/app/uploads
EXPORT_PATH=/app/exports
MAX_FILE_SIZE=50MB

# 画板配置
MAX_CANVAS_SIZE=10000
MAX_ELEMENTS_PER_CANVAS=1000
MAX_COLLABORATORS_PER_CANVAS=50

# 导出配置
EXPORT_TIMEOUT=300
MAX_EXPORT_RESOLUTION=4096

# WebSocket配置
WS_CONNECTION_TIMEOUT=300
WS_HEARTBEAT_INTERVAL=30
```

## 7. 性能优化

### 7.1 数据库优化
- 为画板元素的几何属性创建空间索引
- 使用连接池优化数据库连接
- 实现画板数据的分页加载
- 对大型画板使用增量同步

### 7.2 缓存策略
- Redis缓存活跃画板的完整数据
- 缓存用户权限信息
- 缓存模板和素材数据
- 实现多级缓存架构

### 7.3 实时协作优化
- WebSocket连接池管理
- 操作批量化和防抖
- 冲突检测和解决算法
- 网络断线重连机制

## 8. 安全考虑

### 8.1 权限控制
- 基于角色的访问控制（RBAC）
- 画板级别的细粒度权限
- API访问频率限制
- WebSocket连接身份验证

### 8.2 数据安全
- 敏感数据加密存储
- 文件上传安全检查
- XSS和CSRF防护
- SQL注入防护

---

*本文档版本: v1.0*
*创建时间: 2024-12-24*
*更新时间: 2024-12-24* 