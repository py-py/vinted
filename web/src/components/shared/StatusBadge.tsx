import { Badge } from "@/components/ui/badge"
import type { SaleStatus } from "@/lib/api"
import { STATUSES } from "@/lib/status"
import { cn } from "@/lib/utils"

export function StatusBadge({ status, count }: { status: SaleStatus; count?: number }) {
  return (
    <Badge className={cn("border-0", STATUSES[status].className)}>
      {count != null && count > 1 && <span className="tabular-nums">{count}×</span>}
      {STATUSES[status].label}
    </Badge>
  )
}
