import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useDeferredValue } from "react"

import { PageHeader } from "@/components/shared/PageHeader"
import { Pagination } from "@/components/shared/Pagination"
import { PurchaseSheet } from "@/components/shared/PurchaseSheet"
import { SearchInput } from "@/components/shared/SearchInput"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useUrlParams } from "@/hooks/use-url-params"
import { api, type Purchase, type SaleStatus } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { STATUS_ORDER } from "@/lib/status"

const PAGE_SIZE = 25

export function PurchasesPage() {
  const [params, update] = useUrlParams()
  const q = params.get("q") ?? ""
  const dateFrom = params.get("from") ?? ""
  const dateTo = params.get("to") ?? ""
  const page = Number(params.get("page")) || 1
  const selectedTx = params.get("tx")
  const deferredQ = useDeferredValue(q)

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["purchases", { q: deferredQ, dateFrom, dateTo }],
    queryFn: () => api.purchases({ q: deferredQ, dateFrom, dateTo }),
    placeholderData: keepPreviousData,
  })
  const pages = data ? Math.max(1, Math.ceil(data.length / PAGE_SIZE)) : 1
  const rows = data?.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) ?? []
  const selected = data?.find((p) => p.tx_id === selectedTx)
  const hasFilters = Boolean(q || dateFrom || dateTo)

  // `tx` only opens the sheet, so keep the current page when toggling it.
  const select = (tx: string) => update({ tx, page: params.get("page") ?? "" })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Purchases"
        description={data ? `${data.length} orders` : "Orders bought on Vinted"}
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          placeholder="Search seller or item title…"
          value={q}
          onChange={(value) => update({ q: value })}
        />
        <div className="flex w-full items-center gap-2 text-sm sm:w-auto">
          <Input
            type="date"
            aria-label="From date"
            className="min-w-0 flex-1 sm:w-auto sm:flex-none"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(e) => update({ from: e.target.value })}
          />
          <span className="text-muted-foreground">–</span>
          <Input
            type="date"
            aria-label="To date"
            className="min-w-0 flex-1 sm:w-auto sm:flex-none"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => update({ to: e.target.value })}
          />
        </div>
        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={() => update({ q: "", from: "", to: "" })}>
            Reset
          </Button>
        )}
      </div>

      {isError ? (
        <p className="text-sm text-destructive">Failed to load purchases: {error.message}</p>
      ) : isPending ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No purchases match the filters.</p>
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Seller</TableHead>
                <TableHead>Items</TableHead>
                <TableHead className="hidden md:table-cell">Status</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((p) => (
                <PurchaseRow key={p.tx_id} purchase={p} onSelect={() => select(p.tx_id)} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Pagination page={page} pages={pages} onPageChange={(p) => update({ page: String(p) })} />

      <PurchaseSheet purchase={selected} onOpenChange={(open) => !open && select("")} />
    </div>
  )
}

function PurchaseRow({ purchase: p, onSelect }: { purchase: Purchase; onSelect: () => void }) {
  const counts = new Map<SaleStatus, number>()
  p.items.forEach((i) => counts.set(i.status, (counts.get(i.status) ?? 0) + 1))

  return (
    <TableRow
      className="cursor-pointer"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
    >
      <TableCell className="whitespace-nowrap tabular-nums">
        <span className="hidden sm:inline">{p.order_date.slice(0, 4)}-</span>
        {p.order_date.slice(5, 10)}
      </TableCell>
      <TableCell>
        <div className="font-medium">{p.seller_login || "—"}</div>
        {p.seller_country && (
          <div className="text-xs text-muted-foreground">{p.seller_country}</div>
        )}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div className="hidden -space-x-2 sm:flex">
            {p.items.slice(0, 4).map((i) => (
              <img
                key={i.id}
                src={i.photo_urls[0]}
                alt=""
                className="size-8 rounded-md bg-muted object-cover ring-2 ring-background"
                referrerPolicy="no-referrer"
              />
            ))}
          </div>
          <span className="text-sm text-muted-foreground tabular-nums">{p.items.length}</span>
        </div>
      </TableCell>
      <TableCell className="hidden md:table-cell">
        <div className="flex flex-wrap gap-1">
          {STATUS_ORDER.filter((s) => counts.has(s)).map((s) => (
            <StatusBadge key={s} status={s} count={counts.get(s)} />
          ))}
        </div>
      </TableCell>
      <TableCell className="text-right whitespace-nowrap tabular-nums">
        {formatMoney(p.total_price, p.currency)}
      </TableCell>
    </TableRow>
  )
}
