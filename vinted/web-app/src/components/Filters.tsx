import type { SaleStatus } from '../types'
import { ORDER, STATES } from '../status'

interface Props {
  active: Set<SaleStatus>
  onToggle: (status: SaleStatus) => void
}

export function Filters({ active, onToggle }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {ORDER.map((status) => {
        const on = active.has(status)
        return (
          <button
            key={status}
            type="button"
            onClick={() => onToggle(status)}
            className={`rounded-full px-3 py-1 ring-1 transition ${
              on
                ? 'bg-slate-800 text-white ring-slate-800'
                : 'bg-white text-slate-400 ring-slate-300 line-through'
            }`}
          >
            {STATES[status].label}
          </button>
        )
      })}
    </div>
  )
}
