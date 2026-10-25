import { ExternalLink, MessageCircle, User } from "lucide-react"

import { ItemDetails } from "@/components/shared/ItemSheet"
import { Photo } from "@/components/shared/Photo"
import { StatusSelect } from "@/components/shared/StatusSelect"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Item, Purchase } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

type Props = {
  purchase: Purchase | undefined
  onOpenChange: (open: boolean) => void
  // Item opened from the list; shown as a second pane to the right of the purchase.
  item: Item | undefined
  onSelectItem: (item: Item | undefined) => void
}

export function PurchaseSheet({ purchase, onOpenChange, item: openItem, onSelectItem }: Props) {
  return (
    <Sheet open={!!purchase} onOpenChange={onOpenChange}>
      <SheetContent
        showCloseButton={!openItem}
        className={cn(
          "overflow-y-auto",
          openItem && "w-full flex-row gap-0 overflow-hidden data-[side=right]:sm:max-w-3xl",
        )}
        // Esc closes the item pane first, then the purchase.
        onEscapeKeyDown={(e) => {
          if (!openItem) return
          e.preventDefault()
          onSelectItem(undefined)
        }}
      >
        {purchase && (
          <div
            className={cn(
              openItem && "hidden shrink-0 overflow-y-auto border-r sm:block sm:w-sm",
            )}
          >
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
                      {item.price_pln != null
                        ? formatMoney(item.price_pln)
                        : formatMoney(item.paid_price, item.currency)}
                    </div>
                    <StatusSelect item={item} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
        {openItem && (
          <div
            key={openItem.id}
            className="min-w-0 flex-1 overflow-y-auto duration-200 animate-in fade-in-0 slide-in-from-right-10"
          >
            <ItemDetails item={openItem} onClose={() => onSelectItem(undefined)} />
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
