import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowUpRight } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"
import { toast } from "sonner"

import { Input } from "@/components/ui/input"
import { api, ApiError, type Item } from "@/lib/api"

// Links a purchased item to the sale item it was resold as (`_sale_item_id`).
export function SaleItemInput({ item }: { item: Item }) {
  const queryClient = useQueryClient()
  const saved = item.sale_item_id == null ? "" : String(item.sale_item_id)
  const [draft, setDraft] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: (saleItemId: number | null) => api.setSaleItem(item.tx_id, item.id, saleItemId),
    onError: (error) =>
      toast.error(
        error instanceof ApiError && error.status === 404
          ? "No sale contains this item id"
          : "Failed to update sale item",
      ),
    onSettled: async () => {
      await queryClient.invalidateQueries()
      setDraft(null)
    },
  })

  function commit() {
    if (draft === null || draft.trim() === saved) return setDraft(null)
    const trimmed = draft.trim()
    if (trimmed && !/^\d+$/.test(trimmed)) {
      toast.error("Sale item id must be a number")
      return setDraft(null)
    }
    mutation.mutate(trimmed ? Number(trimmed) : null)
  }

  return (
    <div className="flex w-full items-center gap-1">
      <Input
        aria-label="Sale item id"
        inputMode="numeric"
        placeholder="Sale item id"
        value={draft ?? saved}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur()
          if (e.key === "Escape") setDraft(null)
        }}
        disabled={mutation.isPending}
        className="tabular-nums"
      />
      {item.sale_item_id != null && (
        <Link
          to={`/sales?item=${item.sale_item_id}`}
          title="Open sale"
          className="shrink-0 p-1 text-muted-foreground hover:text-foreground"
        >
          <ArrowUpRight className="size-4" />
        </Link>
      )}
    </div>
  )
}
