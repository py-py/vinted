import { ChevronLeft, ChevronRight, ExternalLink, XIcon } from "lucide-react"
import { useState, type ReactNode } from "react"

import { Photo } from "@/components/shared/Photo"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { Button } from "@/components/ui/button"
import {
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

/**
 * Building blocks of the item details view, shared by the Items, Purchases and Sales sheets.
 */

type PaneSheetContentProps = {
  children: ReactNode
  // Second pane shown to the right of `children` (the sheet widens); hidden when null.
  pane: ReactNode
  // Changes when the pane shows another record, to replay the slide-in animation.
  paneKey?: string | number
  onClosePane: () => void
}

export function PaneSheetContent({ children, pane, paneKey, onClosePane }: PaneSheetContentProps) {
  const open = pane != null
  return (
    <SheetContent
      showCloseButton={!open}
      className={cn(
        "overflow-y-auto",
        open && "w-full flex-row gap-0 overflow-hidden data-[side=right]:sm:max-w-3xl",
      )}
      // Esc closes the pane first, then the sheet.
      onEscapeKeyDown={(e) => {
        if (!open) return
        e.preventDefault()
        onClosePane()
      }}
    >
      <div className={cn(open && "hidden shrink-0 overflow-y-auto border-r sm:block sm:w-sm")}>
        {children}
      </div>
      {open && (
        <div
          key={paneKey}
          className="min-w-0 flex-1 overflow-y-auto duration-200 animate-in fade-in-0 slide-in-from-right-10"
        >
          {pane}
        </div>
      )}
    </SheetContent>
  )
}

type DetailHeaderProps = {
  title: string
  subtitle: string
  // Set when rendered as a pane inside another sheet: plain headings (the sheet already has
  // its own title) and a button that closes just this pane.
  onClose?: () => void
}

export function DetailHeader({ title, subtitle, onClose }: DetailHeaderProps) {
  return (
    <SheetHeader className="relative">
      {onClose ? (
        <>
          <h2 className="pr-8 font-heading text-base font-medium">{title || "—"}</h2>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
          <Button
            variant="ghost"
            size="icon-sm"
            className="absolute top-3 right-3"
            onClick={onClose}
            aria-label="Close item"
          >
            <XIcon />
          </Button>
        </>
      ) : (
        <>
          <SheetTitle className="pr-6">{title || "—"}</SheetTitle>
          <SheetDescription>{subtitle}</SheetDescription>
        </>
      )}
    </SheetHeader>
  )
}

type PhotoCarouselProps = {
  photos: string[]
  fallbacks: string[]
  title: string
}

export function PhotoCarousel({ photos, fallbacks, title }: PhotoCarouselProps) {
  const [index, setIndex] = useState(0)
  const [galleryOpen, setGalleryOpen] = useState(false)
  const step = (delta: number) => setIndex((i) => (i + delta + photos.length) % photos.length)

  if (photos.length === 0) {
    return <Photo alt="No photo" className="aspect-square w-full rounded-lg bg-muted" />
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <button
          type="button"
          className="block w-full cursor-zoom-in"
          onClick={() => setGalleryOpen(true)}
          aria-label={`Open photos of ${title}`}
        >
          <Photo
            key={index}
            src={photos[index]}
            fallback={fallbacks[index]}
            alt={`${title} (${index + 1}/${photos.length})`}
            className="aspect-square w-full rounded-lg bg-muted object-contain"
          />
        </button>
        {photos.length > 1 && (
          <>
            <Button
              size="icon"
              variant="secondary"
              className="absolute top-1/2 left-2 -translate-y-1/2"
              onClick={() => step(-1)}
              aria-label="Previous photo"
            >
              <ChevronLeft />
            </Button>
            <Button
              size="icon"
              variant="secondary"
              className="absolute top-1/2 right-2 -translate-y-1/2"
              onClick={() => step(1)}
              aria-label="Next photo"
            >
              <ChevronRight />
            </Button>
            <span className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white">
              {index + 1} / {photos.length}
            </span>
          </>
        )}
      </div>
      {photos.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {photos.map((src, i) => (
            <button
              key={src}
              type="button"
              onClick={() => setIndex(i)}
              aria-label={`Show photo ${i + 1}`}
              className={cn(
                "shrink-0 rounded-md ring-offset-2 ring-offset-background",
                i === index ? "ring-2 ring-primary" : "opacity-60 hover:opacity-100",
              )}
            >
              <Photo
                src={src}
                fallback={fallbacks[i]}
                alt=""
                className="size-14 rounded-md bg-muted object-cover"
                loading="lazy"
              />
            </button>
          ))}
        </div>
      )}
      <PhotoGallery
        photos={photos}
        fallbacks={fallbacks}
        title={title}
        open={galleryOpen}
        onOpenChange={setGalleryOpen}
      />
    </div>
  )
}

export function Fields({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <dl className={cn("grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm", className)}>
      {children}
    </dl>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="flex min-w-0 flex-wrap items-center gap-1">{children}</dd>
    </>
  )
}

export function ExternalIcon({ href, title }: { href: string; title: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener"
      title={title}
      className="text-muted-foreground hover:text-foreground"
    >
      <ExternalLink className="size-3.5" />
    </a>
  )
}
