# Frontend (Vite + React + TypeScript)

Client for the Video Semantic Search API. See the repository [README.md](../README.md) and [SETUP.md](../SETUP.md) for how to run the stack.

## Commands

```bash
npm install
npm run dev    # http://127.0.0.1:5173 — API URL from VITE_API_BASE (see .env.development)
npm run build
npm run test   # Vitest
```

The Vite dev server proxies `/media` to the backend so previews can load without CORS issues when using that path pattern.
