import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({
    plugins: [react(), tailwindcss()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    base: './', // Относительные пути для assets
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8001',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
        sourcemap: true,
    },
});
