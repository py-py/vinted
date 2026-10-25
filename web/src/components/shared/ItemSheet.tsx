import {
  DetailHeader,
  ExternalIcon,
  Field,
  Fields,
  PhotoCarousel,
} from "@/components/shared/DetailPane"
import { SellPriceInput } from "@/components/shared/SellPriceInput"
import { StatusSelect } from "@/components/shared/StatusSelect"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent } from "@/components/ui/sheet"
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

export function ItemDetails({ item, onClose }: { item: Item; onClose?: () => void }) {
  const benefit =
    item.status === "sold" && item.sell_price != null && item.price_pln != null
      ? item.sell_price - item.price_pln
      : null

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
        </Fields>
        <Separator />
        <h3 className="text-sm font-medium">Custom fields</h3>
        <Fields className="items-center">
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
        </Fields>
      </div>
    </>
  )
}
