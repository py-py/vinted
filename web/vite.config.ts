import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Reuse the backend's ADMIN_USERNAME / ADMIN_PASSWORD from ../.env so the dev proxy
  // can authenticate itself instead of the browser prompting for Basic auth.
  const env = loadEnv(mode, '..', 'ADMIN_')
  const auth =
    env.ADMIN_USERNAME && env.ADMIN_PASSWORD
      ? `Basic ${Buffer.from(`${env.ADMIN_USERNAME}:${env.ADMIN_PASSWORD}`).toString('base64')}`
      : undefined

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(import.meta.dirname, './src') },
    },
    server: {
      // FastAPI dev server (`make admin-web`); override with API_URL=http://host:port.
      proxy: {
        '/api': {
          target: process.env.API_URL ?? 'http://localhost:8000',
          headers: auth ? { Authorization: auth } : undefined,
        },
      },
    },
  }
})
