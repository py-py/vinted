# web — Vinted admin UI

React SPA for the Vinted resale tracker: browse purchased items, set their sale status,
see spend/sell-through stats. Talks only to the FastAPI app in `../vinted/admin`
(JSON under `/api`); there is no other backend.

Stack: React 19, TypeScript 6, Vite 8, Tailwind 4, shadcn/ui (radix-nova preset),
TanStack Query, React Router 8, Recharts (via shadcn `chart`), Lucide icons.

## Commands

```bash
npm run dev       # :5173, proxies /api → API_URL (default http://localhost:8000)
npm run build     # tsc -b && vite build → dist/
npm run lint      # oxlint
npm run gen:api   # regenerate src/types/api.ts from the FastAPI OpenAPI schema
```

From the repo root: `make build` once, then `make run` (API in Docker on `DEV_PORT`, default
8000, + Vite on 5173; Ctrl+C stops both). `make admin-web` / `make web-dev` run one side.
Done = `npm run build` and `npm run lint` pass, and the page was checked in a browser.

## Layout

- `src/pages/` — one file per route: `Dashboard` (`/`), `Items` (`/items`), `Purchases` (`/purchases`).
- `src/components/layout/` — `AdminLayout` (sidebar + header + `<Outlet/>`), `AppSidebar` (nav list).
- `src/components/shared/` — app components reused across pages (`StatusSelect`, `ItemCard`,
  `Pagination`, `SearchInput`, `PurchaseSheet`, …).
- `src/components/ui/` — shadcn-generated; add via `npx shadcn@latest add <name>`, don't hand-edit
  unless necessary. Lint warnings there are expected.
- `src/lib/api.ts` — the only place that calls `fetch`; type aliases over the generated schema.
- `src/lib/status.ts` — sale status labels, colors and display order.
- `src/types/api.ts` — **generated**, never edit by hand.

## Nuances

- **API types come from the backend.** After changing Pydantic models or routes in
  `vinted/admin/api.py`, run `npm run gen:api` and commit the regenerated `src/types/api.ts`.
  `openapi-typescript` runs via `npx` (not a devDependency) because its peer dep is TS 5.
- **Auth.** Everything (API and SPA) is behind HTTP Basic auth. In dev the Vite proxy reads
  `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `../.env` and adds the header itself, so the browser
  never prompts. In production the browser prompts once and sends credentials same-origin.
- **Real data.** The dev API reads the production Firestore. GETs are safe; changing a sale
  status (`PATCH /api/items/{tx}/{item}`) writes to it — don't click status dropdowns while
  testing unless that's intended.
- **Port 8000 may be taken** locally (ssh tunnel); start the API elsewhere and set `API_URL`.
- **Filters live in the URL** (`useUrlParams` in `src/hooks/use-url-params.ts`): `q`, `status`,
  `page`, `from`, `to`, `tx` (open purchase). Changing a filter resets `page`.
- **Server-side filtering.** `/api/items` filters and paginates on the server; `/api/purchases`
  filters on the server and the page paginates client-side. The backend loads all of Firestore per
  request, so keep requests few (TanStack Query `staleTime` is 30s).
- **After a mutation** `StatusSelect` invalidates all queries, so Dashboard stats and lists refresh.
- **Sale statuses** mirror `SaleStatus` in `vinted/account/orders/models.py`. Adding one means:
  backend enum → `gen:api` → `STATUSES` + `STATUS_ORDER` in `src/lib/status.ts`.
- **Vinted images** are hot-linked from the Vinted CDN; keep `referrerPolicy="no-referrer"` on `<img>`.
- **Layout gotcha:** `SidebarInset` needs `min-w-0`, otherwise charts/tables push the page wider
  than the viewport.
- **Production serving.** FastAPI serves `dist/` via `app.frontend("/")` (path from `WEB_DIST`);
  the Docker image builds it in a `node` stage into `/srv/web`. Client routes work on reload
  because FastAPI falls back to `index.html` for browser navigations.

## Style

- Match existing files: double quotes, no semicolons, `@/` imports, function components,
  named exports (except `App`).
- Tailwind + shadcn tokens (`bg-muted`, `text-muted-foreground`, …); no custom CSS files.
- Money via `formatMoney` in `src/lib/format.ts` (pl-PL formatting).
- Responsive down to 375px wide; check there's no horizontal page scroll on mobile.
- Charts: neutral `--chart-*` theme colors, single-series bars, tooltips on hover.
