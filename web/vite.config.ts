import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, /api goes to the FastAPI server (uv run uvicorn server.api:app --port 8000)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
