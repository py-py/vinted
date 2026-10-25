import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useDeferredValue } from "react"

import { PageHeader } from "@/components/shared/PageHeader"
import { Pagination } from "@/components/shared/Pagination"
import { Photo } from "@/components/shared/Photo"
import { SaleSheet } from "@/components/shared/SaleSheet"
import { SearchInput } from "@/components/shared/SearchInput"
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
import { api, type Sale } from "@/lib/api"
import { formatMoney } from "@/lib/format"

const PAGE_SIZE = 25

export function SalesPage() {
  const [params, update] = useUrlParams()
  const q = params.get("q") ?? ""
  const dateFrom = params.get("from") ?? ""
  const dateTo = params.get("to") ?? ""
  const page = Number(params.get("page")) || 1
  const selectedTx = params.get("tx")
  const selectedItemId = params.get("item")
  const deferredQ = useDeferredValue(q)

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["sales", { q: deferredQ, dateFrom, dateTo }],
    queryFn: () => api.sales({ q: deferredQ, dateFrom, dateTo }),
    placeholderData: keepPreviousData,
  })
  const pages = data ? Math.max(1, Math.ceil(data.length / PAGE_SIZE)) : 1
  const rows = data?.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) ?? []
  // `?item=` alone (link from a purchased item) opens the sale that contains that item.
  const selected = selectedTx
    ? data?.find((s) => s.tx_id === selectedTx)
    : data?.find((s) => s.items.some((i) => String(i.id) === selectedItemId))
  const selectedItem = selected?.items.find((i) => String(i.id) === selectedItemId)
  const hasFilters = Boolean(q || dateFrom || dateTo)

  // `tx` and `item` only open the sheet, so keep the current page when toggling them.
  const select = (tx: string) => update({ tx, item: "", page: params.get("page") ?? "" })
  const selectItem = (id: string) =>
    update({ tx: selected?.tx_id ?? "", item: id, page: params.get("page") ?? "" })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales"
        description={data ? `${data.length} orders` : "Orders sold on Vinted"}
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          placeholder="Search buyer or item title…"
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
        <p className="text-sm text-destructive">Failed to load sales: {error.message}</p>
      ) : isPending ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No sales match the filters.</p>
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Buyer</TableHead>
                <TableHead>Items</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((s) => (
                <SaleRow key={s.tx_id} sale={s} onSelect={() => select(s.tx_id)} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Pagination page={page} pages={pages} onPageChange={(p) => update({ page: String(p) })} />

      <SaleSheet
        sale={selected}
        onOpenChange={(open) => !open && select("")}
        item={selectedItem}
        onSelectItem={(item) => selectItem(item ? String(item.id) : "")}
      />
    </div>
  )
}

function SaleRow({ sale: s, onSelect }: { sale: Sale; onSelect: () => void }) {
  return (
    <TableRow
      className="cursor-pointer"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
    >
      <TableCell className="whitespace-nowrap tabular-nums">
        <span className="hidden sm:inline">{s.order_date.slice(0, 4)}-</span>
        {s.order_date.slice(5, 10)}
      </TableCell>
      <TableCell>
        <div className="font-medium">{s.buyer_login || "—"}</div>
        {s.buyer_country && (
          <div className="text-xs text-muted-foreground">{s.buyer_country}</div>
        )}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div className="hidden -space-x-2 sm:flex">
            {s.items.slice(0, 4).map((i) => (
              <Photo
                key={i.id}
                src={i.photo_urls[0]}
                fallback={i.stored_photo_urls[0]}
                alt=""
                className="size-8 rounded-md bg-muted object-cover ring-2 ring-background"
              />
            ))}
          </div>
          <span className="text-sm text-muted-foreground tabular-nums">{s.items.length}</span>
        </div>
      </TableCell>
      <TableCell className="text-right whitespace-nowrap tabular-nums">
        {formatMoney(s.items_price, s.currency)}
      </TableCell>
    </TableRow>
  )
}
