import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react"
import { useDeferredValue, useState } from "react"
import { toast } from "sonner"

import { CardGrid } from "@/components/shared/CardGrid"
import { PageHeader } from "@/components/shared/PageHeader"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { SaleDialog } from "@/components/shared/SaleDialog"
import { SearchInput } from "@/components/shared/SearchInput"
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
import { useUrlParams } from "@/hooks/use-url-params"
import { api, type Sale } from "@/lib/api"
import { formatMoney } from "@/lib/format"

export function SalesPage() {
  const [params, update] = useUrlParams()
  const q = params.get("q") ?? ""
  const deferredQ = useDeferredValue(q).trim().toLowerCase()
  // undefined: closed; null: new sale; Sale: editing it.
  const [editing, setEditing] = useState<Sale | null>()
  const [deleting, setDeleting] = useState<Sale>()
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["sales"],
    queryFn: api.sales,
  })
  // Few sales, so search stays client-side.
  const sales = data?.filter((s) =>
    `${s.title}\n${s.description}`.toLowerCase().includes(deferredQ),
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales"
        description={data ? `${data.length} items for sale` : "Items you sell on Vinted"}
        actions={
          <Button onClick={() => setEditing(null)}>
            <Plus /> New sale
          </Button>
        }
      />

      <SearchInput
        placeholder="Search title or description…"
        value={q}
        onChange={(value) => update({ q: value })}
      />

      {isError ? (
        <p className="text-sm text-destructive">Failed to load sales: {error.message}</p>
      ) : isPending ? (
        <CardGrid>
          {Array.from({ length: 10 }, (_, i) => (
            <Skeleton key={i} className="aspect-[3/4] rounded-xl" />
          ))}
        </CardGrid>
      ) : !sales?.length ? (
        <p className="text-sm text-muted-foreground">
          {q ? "No sales match the search." : "No sales yet. Create the first one."}
        </p>
      ) : (
        <CardGrid>
          {sales.map((sale) => (
            <SaleCard
              key={sale.id}
              sale={sale}
              onEdit={() => setEditing(sale)}
              onDelete={() => setDeleting(sale)}
            />
          ))}
        </CardGrid>
      )}

      {editing !== undefined && (
        <SaleDialog sale={editing ?? undefined} onClose={() => setEditing(undefined)} />
      )}
      <DeleteSaleDialog sale={deleting} onOpenChange={(open) => !open && setDeleting(undefined)} />
    </div>
  )
}

type CardProps = {
  sale: Sale
  onEdit: () => void
  onDelete: () => void
}

function SaleCard({ sale, onEdit, onDelete }: CardProps) {
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [cover] = sale.photo_urls

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="group relative aspect-square overflow-hidden bg-muted">
        {cover && (
          <button
            type="button"
            // absolute: otherwise a portrait photo stretches the aspect-square box
            className="absolute inset-0 cursor-zoom-in"
            onClick={() => setGalleryOpen(true)}
            aria-label={`Open photos of ${sale.title}`}
          >
            <img
              src={cover}
              alt={sale.title}
              className="size-full object-cover transition group-hover:scale-105"
              loading="lazy"
              decoding="async"
            />
          </button>
        )}
        <button
          type="button"
          title="Delete sale"
          aria-label={`Delete ${sale.title}`}
          onClick={onDelete}
          className="absolute right-2 bottom-2 flex size-8 items-center justify-center rounded-full bg-background/90 shadow-sm ring-1 ring-border backdrop-blur hover:bg-background hover:text-destructive"
        >
          <Trash2 className="size-4" />
        </button>
      </div>
      <div className="space-y-1 p-3">
        <div className="line-clamp-2 min-h-10 text-sm font-medium">{sale.title}</div>
        <div className="truncate text-xs text-muted-foreground">{sale.description || "—"}</div>
        <div className="text-xs text-muted-foreground">
          {sale.photo_urls.length} photos · {sale.created_at.slice(0, 10)}
        </div>
        <div className="text-sm font-semibold">{formatMoney(sale.price_pln)}</div>
        <div className="pt-1">
          <Button variant="outline" size="sm" className="w-full" onClick={onEdit}>
            <Pencil /> Edit
          </Button>
        </div>
      </div>
      {cover && (
        <PhotoGallery
          photos={sale.photo_urls}
          fallbacks={[]}
          title={sale.title}
          open={galleryOpen}
          onOpenChange={setGalleryOpen}
        />
      )}
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
