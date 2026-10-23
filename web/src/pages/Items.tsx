import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useDeferredValue } from "react"

import { CardGrid } from "@/components/shared/CardGrid"
import { ItemCard } from "@/components/shared/ItemCard"
import { PageHeader } from "@/components/shared/PageHeader"
import { Pagination } from "@/components/shared/Pagination"
import { SearchInput } from "@/components/shared/SearchInput"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useUrlParams } from "@/hooks/use-url-params"
import { api, type SaleStatus } from "@/lib/api"
import { STATUS_ORDER, STATUSES } from "@/lib/status"

const PAGE_SIZE = 40

export function ItemsPage() {
  const [params, update] = useUrlParams()
  const q = params.get("q") ?? ""
  const status = params.getAll("status") as SaleStatus[]
  const page = Number(params.get("page")) || 1
  const deferredQ = useDeferredValue(q)

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
      </div>

      {isError ? (
        <p className="text-sm text-destructive">Failed to load items: {error.message}</p>
      ) : isPending ? (
        <CardGrid>
          {Array.from({ length: 10 }, (_, i) => (
            <Skeleton key={i} className="aspect-[3/4] rounded-xl" />
          ))}
        </CardGrid>
      ) : data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No items match the filters.</p>
      ) : (
        <CardGrid>
          {data.items.map((item) => (
            <ItemCard key={`${item.tx_id}/${item.id}`} item={item} />
          ))}
        </CardGrid>
      )}

      <Pagination page={page} pages={pages} onPageChange={(p) => update({ page: String(p) })} />
    </div>
  )
}
