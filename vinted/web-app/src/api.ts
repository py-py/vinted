import type { Purchase, SaleStatus } from './types'

export async function getPurchases(): Promise<Purchase[]> {
  const r = await fetch('/api/purchases')
  if (!r.ok) throw new Error(`GET /api/purchases failed: ${r.status}`)
  return r.json()
}

export async function updateItemStatus(
  tx: string,
  itemId: number,
  status: SaleStatus,
): Promise<void> {
  const r = await fetch(`/api/items/${tx}/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sale_status: status }),
  })
  if (!r.ok) throw new Error(`PATCH item ${tx}/${itemId} failed: ${r.status}`)
}
