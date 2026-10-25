import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react"
import { useState, type ReactNode } from "react"

import { Photo } from "@/components/shared/Photo"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { SellPriceInput } from "@/components/shared/SellPriceInput"
import { StatusSelect } from "@/components/shared/StatusSelect"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Item } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

type Props = {
  item: Item | undefined
  onOpenChange: (open: boolean) => void
}

export function ItemSheet({ item, onOpenChange }: Props) {
  return (
    <Sheet open={!!item} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        {/* Keyed so the carousel starts from the first photo for every item. */}
        {item && <ItemDetails key={`${item.tx_id}/${item.id}`} item={item} />}
      </SheetContent>
    </Sheet>
  )
}

function ItemDetails({ item }: { item: Item }) {
  const benefit =
    item.status === "sold" && item.sell_price != null && item.price_pln != null
      ? item.sell_price - item.price_pln
      : null

  return (
    <>
      <SheetHeader>
        <SheetTitle className="pr-6">{item.title || "—"}</SheetTitle>
        <SheetDescription>
          {[item.size, item.condition].filter(Boolean).join(" · ") || "—"}
        </SheetDescription>
      </SheetHeader>
      <div className="space-y-4 px-4 pb-4">
        <PhotoCarousel item={item} />
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <Field label="Item ID">
            <span className="tabular-nums">{item.id}</span>
            {item.url && <ExternalIcon href={item.url} title="Open on Vinted" />}
          </Field>
          <Field label="Paid">
            <span className="font-medium tabular-nums">
              {item.price_pln != null
                ? formatMoney(item.price_pln)
                : formatMoney(item.paid_price, item.currency)}
            </span>
            {item.price_pln != null && item.paid_price != null && (
              <span className="text-muted-foreground tabular-nums">
                {formatMoney(item.paid_price, item.currency)}
                {item.paid_estimated && " (est.)"}
              </span>
            )}
          </Field>
          <Field label="Order date">
            <span className="tabular-nums">{item.order_date.slice(0, 10) || "—"}</span>
          </Field>
          <Field label="Seller">
            {item.seller_login || "—"}
            {item.seller_country && (
              <span className="text-muted-foreground">· {item.seller_country}</span>
            )}
            {item.seller_id && (
              <ExternalIcon
                href={`https://www.vinted.pl/member/${item.seller_id}`}
                title="Open profile on Vinted"
              />
            )}
          </Field>
          <Field label="Transaction">
            <span className="tabular-nums">{item.tx_id}</span>
          </Field>
        </dl>
        <Separator />
        <h3 className="text-sm font-medium">Custom fields</h3>
        <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 text-sm">
          <Field label="Status">
            <div className="w-full">
              <StatusSelect item={item} />
            </div>
          </Field>
          <Field label="Sell price">
            <div className="w-full">
              <SellPriceInput item={item} />
            </div>
          </Field>
          <Field label="Benefits">
            <span
              className={cn(
                "font-medium tabular-nums",
                benefit != null && (benefit < 0 ? "text-destructive" : "text-green-600"),
              )}
            >
              {benefit != null ? formatMoney(benefit) : "—"}
            </span>
          </Field>
        </dl>
      </div>
    </>
  )
}

function PhotoCarousel({ item }: { item: Item }) {
  const photos = item.photo_urls
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
          aria-label={`Open photos of ${item.title}`}
        >
          <Photo
            key={index}
            src={photos[index]}
            fallback={item.stored_photo_urls[index]}
            alt={`${item.title} (${index + 1}/${photos.length})`}
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
                fallback={item.stored_photo_urls[i]}
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
        fallbacks={item.stored_photo_urls}
        title={item.title}
        open={galleryOpen}
        onOpenChange={setGalleryOpen}
      />
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="flex min-w-0 flex-wrap items-center gap-1">{children}</dd>
    </>
  )
}

function ExternalIcon({ href, title }: { href: string; title: string }) {
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
