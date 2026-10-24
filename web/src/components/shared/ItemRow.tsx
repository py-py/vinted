import { ExternalLink } from "lucide-react"
import { useState } from "react"

import { Photo } from "@/components/shared/Photo"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { SellPriceInput } from "@/components/shared/SellPriceInput"
import { StatusSelect } from "@/components/shared/StatusSelect"
import { TableCell, TableRow } from "@/components/ui/table"
import type { Item } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

export function ItemRow({ item }: { item: Item }) {
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [cover] = item.photo_urls
  const benefit =
    item.status === "sold" && item.sell_price != null && item.price_pln != null
      ? item.sell_price - item.price_pln
      : null

  return (
    <TableRow>
      <TableCell className="w-24">
        {cover ? (
          <button
            type="button"
            className="block cursor-zoom-in"
            onClick={() => setGalleryOpen(true)}
            aria-label={`Open photos of ${item.title}`}
          >
            <Photo
              src={cover}
              fallback={item.stored_photo_urls[0]}
              alt={item.title}
              className="size-20 rounded-md bg-muted object-cover"
              loading="lazy"
              decoding="async"
            />
          </button>
        ) : (
          <div className="size-20 rounded-md bg-muted" />
        )}
        {cover && (
          <PhotoGallery
            photos={item.photo_urls}
            fallbacks={item.stored_photo_urls}
            title={item.title}
            open={galleryOpen}
            onOpenChange={setGalleryOpen}
          />
        )}
      </TableCell>
      <TableCell className="max-w-64 min-w-40 whitespace-normal">
        <div className="line-clamp-2 font-medium">{item.title || "—"}</div>
        <div className="text-xs text-muted-foreground">
          {[item.size, item.condition].filter(Boolean).join(" · ") || "—"}
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
          {item.id}
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener"
              title="Open on Vinted"
              className="hover:text-foreground"
            >
              <ExternalLink className="size-3.5" />
            </a>
          )}
        </div>
      </TableCell>
      <TableCell className="hidden whitespace-nowrap md:table-cell">
        {item.seller_country && (
          <span className="mr-1.5 text-xs text-muted-foreground">[{item.seller_country}]</span>
        )}
        {item.seller_login || "—"}
        {item.seller_id && (
          <a
            href={`https://www.vinted.pl/member/${item.seller_id}`}
            target="_blank"
            rel="noopener"
            title="Open profile on Vinted"
            className="ml-1 inline-block align-middle text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="size-3.5" />
          </a>
        )}
      </TableCell>
      <TableCell className="hidden whitespace-nowrap tabular-nums sm:table-cell">
        {item.order_date.slice(0, 10)}
      </TableCell>
      <TableCell className="text-right whitespace-nowrap tabular-nums">
        <div className="font-medium">
          {item.price_pln != null ? formatMoney(item.price_pln) : formatMoney(item.paid_price, item.currency)}
        </div>
        {item.price_pln != null && item.paid_price != null && (
          <div
            className="text-xs text-muted-foreground"
            title={item.paid_estimated ? "estimated from order total" : "listing price"}
          >
            {formatMoney(item.paid_price, item.currency)}
          </div>
        )}
      </TableCell>
      <TableCell className="w-40 min-w-36">
        <StatusSelect item={item} />
      </TableCell>
      <TableCell className="w-32 min-w-28">
        <SellPriceInput item={item} />
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-medium whitespace-nowrap tabular-nums",
          benefit != null && (benefit < 0 ? "text-destructive" : "text-green-600"),
        )}
      >
        {benefit != null ? formatMoney(benefit) : "—"}
      </TableCell>
    </TableRow>
  )
}
