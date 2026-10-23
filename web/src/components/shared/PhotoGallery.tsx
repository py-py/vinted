import { ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"

type Props = {
  photos: string[]
  title: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PhotoGallery({ photos, title, open, onOpenChange }: Props) {
  const [index, setIndex] = useState(0)
  const step = (delta: number) => setIndex((i) => (i + delta + photos.length) % photos.length)

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) setIndex(0)
        onOpenChange(next)
      }}
    >
      <DialogContent
        className="max-w-3xl p-2 sm:max-w-3xl"
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") step(-1)
          if (e.key === "ArrowRight") step(1)
        }}
      >
        <DialogTitle className="sr-only">{title}</DialogTitle>
        <div className="relative flex items-center justify-center">
          <img
            src={photos[index]}
            alt={`${title} (${index + 1}/${photos.length})`}
            className="max-h-[80vh] w-auto rounded-md object-contain"
            referrerPolicy="no-referrer"
          />
          {photos.length > 1 && (
            <>
              <Button
                size="icon"
                variant="secondary"
                className="absolute left-2"
                onClick={() => step(-1)}
                aria-label="Previous photo"
              >
                <ChevronLeft />
              </Button>
              <Button
                size="icon"
                variant="secondary"
                className="absolute right-2"
                onClick={() => step(1)}
                aria-label="Next photo"
              >
                <ChevronRight />
              </Button>
              <span className="absolute bottom-2 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white">
                {index + 1} / {photos.length}
              </span>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
