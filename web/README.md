# web

Admin UI for the Vinted resale tracker: React + TypeScript + Vite + Tailwind + shadcn/ui.

```bash
npm install
npm run dev       # http://localhost:5173, proxies /api to FastAPI (API_URL, default :8000)
npm run gen:api   # regenerate src/types/api.ts from the FastAPI OpenAPI schema
npm run build
```

The dev proxy reads `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `../.env` and sends them as
Basic auth, so the browser doesn't prompt.
