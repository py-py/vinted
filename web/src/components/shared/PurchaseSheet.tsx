import { ExternalLink, MessageCircle, User } from "lucide-react"

import { StatusSelect } from "@/components/shared/StatusSelect"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Purchase } from "@/lib/api"
import { formatMoney } from "@/lib/format"

type Props = {
  purchase: Purchase | undefined
  onOpenChange: (open: boolean) => void
}

export function PurchaseSheet({ purchase, onOpenChange }: Props) {
  return (
    <Sheet open={!!purchase} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        {purchase && (
          <>
            <SheetHeader>
              <SheetTitle>
                {purchase.seller_login || "—"}
                {purchase.seller_country && (
                  <span className="ml-1 font-normal text-muted-foreground">
                    · {purchase.seller_country}
                  </span>
                )}
              </SheetTitle>
              <SheetDescription>
                {purchase.order_date.slice(0, 10)} · {purchase.items.length}{" "}
                {purchase.items.length === 1 ? "item" : "items"} ·{" "}
                {formatMoney(purchase.total_price, purchase.currency)}
              </SheetDescription>
              <div className="flex gap-2 pt-2">
                {purchase.seller_id && (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={`https://www.vinted.pl/member/${purchase.seller_id}`}
                      target="_blank"
                      rel="noopener"
                    >
                      <User /> Seller
                    </a>
                  </Button>
                )}
                {purchase.conversation_id && (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={`https://www.vinted.pl/inbox/${purchase.conversation_id}`}
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
              {purchase.items.map((item) => (
                <li key={item.id} className="flex gap-3 py-3">
                  <img
                    src={item.photo_urls[0]}
                    alt=""
                    className="size-20 shrink-0 rounded-md bg-muted object-cover"
                    referrerPolicy="no-referrer"
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
                      {item.price_pln != null
                        ? formatMoney(item.price_pln)
                        : formatMoney(item.paid_price, item.currency)}
                    </div>
                    <StatusSelect item={item} />
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
