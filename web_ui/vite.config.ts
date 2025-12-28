import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Keep paths relative so the app works when served by Python SimpleHTTP.
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
