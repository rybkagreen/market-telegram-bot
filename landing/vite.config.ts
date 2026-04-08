import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('motion')) return 'motion'
          if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) return 'vendor'
          return undefined
        },
      },
    },
  },
  server: {
    port: 5175,
    host: true,
  },
})
