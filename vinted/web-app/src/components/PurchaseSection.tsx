import type { Item, Purchase } from '../types'
import { ItemCard } from './ItemCard'

interface Props {
  purchase: Purchase
  onOpenItem: (item: Item) => void
  onCycle: (item: Item) => Promise<void>
}

export function PurchaseSection({ purchase, onOpenItem, onCycle }: Props) {
  return (
    <section>
      <div className="flex items-end justify-between gap-4 mb-3 pb-2 border-b">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold truncate">
            {purchase.seller_login || '—'}
            {purchase.seller_country && (
              <span className="text-sm font-normal text-slate-400"> · {purchase.seller_country}</span>
            )}
          </h2>
          <div className="text-xs text-slate-400">
            {purchase.order_date && <>{purchase.order_date.slice(0, 10)} · </>}
            {purchase.items.length} item{purchase.items.length !== 1 ? 's' : ''}
            {purchase.total_price != null && (
              <> · {purchase.total_price.toFixed(2)} {purchase.currency}</>
            )}
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          {purchase.seller_id != null && (
            <a
              href={`https://www.vinted.pl/member/${purchase.seller_id}`}
              target="_blank"
              rel="noopener"
              className="bg-white hover:bg-slate-50 rounded-full p-2 shadow-sm ring-1 ring-slate-200 text-slate-700 hover:text-slate-900"
              title="Open seller profile"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM12 14a7 7 0 0 0-7 7h14a7 7 0 0 0-7-7z" />
              </svg>
            </a>
          )}
          {purchase.conversation_id != null && (
            <a
              href={`https://www.vinted.pl/inbox/${purchase.conversation_id}`}
              target="_blank"
              rel="noopener"
              className="bg-white hover:bg-slate-50 rounded-full p-2 shadow-sm ring-1 ring-slate-200 text-slate-700 hover:text-slate-900"
              title="Open conversation"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 0 1-4-.84L3 21l1.84-4A7.94 7.94 0 0 1 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </a>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {purchase.items.map((item) => (
          <ItemCard
            key={item.id}
            item={item}
            onOpen={() => onOpenItem(item)}
            onCycle={() => onCycle(item)}
          />
        ))}
      </div>
    </section>
  )
}
