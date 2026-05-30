import type { SaleStatus } from './types'

// Click-cycle order for the status button.
export const ORDER: SaleStatus[] = [
  'none',
  'reserved',
  'wait_winter',
  'listed',
  'bought',
  'sold',
  'parted_sold',
]

interface StatusMeta {
  label: string
  /** full button classes (incl. hover) */
  btn: string
  /** solid badge classes for the modal */
  badge: string
}

// Full literal class strings so Tailwind's scanner includes them in the build.
export const STATES: Record<SaleStatus, StatusMeta> = {
  none: {
    label: 'Not listed',
    btn: 'bg-slate-100 text-slate-600 ring-1 ring-slate-300 hover:bg-slate-200',
    badge: 'bg-slate-100 text-slate-600',
  },
  reserved: {
    label: 'Reserved',
    btn: 'bg-blue-600 text-white hover:bg-blue-700',
    badge: 'bg-blue-600 text-white',
  },
  wait_winter: {
    label: 'Wait for winter',
    btn: 'bg-sky-500 text-white hover:bg-sky-600',
    badge: 'bg-sky-500 text-white',
  },
  listed: {
    label: 'Listed',
    btn: 'bg-amber-500 text-white hover:bg-amber-600',
    badge: 'bg-amber-500 text-white',
  },
  bought: {
    label: 'Bought (unconfirmed)',
    btn: 'bg-lime-500 text-white hover:bg-lime-600',
    badge: 'bg-lime-500 text-white',
  },
  sold: {
    label: 'SOLD',
    btn: 'bg-green-600 text-white hover:bg-green-700',
    badge: 'bg-green-600 text-white',
  },
  parted_sold: {
    label: 'Parted Sold',
    btn: 'bg-teal-600 text-white hover:bg-teal-700',
    badge: 'bg-teal-600 text-white',
  },
}

export const nextStatus = (s: SaleStatus): SaleStatus =>
  ORDER[(ORDER.indexOf(s) + 1) % ORDER.length]
