import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, Search } from "lucide-react"
import { useDeferredValue } from "react"
import { useSearchParams } from "react-router"

import { ItemCard } from "@/components/shared/ItemCard"
import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { api, type SaleStatus } from "@/lib/api"
import { STATUS_ORDER, STATUSES } from "@/lib/status"

const PAGE_SIZE = 40

export function ItemsPage() {
  // Filters live in the URL so a reload or shared link keeps them.
  const [params, setParams] = useSearchParams()
  const q = params.get("q") ?? ""
  const status = params.getAll("status") as SaleStatus[]
  const page = Number(params.get("page")) || 1
  const deferredQ = useDeferredValue(q)

  const update = (patch: Record<string, string | string[]>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(patch)) {
      next.delete(key)
      ;[value].flat().filter(Boolean).forEach((v) => next.append(key, v))
    }
    if (!("page" in patch)) next.delete("page")
    setParams(next, { replace: true })
  }

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["items", { status, q: deferredQ, page }],
    queryFn: () => api.items({ status, q: deferredQ, page, size: PAGE_SIZE }),
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
        <div className="relative max-w-sm">
          <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search title or seller…"
            className="pl-8"
            value={q}
            onChange={(e) => update({ q: e.target.value })}
          />
        </div>
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
      </div>

      {isError ? (
        <p className="text-sm text-destructive">Failed to load items: {error.message}</p>
      ) : isPending ? (
        <ItemGrid>
          {Array.from({ length: 10 }, (_, i) => (
            <Skeleton key={i} className="aspect-[3/4] rounded-xl" />
          ))}
        </ItemGrid>
      ) : data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No items match the filters.</p>
      ) : (
        <ItemGrid>
          {data.items.map((item) => (
            <ItemCard key={`${item.tx_id}/${item.id}`} item={item} />
          ))}
        </ItemGrid>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <span className="text-muted-foreground">
            Page {page} of {pages}
          </span>
          <Button
            variant="outline"
            size="icon"
            disabled={page <= 1}
            onClick={() => update({ page: String(page - 1) })}
            aria-label="Previous page"
          >
            <ChevronLeft />
          </Button>
          <Button
            variant="outline"
            size="icon"
            disabled={page >= pages}
            onClick={() => update({ page: String(page + 1) })}
            aria-label="Next page"
          >
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}

function ItemGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
      {children}
    </div>
  )
}
