import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// /api 代理到 Django 后端，绕开跨域
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
