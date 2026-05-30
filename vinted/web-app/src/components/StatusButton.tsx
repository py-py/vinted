import { useState } from 'react'
import type { SaleStatus } from '../types'
import { STATES } from '../status'

interface Props {
  status: SaleStatus
  /** Cycle to the next status; resolves when the server write settles. */
  onCycle: () => Promise<void>
}

export function StatusButton({ status, onCycle }: Props) {
  const [pending, setPending] = useState(false)
  const meta = STATES[status]

  return (
    <button
      type="button"
      disabled={pending}
      className={`w-full mt-1 rounded-md px-3 py-1.5 text-sm font-semibold transition disabled:opacity-60 ${meta.btn}`}
      onClick={async (e) => {
        e.stopPropagation() // don't trigger the card's open-modal handler
        setPending(true)
        try {
          await onCycle()
        } finally {
          setPending(false)
        }
      }}
    >
      {meta.label}
    </button>
  )
}
