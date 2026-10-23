import type { components } from "@/types/api"

type Schemas = components["schemas"]
export type Item = Schemas["Item"]
export type Purchase = Schemas["Purchase"]
export type ItemsPage = Schemas["Page_Item_"]
export type SaleStatus = Schemas["SaleStatus"]
export type Stats = Schemas["Stats"]

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  })
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export type ItemsQuery = {
  status?: SaleStatus[]
  q?: string
  hasSellPrice?: boolean
  page?: number
  size?: number
}

export type PurchasesQuery = {
  q?: string
  dateFrom?: string
  dateTo?: string
}

export const api = {
  items({ status = [], q, hasSellPrice, page, size }: ItemsQuery): Promise<ItemsPage> {
    const params = new URLSearchParams()
    status.forEach((s) => params.append("status", s))
    if (q) params.set("q", q)
    if (hasSellPrice != null) params.set("has_sell_price", String(hasSellPrice))
    if (page) params.set("page", String(page))
    if (size) params.set("size", String(size))
    return request(`/items?${params}`)
  },
  purchases({ q, dateFrom, dateTo }: PurchasesQuery = {}): Promise<Purchase[]> {
    const params = new URLSearchParams()
    if (q) params.set("q", q)
    if (dateFrom) params.set("date_from", dateFrom)
    if (dateTo) params.set("date_to", dateTo)
    return request(`/purchases?${params}`)
  },
  stats(): Promise<Stats> {
    return request("/stats")
  },
  setStatus(txId: string, itemId: number, status: SaleStatus) {
    return request(`/items/${txId}/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    })
  },
  setSellPrice(txId: string, itemId: number, sellPrice: number | null) {
    return request(`/items/${txId}/${itemId}/sell-price`, {
      method: "PATCH",
      body: JSON.stringify({ sell_price: sellPrice }),
    })
  },
}
