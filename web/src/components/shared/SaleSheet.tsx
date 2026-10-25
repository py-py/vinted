import { ExternalLink, MessageCircle, User } from "lucide-react"

import {
  DetailHeader,
  ExternalIcon,
  Field,
  Fields,
  PaneSheetContent,
  PhotoCarousel,
} from "@/components/shared/DetailPane"
import { Photo } from "@/components/shared/Photo"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Sale, SaleItem } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

type Props = {
  sale: Sale | undefined
  onOpenChange: (open: boolean) => void
  // Item opened from the list; shown as a second pane to the right of the sale.
  item: SaleItem | undefined
  onSelectItem: (item: SaleItem | undefined) => void
}

export function SaleSheet({ sale, onOpenChange, item: openItem, onSelectItem }: Props) {
  return (
    <Sheet open={!!sale} onOpenChange={onOpenChange}>
      <PaneSheetContent
        pane={
          sale &&
          openItem && (
            <SaleItemDetails
              sale={sale}
              item={openItem}
              onClose={() => onSelectItem(undefined)}
            />
          )
        }
        paneKey={openItem?.id}
        onClosePane={() => onSelectItem(undefined)}
      >
        {sale && (
          <>
            <SheetHeader>
              <SheetTitle>
                {sale.buyer_login || "—"}
                {sale.buyer_country && (
                  <span className="ml-1 font-normal text-muted-foreground">
                    · {sale.buyer_country}
                  </span>
                )}
              </SheetTitle>
              <SheetDescription>
                {sale.order_date.slice(0, 10)} · {sale.items.length}{" "}
                {sale.items.length === 1 ? "item" : "items"} ·{" "}
                {formatMoney(sale.items_price, sale.currency)}
                {sale.shipment_price ? (
                  <> + {formatMoney(sale.shipment_price, sale.currency)} shipping</>
                ) : null}
              </SheetDescription>
              <div className="flex gap-2 pt-2">
                {sale.buyer_id && (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={`https://www.vinted.pl/member/${sale.buyer_id}`}
                      target="_blank"
                      rel="noopener"
                    >
                      <User /> Buyer
                    </a>
                  </Button>
                )}
                {sale.conversation_id && (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={`https://www.vinted.pl/inbox/${sale.conversation_id}`}
                      target="_blank"
                      rel="noopener"
                    >
                      <MessageCircle /> Conversation
                    </a>
                  </Button>
                )}
              </div>
            </SheetHeader>
            <ul className="divide-y px-4 pb-4">
              {sale.items.map((item) => (
                <li
                  key={item.id}
                  className={cn(
                    "-mx-2 flex gap-3 rounded-md px-2 py-3",
                    item.id === openItem?.id && "bg-muted",
                  )}
                >
                  <button
                    type="button"
                    className="shrink-0 cursor-pointer"
                    onClick={() => onSelectItem(item)}
                    aria-label={`Open details of ${item.title}`}
                  >
                    <Photo
                      src={item.photo_urls[0]}
                      fallback={item.stored_photo_urls[0]}
                      alt=""
                      className="size-20 rounded-md bg-muted object-cover"
                    />
                  </button>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-start gap-1">
                      <button
                        type="button"
                        className="line-clamp-2 flex-1 cursor-pointer text-left text-sm font-medium hover:underline"
                        onClick={() => onSelectItem(item)}
                      >
                        {item.title || "—"}
                      </button>
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener"
                          title="Open on Vinted"
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <ExternalLink className="size-4" />
                        </a>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {[item.size, item.condition].filter(Boolean).join(" · ") || "—"}
                    </div>
                    <div className="text-sm font-semibold">
                      {formatMoney(item.sold_price, item.currency || sale.currency)}
                      {item.listed_price != null && item.listed_price !== item.sold_price && (
                        <span className="ml-2 text-xs font-normal text-muted-foreground line-through">
                          {formatMoney(item.listed_price, item.currency || sale.currency)}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </PaneSheetContent>
    </Sheet>
  )
}

type SaleItemDetailsProps = {
  sale: Sale
  item: SaleItem
  onClose: () => void
}

function SaleItemDetails({ sale, item, onClose }: SaleItemDetailsProps) {
  const currency = item.currency || sale.currency

  return (
    <>
      <DetailHeader
        title={item.title}
        subtitle={[item.size, item.condition].filter(Boolean).join(" · ") || "—"}
        onClose={onClose}
      />
      <div className="space-y-4 px-4 pb-4">
        <PhotoCarousel
          photos={item.photo_urls}
          fallbacks={item.stored_photo_urls}
          title={item.title}
        />
        <Fields>
          <Field label="Item ID">
            <span className="tabular-nums">{item.id}</span>
            {item.url && <ExternalIcon href={item.url} title="Open on Vinted" />}
          </Field>
          <Field label="Sold">
            <span className="font-medium tabular-nums">
              {formatMoney(item.sold_price, currency)}
            </span>
          </Field>
          <Field label="Listed">
            <span className="tabular-nums">{formatMoney(item.listed_price, currency)}</span>
          </Field>
          <Field label="Order date">
            <span className="tabular-nums">{sale.order_date.slice(0, 10) || "—"}</span>
          </Field>
          <Field label="Buyer">
            {sale.buyer_login || "—"}
            {sale.buyer_country && (
              <span className="text-muted-foreground">· {sale.buyer_country}</span>
            )}
            {sale.buyer_id && (
              <ExternalIcon
                href={`https://www.vinted.pl/member/${sale.buyer_id}`}
                title="Open profile on Vinted"
              />
            )}
          </Field>
          <Field label="Transaction">
            <span className="tabular-nums">{sale.tx_id}</span>
          </Field>
        </Fields>
      </div>
    </>
  )
}
