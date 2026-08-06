import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 개발 중 API는 FastAPI(8000)로 넘긴다 — 프론트는 상대경로만 쓴다
    proxy: {
      '/roadmap': 'http://127.0.0.1:8000',
      '/report': 'http://127.0.0.1:8000',
      '/depts': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/me': 'http://127.0.0.1:8000',
    },
  },
})
