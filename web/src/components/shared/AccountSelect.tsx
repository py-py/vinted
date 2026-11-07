import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ACCOUNTS, api, type Account, type Item } from "@/lib/api"

// Radix Select can't hold an empty value, so "unassigned" gets a sentinel.
const NONE = "none"

export function AccountSelect({ item }: { item: Item }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (account: Account | null) => api.setAccount(item.tx_id, item.id, account),
    onError: () => toast.error("Failed to update account"),
    onSettled: () => queryClient.invalidateQueries(),
  })
  // Show the new value right away; fall back to the server value on error.
  const account = mutation.isPending ? mutation.variables : (item.account ?? null)

  return (
    <Select
      value={account ?? NONE}
      onValueChange={(value) => mutation.mutate(value === NONE ? null : (value as Account))}
      disabled={mutation.isPending}
    >
      <SelectTrigger aria-label="Account" className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE} className="text-muted-foreground">
          —
        </SelectItem>
        {ACCOUNTS.map((a) => (
          <SelectItem key={a} value={a}>
            {a}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
