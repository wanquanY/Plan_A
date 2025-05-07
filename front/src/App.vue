<script setup lang="ts">
// 不需要任何代码，仅作为路由容器
</script>

<template>
  <div class="app-container">
    <router-view />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol',
    'Noto Color Emoji';
  background-color: #f8fafc;
  overflow: auto;
}

body {
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

#app {
  min-height: 100vh;
  width: 100vw;
  overflow-x: hidden;
  position: relative;
  margin: 0;
  padding: 0;
}

.app-container {
  min-height: 100vh;
  width: 100vw;
  max-width: 100%;
  position: relative;
  margin: 0;
  padding: 0;
}

@media (min-width: 1200px) {
  .app-container {
    margin: 0 auto;
  }
}
</style>
