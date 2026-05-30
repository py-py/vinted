import { useEffect } from 'react'
import type { Item, Purchase } from '../types'
import { STATES } from '../status'

export interface ModalData {
  item: Item
  purchase: Purchase
}

interface Props {
  data: ModalData | null
  onClose: () => void
}

// Item detail modal. A shell for now; editing controls will land in the
// bordered section at the bottom.
export function ItemModal({ data, onClose }: Props) {
  useEffect(() => {
    if (!data) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.classList.add('overflow-hidden')
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.classList.remove('overflow-hidden')
    }
  }, [data, onClose])

  if (!data) return null
  const { item, purchase } = data
  const photo = item.photo_urls?.[0] || item.photo_url
  const meta = STATES[item._sale_status]
  const sub = [item.size, item.condition, purchase.seller_login].filter(Boolean).join(' · ')

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative mx-auto my-8 w-[92%] max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl bg-white shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 z-10 rounded-full bg-white/90 p-2 shadow ring-1 ring-slate-200 text-slate-600 hover:text-slate-900"
          title="Close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <div className="p-6">
          <div className="flex flex-col sm:flex-row gap-5">
            {photo && (
              <img
                src={photo}
                alt={item.title}
                referrerPolicy="no-referrer"
                className="w-full sm:w-56 aspect-square object-cover rounded-lg bg-slate-100 shrink-0"
              />
            )}
            <div className="min-w-0 flex-1 space-y-3">
              <h3 className="text-xl font-semibold">{item.title || '—'}</h3>
              <div className="text-sm text-slate-500">{sub || '—'}</div>
              <div>
                <span className={`inline-block rounded-md px-3 py-1 text-sm font-semibold ${meta.badge}`}>
                  {meta.label}
                </span>
              </div>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener"
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                >
                  Open on Vinted
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 5h5v5M19 5l-9 9M5 7v12h12" />
                  </svg>
                </a>
              )}
            </div>
          </div>
          <div className="mt-6 border-t pt-4 text-sm text-slate-400">
            {/* TODO: editing controls go here */}
            Editing controls coming here.
          </div>
        </div>
      </div>
    </div>
  )
}
