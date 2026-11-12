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

export function AccountSelect({ item }: { item: Item }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (account: Account) => api.setAccount(item.tx_id, item.id, account),
    onError: () => toast.error("Failed to update seller account"),
    onSettled: () => queryClient.invalidateQueries(),
  })
  // Show the new value right away; fall back to the server value on error.
  const account = mutation.isPending ? mutation.variables : item.account

  return (
    <Select
      value={account}
      onValueChange={(value) => mutation.mutate(value as Account)}
      disabled={mutation.isPending}
    >
      <SelectTrigger aria-label="Seller account" className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {ACCOUNTS.map((a) => (
          <SelectItem key={a} value={a}>
            {a}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
