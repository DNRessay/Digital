import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxies API calls to a local Django dev server so the browser sees
    // everything as same-origin — the backend's session/CSRF cookies use
    // SameSite=None;Secure in production (see backend/config/settings.py),
    // which only works over HTTPS, so a genuinely cross-origin plain-HTTP
    // localhost setup can't carry them. Leave VITE_API_BASE_URL unset
    // locally so requests go out as relative paths and hit this proxy.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
