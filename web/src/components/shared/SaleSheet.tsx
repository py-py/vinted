import { ExternalLink, MessageCircle, User } from "lucide-react"

import { Photo } from "@/components/shared/Photo"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Sale } from "@/lib/api"
import { formatMoney } from "@/lib/format"

type Props = {
  sale: Sale | undefined
  onOpenChange: (open: boolean) => void
}

export function SaleSheet({ sale, onOpenChange }: Props) {
  return (
    <Sheet open={!!sale} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
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
                <li key={item.id} className="flex gap-3 py-3">
                  <Photo
                    src={item.photo_urls[0]}
                    fallback={item.stored_photo_urls[0]}
                    alt=""
                    className="size-20 shrink-0 rounded-md bg-muted object-cover"
                  />
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-start gap-1">
                      <span className="line-clamp-2 flex-1 text-sm font-medium">
                        {item.title || "—"}
                      </span>
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
      </SheetContent>
    </Sheet>
  )
}
