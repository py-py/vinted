import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useDeferredValue } from "react"

import { ItemRow } from "@/components/shared/ItemRow"
import { PageHeader } from "@/components/shared/PageHeader"
import { Pagination } from "@/components/shared/Pagination"
import { SearchInput } from "@/components/shared/SearchInput"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useUrlParams } from "@/hooks/use-url-params"
import { api, type SaleStatus } from "@/lib/api"
import { STATUS_ORDER, STATUSES } from "@/lib/status"

const PAGE_SIZE = 40

// URL value of the `sell` param → API filter
const SELL_PRICE_FILTERS = {
  with: { label: "With sell price", hasSellPrice: true },
  without: { label: "No sell price", hasSellPrice: false },
} as const
type SellPriceFilter = keyof typeof SELL_PRICE_FILTERS

export function ItemsPage() {
  const [params, update] = useUrlParams()
  const q = params.get("q") ?? ""
  const status = params.getAll("status") as SaleStatus[]
  const sell = params.get("sell") as SellPriceFilter | null
  const hasSellPrice = sell ? SELL_PRICE_FILTERS[sell]?.hasSellPrice : undefined
  const page = Number(params.get("page")) || 1
  const deferredQ = useDeferredValue(q)

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["items", { status, q: deferredQ, hasSellPrice, page }],
    queryFn: () => api.items({ status, q: deferredQ, hasSellPrice, page, size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div className="space-y-6">
      <PageHeader
        title="Items"
        description={data ? `${data.total} items` : "Purchased items and their sale status"}
      />

      <div className="flex flex-col gap-3">
        <SearchInput
          placeholder="Search title or seller…"
          value={q}
          onChange={(value) => update({ q: value })}
        />
        <ToggleGroup
          type="multiple"
          variant="outline"
          size="sm"
          spacing={2}
          className="flex-wrap"
          value={status}
          onValueChange={(value) => update({ status: value })}
        >
          {STATUS_ORDER.map((s) => (
            <ToggleGroupItem
              key={s}
              value={s}
              className="rounded-full data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
            >
              {STATUSES[s].label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <ToggleGroup
          type="single"
          variant="outline"
          size="sm"
          spacing={2}
          className="flex-wrap"
          value={sell ?? ""}
          onValueChange={(value) => update({ sell: value })}
        >
          {Object.entries(SELL_PRICE_FILTERS).map(([key, { label }]) => (
            <ToggleGroupItem
              key={key}
              value={key}
              className="rounded-full data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
            >
              {label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      {isError ? (
        <p className="text-sm text-destructive">Failed to load items: {error.message}</p>
      ) : isPending ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No items match the filters.</p>
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14" />
                <TableHead>Item</TableHead>
                <TableHead className="hidden md:table-cell">Seller</TableHead>
                <TableHead className="hidden sm:table-cell">Date</TableHead>
                <TableHead className="text-right">Paid</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Sell price</TableHead>
                <TableHead className="text-right">Benefits</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((item) => (
                <ItemRow key={`${item.tx_id}/${item.id}`} item={item} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Pagination page={page} pages={pages} onPageChange={(p) => update({ page: String(p) })} />
    </div>
  )
}
