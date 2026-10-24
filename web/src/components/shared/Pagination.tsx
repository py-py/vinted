import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"

type Props = {
  page: number
  pages: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, pages, onPageChange }: Props) {
  if (pages <= 1) return null

  const go = (p: number) => {
    onPageChange(p)
    window.scrollTo({ top: 0 })
  }

  return (
    <nav className="flex items-center justify-center gap-1" aria-label="Pagination">
      <Button
        variant="ghost"
        size="sm"
        disabled={page <= 1}
        onClick={() => go(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft />
        <span className="hidden sm:inline">Previous</span>
      </Button>
      {pageList(page, pages).map((p, i) =>
        p == null ? (
          <span
            key={`gap-${i}`}
            className="flex size-8 items-center justify-center text-muted-foreground"
            aria-hidden
          >
            <MoreHorizontal className="size-4" />
          </span>
        ) : (
          <Button
            key={p}
            variant={p === page ? "outline" : "ghost"}
            size="icon"
            className="tabular-nums"
            onClick={() => p !== page && go(p)}
            aria-current={p === page ? "page" : undefined}
          >
            {p}
          </Button>
        ),
      )}
      <Button
        variant="ghost"
        size="sm"
        disabled={page >= pages}
        onClick={() => go(page + 1)}
        aria-label="Next page"
      >
        <span className="hidden sm:inline">Next</span>
        <ChevronRight />
      </Button>
    </nav>
  )
}

// Always 7 slots so the controls don't shift: 1 2 3 4 5 … 13 / 1 … 6 7 8 … 13 /
// 1 … 9 10 11 12 13 — `null` marks a gap
function pageList(page: number, pages: number): (number | null)[] {
  const range = (from: number, to: number) => Array.from({ length: to - from + 1 }, (_, i) => from + i)
  if (pages <= 7) return range(1, pages)
  if (page <= 4) return [...range(1, 5), null, pages]
  if (page >= pages - 3) return [1, null, ...range(pages - 4, pages)]
  return [1, null, page - 1, page, page + 1, null, pages]
}
