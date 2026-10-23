import { ChevronLeft, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"

type Props = {
  page: number
  pages: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, pages, onPageChange }: Props) {
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-end gap-2 text-sm">
      <span className="text-muted-foreground">
        Page {page} of {pages}
      </span>
      <Button
        variant="outline"
        size="icon"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft />
      </Button>
      <Button
        variant="outline"
        size="icon"
        disabled={page >= pages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight />
      </Button>
    </div>
  )
}
