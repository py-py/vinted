import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { NewSaleDialog } from "@/components/shared/NewSaleDialog"
import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type Sale } from "@/lib/api"
import { formatMoney } from "@/lib/format"

export function SalesPage() {
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<Sale>()
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
              <SaleCard sale={sale} onDelete={() => setDeleting(sale)} />
            </li>
          ))}
        </ul>
      )}

      <NewSaleDialog open={creating} onOpenChange={setCreating} />
      <DeleteSaleDialog sale={deleting} onOpenChange={(open) => !open && setDeleting(undefined)} />
    </div>
  )
}

function SaleCard({ sale, onDelete }: { sale: Sale; onDelete: () => void }) {
  return (
    <Card className="relative gap-0 overflow-hidden py-0">
      <img
        src={sale.photo_urls[0]}
        alt=""
        loading="lazy"
        className="aspect-square w-full bg-muted object-cover"
      />
      <Button
        variant="secondary"
        size="icon-sm"
        className="absolute top-2 right-2"
        aria-label={`Delete ${sale.title}`}
        onClick={onDelete}
      >
        <Trash2 />
      </Button>
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

type DeleteProps = {
  sale: Sale | undefined
  onOpenChange: (open: boolean) => void
}

function DeleteSaleDialog({ sale, onOpenChange }: DeleteProps) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (id: string) => api.deleteSale(id),
    onSuccess: () => {
      toast.success("Sale deleted")
      queryClient.invalidateQueries({ queryKey: ["sales"] })
      onOpenChange(false)
    },
    onError: () => toast.error("Failed to delete sale"),
  })

  return (
    <Dialog open={!!sale} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete sale?</DialogTitle>
          <DialogDescription>
            “{sale?.title}” and its {sale?.photo_urls.length} photos will be deleted permanently.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={mutation.isPending}
            onClick={() => sale && mutation.mutate(sale.id)}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
