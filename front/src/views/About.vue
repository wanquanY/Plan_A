<template>
  <div class="site-layout-content">
    <a-card title="关于FreeWrite" style="width: 100%">
      <p>FreeWrite是一个简单的写作和待办事项应用。</p>
      <p>这个应用使用了以下技术栈：</p>
      <a-descriptions bordered>
        <a-descriptions-item label="前端框架">Vue 3</a-descriptions-item>
        <a-descriptions-item label="UI库">Ant Design Vue</a-descriptions-item>
        <a-descriptions-item label="构建工具">Vite</a-descriptions-item>
        <a-descriptions-item label="后端框架">FastAPI</a-descriptions-item>
        <a-descriptions-item label="数据库">PostgreSQL</a-descriptions-item>
      </a-descriptions>
    </a-card>
  </div>
</template>

<style scoped>
.site-layout-content {
  background: #fff;
  padding: 24px;
  min-height: 280px;
}
</style> 