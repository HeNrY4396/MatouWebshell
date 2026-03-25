import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools({
      componentInspector: true,
      launchEditor: 'cursor',
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    hmr: {
      port: 5173,
    },
    fs: {
      strict: false,
    },
    cacheDir: './.vite', // 指定缓存目录为项目内的 .vite 文件夹
  },
  build: {
    // 为生产环境构建配置
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
})
