import type { Item } from '../types'
import { StatusButton } from './StatusButton'

interface Props {
  item: Item
  onOpen: () => void
  onCycle: () => Promise<void>
}

// Placeholder dims; corrected from the natural image size (see usePhotoSwipe).
const PSWP_DIM = 1000

export function ItemCard({ item, onOpen, onCycle }: Props) {
  const photos = item.photo_urls?.length
    ? item.photo_urls
    : item.photo_url
      ? [item.photo_url]
      : []

  const seedDims = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget
    const a = img.parentElement
    if (a && img.naturalWidth) {
      a.setAttribute('data-pswp-width', String(img.naturalWidth))
      a.setAttribute('data-pswp-height', String(img.naturalHeight))
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm hover:shadow-md transition overflow-hidden">
      <div className="pswp-gallery aspect-square relative bg-slate-100 group">
        {photos.length ? (
          photos.map((url, i) => (
            <a
              key={i}
              href={url}
              data-pswp-width={PSWP_DIM}
              data-pswp-height={PSWP_DIM}
              target="_blank"
              rel="noopener"
              className={i === 0 ? 'block w-full h-full' : 'hidden'}
            >
              {i === 0 && (
                <img
                  src={url}
                  alt={item.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition"
                  loading="lazy"
                  decoding="async"
                  referrerPolicy="no-referrer"
                  onLoad={seedDims}
                />
              )}
            </a>
          ))
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
            no photo
          </div>
        )}
        {item.url && (
          <div className="absolute bottom-2 right-2 z-10">
            <a
              href={item.url}
              target="_blank"
              rel="noopener"
              className="bg-white/95 hover:bg-white rounded-full p-2 shadow ring-1 ring-slate-200 text-slate-700 hover:text-slate-900 block"
              title="Open on Vinted"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5h5v5M19 5l-9 9M5 7v12h12" />
              </svg>
            </a>
          </div>
        )}
      </div>

      <div className="p-3 space-y-1 cursor-pointer" onClick={onOpen}>
        <div className="text-sm font-medium line-clamp-2 min-h-[2.5rem] hover:text-blue-600">
          {item.title || '—'}
        </div>
        <div className="text-xs text-slate-500 flex justify-between gap-2">
          <span className="truncate">{item.size || '—'}</span>
          <span className="truncate">{item.condition || ''}</span>
        </div>
        {item.price_pln != null ? (
          <div className="text-sm font-semibold">
            {item.price_pln.toFixed(2)} PLN
            {item.paid_price != null && (
              <span className="text-xs font-normal text-slate-400" title="listing price">
                {' '}
                ({item.paid_price.toFixed(2)} {item.currency})
              </span>
            )}
          </div>
        ) : item.paid_price != null ? (
          <div className="text-sm font-semibold text-slate-500">
            {item.paid_price.toFixed(2)} {item.currency}
          </div>
        ) : null}
        <StatusButton status={item._sale_status} onCycle={onCycle} />
      </div>
    </div>
  )
}
