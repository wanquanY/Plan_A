import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
  },
  resolve: {
    alias: {
      '@': '/src',
    }
  },
  optimizeDeps: {
    include: ['tinymce/tinymce'],
  },
  build: {
    target: 'esnext',
    chunkSizeWarningLimit: 1600,
  },
})
