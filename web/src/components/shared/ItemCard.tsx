import { ExternalLink } from "lucide-react"
import { useState } from "react"

import { Photo } from "@/components/shared/Photo"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { StatusSelect } from "@/components/shared/StatusSelect"
import { Card } from "@/components/ui/card"
import type { Item } from "@/lib/api"
import { formatMoney } from "@/lib/format"

export function ItemCard({ item }: { item: Item }) {
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [cover] = item.photo_urls

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="group relative aspect-square bg-muted">
        {cover ? (
          <button
            type="button"
            className="size-full cursor-zoom-in"
            onClick={() => setGalleryOpen(true)}
            aria-label={`Open photos of ${item.title}`}
          >
            <Photo
              src={cover}
              fallback={item.stored_photo_urls[0]}
              alt={item.title}
              className="size-full object-cover transition group-hover:scale-105"
              loading="lazy"
              decoding="async"
            />
          </button>
        ) : (
          <div className="flex size-full items-center justify-center text-sm text-muted-foreground">
            no photo
          </div>
        )}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener"
            title="Open on Vinted"
            className="absolute right-2 bottom-2 flex size-8 items-center justify-center rounded-full bg-background/90 shadow-sm ring-1 ring-border backdrop-blur hover:bg-background"
          >
            <ExternalLink className="size-4" />
          </a>
        )}
      </div>
      <div className="space-y-1 p-3">
        <div className="line-clamp-2 min-h-10 text-sm font-medium">{item.title || "—"}</div>
        <div className="flex justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">{item.size || "—"}</span>
          <span className="truncate">{item.condition}</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {item.seller_login} · {item.order_date.slice(0, 10)}
        </div>
        <div className="text-sm font-semibold">
          {item.price_pln != null ? formatMoney(item.price_pln) : formatMoney(item.paid_price, item.currency)}
          {item.price_pln != null && item.paid_price != null && (
            <span
              className="ml-1 text-xs font-normal text-muted-foreground"
              title={item.paid_estimated ? "estimated from order total" : "listing price"}
            >
              ({formatMoney(item.paid_price, item.currency)})
            </span>
          )}
        </div>
        <div className="pt-1">
          <StatusSelect item={item} />
        </div>
      </div>
      {cover && (
        <PhotoGallery
          photos={item.photo_urls}
          fallbacks={item.stored_photo_urls}
          title={item.title}
          open={galleryOpen}
          onOpenChange={setGalleryOpen}
        />
      )}
    </Card>
  )
}
