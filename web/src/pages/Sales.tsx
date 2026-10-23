import { useQuery } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"

import { NewSaleDialog } from "@/components/shared/NewSaleDialog"
import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type Sale } from "@/lib/api"
import { formatMoney } from "@/lib/format"

export function SalesPage() {
  const [creating, setCreating] = useState(false)
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["sales"],
    queryFn: api.sales,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales"
        description={data ? `${data.length} items for sale` : "Items you sell on Vinted"}
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus /> New sale
          </Button>
        }
      />

      {isError ? (
        <p className="text-sm text-destructive">Failed to load sales: {error.message}</p>
      ) : isPending ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : data.length === 0 ? (
        <p className="text-sm text-muted-foreground">No sales yet. Create the first one.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
          {data.map((sale) => (
            <li key={sale.id}>
              <SaleCard sale={sale} />
            </li>
          ))}
        </ul>
      )}

      <NewSaleDialog open={creating} onOpenChange={setCreating} />
    </div>
  )
}

function SaleCard({ sale }: { sale: Sale }) {
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <img
        src={sale.photo_urls[0]}
        alt=""
        loading="lazy"
        className="aspect-square w-full bg-muted object-cover"
      />
      <div className="space-y-1 p-3">
        <div className="line-clamp-2 text-sm font-medium">{sale.title}</div>
        {sale.description && (
          <p className="line-clamp-2 text-xs text-muted-foreground">{sale.description}</p>
        )}
        <div className="flex items-baseline justify-between gap-2 pt-1">
          <span className="text-sm font-semibold">{formatMoney(sale.price_pln)}</span>
          <span className="text-xs text-muted-foreground tabular-nums">
            {sale.photo_urls.length} photos · {sale.created_at.slice(0, 10)}
          </span>
        </div>
      </div>
    </Card>
  )
}
