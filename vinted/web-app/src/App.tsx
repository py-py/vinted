import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Item, Purchase, SaleStatus } from './types'
import { getPurchases, updateItemStatus } from './api'
import { ORDER, nextStatus } from './status'
import { usePhotoSwipe } from './usePhotoSwipe'
import { Filters } from './components/Filters'
import { PurchaseSection } from './components/PurchaseSection'
import { ItemModal, type ModalData } from './components/ItemModal'

export default function App() {
  const [purchases, setPurchases] = useState<Purchase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<Set<SaleStatus>>(() => new Set(ORDER))
  const [modal, setModal] = useState<ModalData | null>(null)

  useEffect(() => {
    getPurchases()
      .then(setPurchases)
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const setItemStatus = useCallback((tx: string, itemId: number, status: SaleStatus) => {
    setPurchases((prev) =>
      prev.map((p) =>
        p.tx_id !== tx
          ? p
          : { ...p, items: p.items.map((it) => (it.id === itemId ? { ...it, _sale_status: status } : it)) },
      ),
    )
  }, [])

  // Optimistic: flip local state, persist, revert on failure.
  const cycleStatus = useCallback(
    async (tx: string, item: Item) => {
      const prev = item._sale_status
      const next = nextStatus(prev)
      setItemStatus(tx, item.id, next)
      try {
        await updateItemStatus(tx, item.id, next)
      } catch {
        setItemStatus(tx, item.id, prev)
        alert('Failed to update status')
      }
    },
    [setItemStatus],
  )

  const toggleFilter = useCallback((status: SaleStatus) => {
    setActive((prev) => {
      const next = new Set(prev)
      if (next.has(status)) next.delete(status)
      else next.add(status)
      return next
    })
  }, [])

  // Drop filtered-out items, then sections left empty.
  const visible = useMemo(
    () =>
      purchases
        .map((p) => ({ ...p, items: p.items.filter((it) => active.has(it._sale_status)) }))
        .filter((p) => p.items.length > 0),
    [purchases, active],
  )

  usePhotoSwipe(visible)

  const total = useMemo(() => purchases.reduce((n, p) => n + p.items.length, 0), [purchases])
  const shown = useMemo(() => visible.reduce((n, p) => n + p.items.length, 0), [visible])
  const closeModal = useCallback(() => setModal(null), [])

  return (
    <div className="bg-slate-50 text-slate-900 min-h-screen">
      <header className="border-b bg-white sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Purchased items</h1>
          <span className="text-sm text-slate-500">
            {shown === total ? `${total} items` : `${shown} shown`}
          </span>
        </div>
        {purchases.length > 0 && (
          <div className="max-w-7xl mx-auto px-6 pb-3 -mt-1">
            <Filters active={active} onToggle={toggleFilter} />
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <p className="text-slate-500">Loading…</p>
        ) : error ? (
          <p className="text-red-600">{error}</p>
        ) : visible.length === 0 ? (
          <p className="text-slate-500">Nothing to show.</p>
        ) : (
          <div className="space-y-10">
            {visible.map((p) => (
              <PurchaseSection
                key={p.tx_id}
                purchase={p}
                onOpenItem={(item) => setModal({ item, purchase: p })}
                onCycle={(item) => cycleStatus(p.tx_id, item)}
              />
            ))}
          </div>
        )}
      </main>

      <ItemModal data={modal} onClose={closeModal} />
    </div>
  )
}
