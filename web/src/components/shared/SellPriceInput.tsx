import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { toast } from "sonner"

import { Input } from "@/components/ui/input"
import { api, type Item } from "@/lib/api"

function parsePrice(text: string): number | null | undefined {
  const trimmed = text.trim().replace(",", ".")
  if (!trimmed) return null
  const value = Number(trimmed)
  return Number.isFinite(value) && value >= 0 ? value : undefined
}

export function SellPriceInput({ item }: { item: Item }) {
  const queryClient = useQueryClient()
  const saved = item.sell_price == null ? "" : String(item.sell_price)
  const [draft, setDraft] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: (price: number | null) => api.setSellPrice(item.tx_id, item.id, price),
    onError: () => toast.error("Failed to update sell price"),
    onSettled: async () => {
      await queryClient.invalidateQueries()
      setDraft(null)
    },
  })

  function commit() {
    if (draft === null || draft === saved) return setDraft(null)
    const price = parsePrice(draft)
    if (price === undefined) {
      toast.error("Sell price must be a non-negative number")
      return setDraft(null)
    }
    if (price === item.sell_price) return setDraft(null)
    mutation.mutate(price)
  }

  return (
    <div className="relative">
      <Input
        aria-label="Sell price"
        inputMode="decimal"
        placeholder="Sell price"
        value={draft ?? saved}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur()
          if (e.key === "Escape") setDraft(null)
        }}
        disabled={mutation.isPending}
        className="pr-11 tabular-nums"
      />
      <span className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-muted-foreground">
        PLN
      </span>
    </div>
  )
}
