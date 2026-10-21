import { defineConfig } from 'vite';
export default defineConfig({
  base: '/admin-web/',
  server: { proxy: { '/api': { target: process.env.ADMIN_API_URL || 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '') } } }
});
