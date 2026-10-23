import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { api, type Item, type SaleStatus } from "@/lib/api"
import { STATUS_ORDER, STATUSES } from "@/lib/status"
import { cn } from "@/lib/utils"

export function StatusSelect({ item }: { item: Item }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (status: SaleStatus) => api.setStatus(item.tx_id, item.id, status),
    onError: () => toast.error("Failed to update sale status"),
    onSettled: () => queryClient.invalidateQueries(),
  })
  // Show the new value right away; fall back to the server value on error.
  const status = mutation.isPending ? mutation.variables : item.status

  return (
    <Select
      value={status}
      onValueChange={(value) => mutation.mutate(value as SaleStatus)}
      disabled={mutation.isPending}
    >
      <SelectTrigger
        aria-label="Sale status"
        className={cn("w-full border-0 font-semibold", STATUSES[status].className)}
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {STATUS_ORDER.map((s) => (
          <SelectItem key={s} value={s}>
            {STATUSES[s].label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
