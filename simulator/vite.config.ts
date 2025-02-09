import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',  // Allow external access
    allowedHosts: [
      'mac.tail12403c.ts.net',  // Your Tailscale domain
      'localhost',
      '127.0.0.1'
    ]
  }
})