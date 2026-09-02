import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'lucide-react',
      'recharts',
      'axios',
      'firebase/app',
      'firebase/auth',
    ],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-charts': ['recharts'],
          'vendor-icons': ['lucide-react'],
          'vendor-firebase': ['firebase/app', 'firebase/auth'],
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
    // Dev proxy: forwards /api/* to the Render backend when no local backend is running.
    // Switch VITE_API_BASE_URL in .env to http://localhost:8000/api/v1 to use a local backend instead.
    proxy: {
      '/api': {
        target: 'https://financial-report-analyzer-a7q5.onrender.com',
        changeOrigin: true,
        secure: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.warn('[Vite Proxy] Render backend not reachable:', err.message);
          });
        },
      },
    },
  },
});

